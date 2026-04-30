from odoo import models, fields, tools, api, exceptions, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import date_utils
from collections import defaultdict


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    batch_employee_ids = fields.One2many("hr.payslip.run.employee", "payslip_batch_id",
                                         string="Payslip Batch Employees")
    batch_summary_ids = fields.One2many("hr.payslip.run.summary", "payslip_batch_id", string="Payslip Batch Summary")
    total_basic_amount = fields.Float(string="Basic Amount", readonly=True)
    total_alw_amount = fields.Float(string="Allowance Amount", readonly=True)
    total_ded_amount = fields.Float(string="Deduction Amount", readonly=True)
    total_gross_amount = fields.Float(string="Gross Amount", readonly=True)
    total_net_amount = fields.Float(string="Net Amount", readonly=True)
    salary_journal_entry_id = fields.Many2one("account.move", readonly=True)
    paid_date = fields.Date(string="Paid Date", readonly=True)
    approval_state = fields.Selection([
        ('draft', 'New'),
        ('submitted', 'Submitted to HR'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Approval Status', default='draft', copy=False, tracking=True)

    rejection_reason = fields.Text(string="Rejection Reason", readonly=True, tracking=True)

    @api.depends("state")
    def _compute_approval_state(self):
        for payslip_run in self:
            payslip_run.approval_state = payslip_run.state

    def action_open(self):
        res = super().action_open()
        self._generate_batch_payslip_data_summary()
        return res

    def _generate_batch_payslip_data_summary(self):
        # Pre-fetch category IDs once
        category_alw = self.env.ref("hr_payroll.ALW").id
        category_ded = self.env.ref("hr_payroll.DED").id
        category_net = self.env.ref("hr_payroll.NET").id

        for batch in self:
            # if not batch.slip_ids or batch.state != "verify":
            if not batch.slip_ids:
                continue

            # -- Batch Summary -- #

            total_basic_amount = 0
            total_alw_amount = 0
            total_ded_amount = 0
            total_gross_amount = 0
            total_net_amount = 0

            # -- Batch Summary -- #

            batch_employee_list = []
            salary_rule_total_dict = defaultdict(float)

            for payslip in batch.slip_ids:
                employee = payslip.employee_id
                employee_data = {
                    "payslip_batch_id": batch.id,
                    "employee_id": employee.id,
                }

                basic_amount = 0.0
                allowance_amount = 0.0
                deduction_amount = 0.0
                net_amount = 0.0

                for line in payslip.line_ids:
                    rule = line.salary_rule_id
                    category_id = line.category_id.id
                    total = line.total

                    # Salary components
                    if rule.code == "BASIC" and total > 0:
                        basic_amount = total
                        total_basic_amount += total
                    elif category_id == category_alw and total > 0:
                        allowance_amount += total
                        total_alw_amount += total
                    elif category_id == category_ded and total < 0:
                        deduction_amount += total
                        total_ded_amount += total
                    # elif rule.code == "GROSS" and total > 0:
                    elif rule.code == "GROSS":
                        total_gross_amount += total
                    # elif category_id == category_net and total > 0:
                    elif category_id == category_net:
                        net_amount = total
                        total_net_amount += total

                    # Aggregated salary rule totals
                    line_code = line.code
                    if total != 0 and line_code:
                        salary_rule_total_dict[rule.id] += total

                employee_data.update({
                    "basic_amount": basic_amount,
                    "allowance_amount": allowance_amount,
                    "deduction_amount": deduction_amount,
                    "net_amount": net_amount
                })

                batch_employee_list.append((0, 0, employee_data))

            # Prepare salary rule summary data
            batch_summary = [
                (0, 0, {
                    "payslip_batch_id": batch.id,
                    "name": self.env["hr.salary.rule"].browse(rule_id).name,
                    "salary_rule_id": rule_id,
                    "total_amount": total,
                })
                for rule_id, total in salary_rule_total_dict.items()
            ]

            # Assign computed data
            if batch_employee_list:
                batch.batch_employee_ids = batch_employee_list
            if batch_summary:
                batch.batch_summary_ids = batch_summary

            batch.total_basic_amount = total_basic_amount
            batch.total_alw_amount = total_alw_amount
            batch.total_ded_amount = total_ded_amount
            batch.total_gross_amount = total_gross_amount
            batch.total_net_amount = total_net_amount

    def action_draft(self):
        res = super().action_draft()
        if self.batch_employee_ids:
            self.batch_employee_ids.unlink()
        if self.batch_summary_ids:
            self.batch_summary_ids.unlink()
        return res

    def action_hr_reject_batch(self):
        self.ensure_one()
        if self.approval_state != 'submitted':
            raise UserError(_("Only submitted batches can be rejected."))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Batch'),
            'view_mode': 'form',
            'res_model': 'payslip.run.reject.wizard',
            'target': 'new',
            'context': {
                'default_payslip_run_id': self.id,
            },
        }

    def action_hr_approve_batch(self):
        for rec in self:
            if rec.approval_state != 'submitted':
                raise UserError(_("Only submitted batches can be approved."))
            rec.action_validate()
            rec.approval_state = 'approved'
            rec.rejection_reason = False

    def action_submit_to_hr(self):
        for rec in self:
            if rec.approval_state != 'draft':
                raise UserError(_("Only batches in 'New' state can be submitted to HR."))
            rec.approval_state = 'submitted'
            rec.rejection_reason = False

    def _get_anb_balancing_account(self, company):
        # NOTE:
        # In this database the ANB account can be configured in a parent/shared company,
        # so avoid strict company filtering and prioritize exact code match.
        account = self.env['account.account'].with_context(active_test=False).search([
            ('code', '=', '1001.02.00.07')
        ], limit=1)
        if not account:
            account = self.env['account.account'].with_context(active_test=False).search([
                ('name', 'ilike', 'ANB Bank-470015')
            ], limit=1)
        return account

    def _prepare_balancing_line_vals(self, batch, journal, account, imbalance_amount):
        return {
            'name': f"{batch.name} balancing line",
            'partner_id': False,
            'account_id': account.id,
            'journal_id': journal.id,
            'date': fields.Date.today(),
            'debit': abs(imbalance_amount) if imbalance_amount < 0 else 0.0,
            'credit': imbalance_amount if imbalance_amount > 0 else 0.0,
        }

    def action_validate(self):
        res = super().action_validate()
        journal = self.env.ref('pr_account.journal_journal_voucher')

        for rec in self:
            pay_slips = rec.slip_ids.filtered(lambda s: not s.hold_salary)

            move_line_ids = []
            for slip in pay_slips:
                move_line_ids += slip.prepare_payslip_entry_vals_lines()

            total_debit = sum(vals[2].get('debit', 0.0) for vals in move_line_ids if vals[0] == 0)
            total_credit = sum(vals[2].get('credit', 0.0) for vals in move_line_ids if vals[0] == 0)
            currency = rec.company_id.currency_id
            imbalance_amount = currency.round(total_debit - total_credit)

            if not currency.is_zero(imbalance_amount):
                anb_account = rec._get_anb_balancing_account(rec.company_id)
                if not anb_account:
                    raise ValidationError(_(
                        "Could not find ANB balancing account (code 1001.02.00.07) to balance payroll journal entry."
                    ))

                move_line_ids.append((0, 0, rec._prepare_balancing_line_vals(
                    batch=rec,
                    journal=journal,
                    account=anb_account,
                    imbalance_amount=imbalance_amount,
                )))

            salary_journal_entry_id = self.env['account.move'].sudo().with_context(check_move_validity=False,
                                                                                   skip_invoice_sync=True).create({
                'ref': f"Payslip Batch of PETRORAQ Company for {rec.date_end.strftime('%B')} {rec.date_end.year}",
                'date': fields.Date.today(),
                'move_type': 'entry',
                'journal_id': journal.id,

                'line_ids': move_line_ids,
            })
            if salary_journal_entry_id:
                final_debit = sum(salary_journal_entry_id.line_ids.mapped('debit'))
                final_credit = sum(salary_journal_entry_id.line_ids.mapped('credit'))
                final_imbalance = currency.round(final_debit - final_credit)
                if not currency.is_zero(final_imbalance):
                    anb_account = rec._get_anb_balancing_account(rec.company_id)
                    if not anb_account:
                        raise ValidationError(_(
                            "Could not find ANB balancing account (code 1001.02.00.07) for final payroll move balancing."
                        ))
                    salary_journal_entry_id.with_context(check_move_validity=False, skip_invoice_sync=True).write({
                        'line_ids': [(0, 0, rec._prepare_balancing_line_vals(
                            batch=rec,
                            journal=journal,
                            account=anb_account,
                            imbalance_amount=final_imbalance,
                        ))],
                    })

                if salary_journal_entry_id.state != 'posted':
                    salary_journal_entry_id.sudo().with_context(check_move_validity=False, skip_invoice_sync=True).action_post()

                rec.salary_journal_entry_id = salary_journal_entry_id.id
                for slip_sa in pay_slips:
                    slip_sa.sudo().write({'salary_journal_entry_id': salary_journal_entry_id.id})
            rec.write({'state': 'close'})
        return res

    def action_paid(self):
        for rec in self:
            if rec.salary_journal_entry_id and rec.salary_journal_entry_id.state != "posted":
                rec.salary_journal_entry_id.sudo().with_context(check_move_validity=False,
                                                                skip_invoice_sync=True).action_post()
            for slip_sa in rec.slip_ids.filtered(
                    lambda s: s.salary_journal_entry_id.id == rec.salary_journal_entry_id.id and not s.hold_salary):
                slip_sa.sudo().write({
                    'state': 'paid',
                    'paid_date': fields.Date.today(),
                })
            rec.write({'paid_date': fields.Date.today(), 'state': 'paid'})

    def action_open_salary_journal_entry(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": self.salary_journal_entry_id.id,
            "views": [[self.env.ref('account.view_move_form').id, "form"]],
            "target": "current",
            "name": self.name,
            "context": {"form_view_initial_mode": "readonly"}
        }

    def unlink(self):
        if self.batch_employee_ids:
            self.batch_employee_ids.unlink()
        if self.batch_summary_ids:
            self.batch_summary_ids.unlink()
        if self.salary_journal_entry_id:
            if self.salary_journal_entry_id.state != 'draft':
                self.salary_journal_entry_id.sudo().button_draft()
            self.salary_journal_entry_id.sudo().unlink()
            self.paid_date = False
        return super().unlink()


class HrPayslipRunEmployee(models.Model):
    """
    """

    # region [Initial]
    _name = 'hr.payslip.run.employee'
    _description = 'Hr Payslip Run Employee'
    _rec_name = 'payslip_batch_id'
    # endregion [Initial]

    payslip_batch_id = fields.Many2one("hr.payslip.run", string="Payslip Batch", readonly=True, required=True)
    employee_id = fields.Many2one("hr.employee", string="Employee", required=True, readonly=True)
    basic_amount = fields.Float(string="Basic Amount", readonly=True)
    allowance_amount = fields.Float(string="Allowance Amount", readonly=True)
    deduction_amount = fields.Float(string="Deduction Amount", readonly=True)
    net_amount = fields.Float(string="Net Amount", readonly=True)


class HrPayslipRunSummary(models.Model):
    """
    """

    # region [Initial]
    _name = 'hr.payslip.run.summary'
    _description = 'Hr Payslip Run Summary'
    _rec_name = 'payslip_batch_id'
    # endregion [Initial]

    payslip_batch_id = fields.Many2one("hr.payslip.run", string="Payslip Batch", readonly=True, required=True)
    name = fields.Char(string="Name")
    salary_rule_id = fields.Many2one("hr.salary.rule", string="Rule", required=True, readonly=True)
    category_id = fields.Many2one("hr.salary.rule.category", string="Category", related="salary_rule_id.category_id")
    total_amount = fields.Float(string="Total", readonly=True)


class PayslipRunRejectWizard(models.TransientModel):
    _name = 'payslip.run.reject.wizard'
    _description = 'Payslip Run Reject Wizard'

    payslip_run_id = fields.Many2one('hr.payslip.run', string="Batch", required=True)
    reason = fields.Text(string="Reason", required=True)

    def action_reject_confirm(self):
        self.ensure_one()
        batch = self.payslip_run_id
        batch.rejection_reason = self.reason
        batch.approval_state = 'draft'
        return {'type': 'ir.actions.act_window_close'}