
from odoo import models, fields, api, _, Command
from odoo.exceptions import UserError, ValidationError
from odoo.tools import frozendict, format_date, float_compare, Query


class PaymentReceipt(models.Model):
    # region [Initial]
    _name = "pr.payment.receipt"
    _description = "Payment Receipt"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "id"
    _rec_name = 'name'
    # endregion [Initial]

    # region [Fields]

    name = fields.Char(string='Receipt Number', required=False, translate=True)
    company_id = fields.Many2one('res.company', string='Company', index=True, required=True, default=lambda self: self.env.company,
                                 tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id', store=True, tracking=True)
    received_from_partner_id = fields.Many2one('res.partner', string='Received From', tracking=True)
    debit_account_id = fields.Many2one('account.account', string='Debit Acc', required=True, index=True, tracking=True)
    debit_account_name = fields.Char(string='Debit Acc. Name', related="debit_account_id.name", store=True, tracking=True)
    debit_cs_project_id = fields.Many2one("account.analytic.account", string="Debit Project",
                                    domain="[('analytic_plan_type', '=', 'project')]", tracking=True)
    check_debit_cost_centers_block = fields.Boolean(compute="_compute_check_debit_cost_centers_block")
    # === Analytic fields === #
    debit_analytic_line_ids = fields.One2many(
        comodel_name='account.analytic.line', inverse_name='debit_payment_receipt_id',
        string='Debit Analytic lines',
    )
    debit_analytic_distribution = fields.Json(
        inverse="_inverse_debit_analytic_distribution",
    )
    credit_account_id = fields.Many2one('account.account', string='Credit Account', required=True, index=True, tracking=True)
    credit_account_name = fields.Char(string='Credit Account Name', related="credit_account_id.name", store=True, tracking=True)
    credit_cs_project_id = fields.Many2one("account.analytic.account", string="Credit Project",
                                          domain="[('analytic_plan_type', '=', 'project')]", tracking=True)
    check_credit_cost_centers_block = fields.Boolean(compute="_compute_check_credit_cost_centers_block")
    # === Analytic fields === #
    credit_analytic_line_ids = fields.One2many(
        comodel_name='account.analytic.line', inverse_name='credit_payment_receipt_id',
        string='Credit Analytic lines',
    )
    credit_analytic_distribution = fields.Json(
        inverse="_inverse_credit_analytic_distribution",
    )
    analytic_precision = fields.Integer(
        store=False,
        default=lambda self: self.env["decimal.precision"].precision_get(
            "Percentage Analytic"
        ),
    )
    receipt_date = fields.Date(string="Receipt Date", required=True, default=fields.Date.today, tracking=True)
    receipt_mode = fields.Selection([
        ("cash", "Cash"),
        ("cheque", "Cheque"),
        ("deposit", "Deposit"),
        ("e_transfer", "e Transfer"),
    ], string="Receipt Mode", required=True, tracking=True)
    description = fields.Text(string='Description', tracking=True)
    notes = fields.Text(string='Notes', tracking=True)
    amount = fields.Float(string="Amount", tracking=True)
    tax_id = fields.Many2one('account.tax', string='Taxes', ondelete='restrict', check_company=True)
    amount_tax = fields.Float(string="Tax Amount", tracking=True, compute="_compute_amount", store=True)
    total_amount = fields.Float(string="Total Amount", tracking=True, compute="_compute_amount", store=True)
    journal_entry_id = fields.Many2one("account.move", string="Journal Entry", readonly=True, tracking=True)
    state = fields.Selection([
        ("draft", "Draft"),
        ("posted", "Posted"),
        ("cancel", "Cancelled"),
    ], string="Status", tracking=True, default="draft")

    # endregion [Fields]

    # region [Onchange Methods]

    @api.onchange("debit_cs_project_id")
    def _onchange_debit_cs_project_id(self):
        for rec in self:
            debit_analytic_distribution = {}
            if rec.debit_cs_project_id:
                # Analytic Distribution
                if rec.debit_cs_project_id.department_id:
                    debit_analytic_distribution.update({
                        str(rec.debit_cs_project_id.department_id.id): 100.0
                    })
                if rec.debit_cs_project_id.section_id:
                    debit_analytic_distribution.update({
                        str(rec.debit_cs_project_id.section_id.id): 100.0
                    })
                debit_analytic_distribution.update({
                    str(rec.debit_cs_project_id.id): 100.0
                })
            rec.debit_analytic_distribution = debit_analytic_distribution

    @api.onchange("credit_cs_project_id")
    def _onchange_credit_cs_project_id(self):
        for rec in self:
            credit_analytic_distribution = {}
            if rec.credit_cs_project_id:
                # Analytic Distribution
                if rec.credit_cs_project_id.department_id:
                    credit_analytic_distribution.update({
                        str(rec.credit_cs_project_id.department_id.id): 100.0
                    })
                if rec.credit_cs_project_id.section_id:
                    credit_analytic_distribution.update({
                        str(rec.credit_cs_project_id.section_id.id): 100.0
                    })
                credit_analytic_distribution.update({
                    str(rec.credit_cs_project_id.id): 100.0
                })
            rec.credit_analytic_distribution = credit_analytic_distribution
            # Analytic Distribution

    # endregion [Onchange Methods]

    # region [Constrains]

    @api.constrains("company_id")
    def _check_company(self):
        for receipt in self:
            if receipt.company_id and receipt.company_id.id != self.env.company.id:
                raise ValidationError("You Should Select The Current Company !!, Please Check"
                                      "")
    # endregion [Constrains]

    # region [Actions]

    def action_draft(self):
        for receipt in self:
            if receipt.journal_entry_id and receipt.journal_entry_id.state != "draft":
                receipt.journal_entry_id.sudo().button_draft()
                receipt.journal_entry_id.unlink()
            receipt.state = "draft"

    def action_cancel(self):
        for receipt in self:
            if receipt.journal_entry_id and receipt.journal_entry_id.state != "cancel":
                receipt.journal_entry_id.sudo().button_draft()
                receipt.journal_entry_id.sudo().button_cancel()
            receipt.state = "cancel"

    def action_post(self):
        for receipt in self:
            journal_entry_id = self.env['account.move'].create({
                'name': receipt.name,
                'ref': receipt.name,
                'date': receipt.receipt_date,
                'move_type': 'entry',
            })
            if journal_entry_id:
                journal_entry_id = journal_entry_id.with_context(check_move_validity=False)
                move_line = self.env['account.move.line'].with_context(check_move_validity=False,
                                                                       skip_invoice_sync=True)
                line_ids = [
                    move_line.create(receipt.prepare_debit_move_line_vals(move_id=journal_entry_id)),
                    move_line.create(receipt.prepare_credit_move_line_vals(move_id=journal_entry_id)),
                ]
                if receipt.tax_id:
                    line_ids.insert(1, move_line.create(receipt.prepare_debit_tax_move_line_vals(move_id=journal_entry_id)))
                journal_entry_id.action_post()
                receipt.journal_entry_id = journal_entry_id.id
            receipt.state = "posted"

    def prepare_debit_move_line_vals(self, move_id=False):
        for receipt in self:
            line_vals = {
                "account_id": receipt.debit_account_id.id,
                "partner_id": receipt.received_from_partner_id.id if receipt.received_from_partner_id else False,
                "name": receipt.description + " " + f" Debit Line For {receipt.name}" if receipt.description else f"Debit Line For {receipt.name}",
                "analytic_distribution": receipt.debit_analytic_distribution if receipt.debit_analytic_distribution else False,
                "cs_project_id": receipt.debit_cs_project_id.id if receipt.debit_cs_project_id else False,
                "debit": receipt.amount if receipt.tax_id else receipt.total_amount,
                'tax_ids': receipt.tax_id.ids if receipt.tax_id else False,
                "credit": 0.0,
            }
            if move_id:
                line_vals.update({"move_id": move_id.id})
            return line_vals

    def prepare_debit_tax_move_line_vals(self, move_id=False):
        for receipt in self:
            default_account_tax_id = receipt.tax_id.mapped('refund_repartition_line_ids.account_id')
            repartition_tax_line = receipt.tax_id.refund_repartition_line_ids.filtered(
                lambda l: l.repartition_type == 'tax' and l.account_id)
            if not default_account_tax_id or not repartition_tax_line:
                raise ValidationError(f"Please Set Account In The {receipt.tax_id.name}")
            line_vals = {
                "account_id": default_account_tax_id.id,
                "name": receipt.description + " " + f"Debit Tax Line For {receipt.name}" if receipt.description else f"Debit Tax Line For {receipt.name}",
                "analytic_distribution": receipt.debit_analytic_distribution if receipt.debit_analytic_distribution else False,
                "cs_project_id": receipt.debit_cs_project_id.id if receipt.debit_cs_project_id else False,
                'display_type': 'tax',
                'tax_repartition_line_id': repartition_tax_line.id,
                'tax_line_id': receipt.tax_id.id,
                "debit": receipt.amount_tax,
            }
            if move_id:
                line_vals.update({"move_id": move_id.id})
            return line_vals

    def prepare_credit_move_line_vals(self, move_id=False):
        for receipt in self:
            line_vals = {
                "account_id": receipt.credit_account_id.id,
                "name": receipt.description + " " + f" Credit Line For {receipt.name}" if receipt.description else f"Credit Line For {receipt.name}",
                "analytic_distribution": receipt.credit_analytic_distribution if receipt.credit_analytic_distribution else False,
                "cs_project_id": receipt.credit_cs_project_id.id if receipt.credit_cs_project_id else False,
                "credit": receipt.total_amount,
                "debit": 0.0,
            }
            if move_id:
                line_vals.update({"move_id": move_id.id})
            return line_vals

    def open_journal_entry(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Entry'),
            'res_model': 'account.move',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': self.journal_entry_id.id,
        }

    # endregion [Actions]

    # region [Compute Methods]

    def _convert_to_tax_base_line_dict(self):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            partner=self.received_from_partner_id if self.received_from_partner_id else False,
            currency=self.currency_id,
            product=False,
            taxes=self.tax_id,
            price_unit=self.amount,
            quantity=1,
            discount=0,
            price_subtotal=self.amount,
        )

    @api.depends('amount', 'tax_id', 'received_from_partner_id', 'currency_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for receipt in self:
            if receipt.tax_id and receipt.currency_id:
                tax_results = self.env['account.tax']._compute_taxes([
                    receipt._convert_to_tax_base_line_dict()
                ])
                totals = list(tax_results['totals'].values())[0]
                amount_untaxed = totals['amount_untaxed']
                amount_tax = totals['amount_tax']

                receipt.update({
                    'amount_tax': amount_tax,
                    'total_amount': amount_untaxed + amount_tax,
                })
            else:
                receipt.amount_tax = 0.0
                receipt.total_amount = receipt.amount

    @api.depends("debit_account_id", "debit_account_id.cash_equivalents_subcategory", "debit_account_id.accounts_receivable_subcategory")
    @api.onchange("debit_account_id", "debit_account_id.cash_equivalents_subcategory", "debit_account_id.accounts_receivable_subcategory")
    def _compute_check_debit_cost_centers_block(self):
        for rec in self:
            if rec.debit_account_id and rec.debit_account_id.cash_equivalents_subcategory == "petty_cash" and rec.debit_account_id.accounts_receivable_subcategory == "employee_advances":
                rec.check_debit_cost_centers_block = True
            else:
                rec.check_debit_cost_centers_block = False

    @api.depends("credit_account_id", "credit_account_id.cash_equivalents_subcategory",
                 "credit_account_id.accounts_receivable_subcategory")
    @api.onchange("credit_account_id", "credit_account_id.cash_equivalents_subcategory",
                  "credit_account_id.accounts_receivable_subcategory")
    def _compute_check_credit_cost_centers_block(self):
        for rec in self:
            if rec.credit_account_id and rec.credit_account_id.cash_equivalents_subcategory == "petty_cash" and rec.credit_account_id.accounts_receivable_subcategory == "employee_advances":
                rec.check_credit_cost_centers_block = True
            else:
                rec.check_credit_cost_centers_block = False

    # endregion [Compute Methods]

    # region [Debit Analytic Distribution Methods]

    def _inverse_debit_analytic_distribution(self):
        """ Unlink and recreate analytic_lines when modifying the distribution."""
        lines_to_modify = self.env['pr.payment.receipt'].browse([
            line.id for line in self if line.state == "posted"
        ])
        lines_to_modify.debit_analytic_line_ids.unlink()
        lines_to_modify._create_debit_analytic_lines()

    def _create_debit_analytic_lines(self):
        """ Create analytic items upon validation of an account.move.line having an analytic distribution.
        """
        # self._validate_analytic_distribution()
        analytic_line_vals = []
        for line in self:
            analytic_line_vals.extend(line._prepare_debit_analytic_lines())

        self.env['account.analytic.line'].create(analytic_line_vals)

    def _prepare_debit_analytic_lines(self):
        self.ensure_one()
        analytic_line_vals = []
        if self.debit_analytic_distribution:
            # distribution_on_each_plan corresponds to the proportion that is distributed to each plan to be able to
            # give the real amount when we achieve a 100% distribution
            distribution_on_each_plan = {}
            for account_ids, distribution in self.debit_analytic_distribution.items():
                line_values = self._prepare_debit_analytic_distribution_line(float(distribution), account_ids, distribution_on_each_plan)
                if not self.currency_id.is_zero(line_values.get('amount')):
                    analytic_line_vals.append(line_values)
        return analytic_line_vals

    def _prepare_debit_analytic_distribution_line(self, distribution, account_ids, distribution_on_each_plan):
        """ Prepare the values used to create() an account.analytic.line upon validation of an account.move.line having
            analytic tags with analytic distribution.
        """
        self.ensure_one()
        account_field_values = {}
        decimal_precision = self.env['decimal.precision'].precision_get('Percentage Analytic')
        amount = 0
        for account in self.env['account.analytic.account'].browse(map(int, account_ids.split(","))).exists():
            distribution_plan = distribution_on_each_plan.get(account.root_plan_id, 0) + distribution
            if float_compare(distribution_plan, 100, precision_digits=decimal_precision) == 0:
                amount = -self.total_amount * (100 - distribution_on_each_plan.get(account.root_plan_id, 0)) / 100.0
            else:
                amount = -self.total_amount * distribution / 100.0
            distribution_on_each_plan[account.root_plan_id] = distribution_plan
            account_field_values[account.plan_id._column_name()] = account.id
        default_name = self.name or self.description
        return {
            'name': default_name,
            'date': self.receipt_date,
            **account_field_values,
            'unit_amount': 1,
            'amount': amount,
            'general_account_id': self.debit_account_id.id,
            'ref': self.name,
            'debit_payment_receipt_id': self.id,
            'user_id': self._uid,
            'company_id': self.company_id.id or self.env.company.id,
        }

    # endregion [Debit Analytic Distribution Methods]

    # region [Credit Analytic Distribution Methods]

    def _inverse_credit_analytic_distribution(self):
        """ Unlink and recreate analytic_lines when modifying the distribution."""
        lines_to_modify = self.env['pr.payment.receipt'].browse([
            line.id for line in self if line.state == "posted"
        ])
        lines_to_modify.credit_analytic_line_ids.unlink()
        lines_to_modify._create_credit_analytic_lines()

    def _create_credit_analytic_lines(self):
        """ Create analytic items upon validation of an account.move.line having an analytic distribution.
        """
        # self._validate_analytic_distribution()
        analytic_line_vals = []
        for line in self:
            analytic_line_vals.extend(line._prepare_credit_analytic_lines())

        self.env['account.analytic.line'].create(analytic_line_vals)

    def _prepare_credit_analytic_lines(self):
        self.ensure_one()
        analytic_line_vals = []
        if self.credit_analytic_distribution:
            # distribution_on_each_plan corresponds to the proportion that is distributed to each plan to be able to
            # give the real amount when we achieve a 100% distribution
            distribution_on_each_plan = {}
            for account_ids, distribution in self.credit_analytic_distribution.items():
                line_values = self._prepare_credit_analytic_distribution_line(float(distribution), account_ids,
                                                                             distribution_on_each_plan)
                if not self.currency_id.is_zero(line_values.get('amount')):
                    analytic_line_vals.append(line_values)
        return analytic_line_vals

    def _prepare_credit_analytic_distribution_line(self, distribution, account_ids, distribution_on_each_plan):
        """ Prepare the values used to create() an account.analytic.line upon validation of an account.move.line having
            analytic tags with analytic distribution.
        """
        self.ensure_one()
        account_field_values = {}
        decimal_precision = self.env['decimal.precision'].precision_get('Percentage Analytic')
        amount = 0
        for account in self.env['account.analytic.account'].browse(map(int, account_ids.split(","))).exists():
            distribution_plan = distribution_on_each_plan.get(account.root_plan_id, 0) + distribution
            if float_compare(distribution_plan, 100, precision_digits=decimal_precision) == 0:
                amount = -self.total_amount * (100 - distribution_on_each_plan.get(account.root_plan_id, 0)) / 100.0
            else:
                amount = -self.total_amount * distribution / 100.0
            distribution_on_each_plan[account.root_plan_id] = distribution_plan
            account_field_values[account.plan_id._column_name()] = account.id
        default_name = self.name or self.description
        return {
            'name': default_name,
            'date': self.receipt_date,
            **account_field_values,
            'unit_amount': 1,
            'amount': amount,
            'general_account_id': self.credit_account_id.id,
            'ref': self.name,
            'credit_payment_receipt_id': self.id,
            'user_id': self._uid,
            'company_id': self.company_id.id or self.env.company.id,
        }

    # endregion [Credit Analytic Distribution Methods]

    # region [Crud]

    @api.model
    def create(self, vals):
        '''
        We Inherit Create Method To Pass Sequence Fo Field Name
        '''
        res = super().create(vals)
        res.name = self.env['ir.sequence'].next_by_code('account.payment.receipt.seq.code') or ''
        return res

    def unlink(self):
        if self.state != 'draft':
            raise ValidationError("The Receipt Should Be Draft To Can Delete !!")
        return super().unlink()

    # endregion [Crud]
