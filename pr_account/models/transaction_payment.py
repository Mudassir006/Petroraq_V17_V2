
from odoo import models, fields, api, _, Command
from odoo.exceptions import UserError, ValidationError
from odoo.tools import frozendict, format_date, float_compare, Query


class TransactionPayment(models.Model):
    # region [Initial]
    _name = "pr.transaction.payment"
    _description = "Transaction Payment"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "id"
    _rec_name = 'name'
    # endregion [Initial]

    # region [Fields]

    name = fields.Char(string='Payment Number', required=False, translate=True)
    company_id = fields.Many2one('res.company', string='Company', index=True, required=True, default=lambda self: self.env.company,
                                 tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id', store=True, tracking=True)
    payment_to_partner_id = fields.Many2one('res.partner', string='Send To', tracking=True)
    debit_account_id = fields.Many2one('account.account', string='Debit Account', required=True, index=True, tracking=True)
    debit_account_name = fields.Char(string='Debit Account Name', related="debit_account_id.name", store=True, tracking=True)
    debit_cs_project_id = fields.Many2one("account.analytic.account", string="Debit Project",
                                          domain="[('analytic_plan_type', '=', 'project')]", tracking=True)
    check_debit_cost_centers_block = fields.Boolean(compute="_compute_check_debit_cost_centers_block")
    # === Analytic fields === #
    debit_analytic_line_ids = fields.One2many(
        comodel_name='account.analytic.line', inverse_name='debit_transaction_payment_id',
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
        comodel_name='account.analytic.line', inverse_name='credit_transaction_payment_id',
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
    payment_date = fields.Date(string="Payment Date", required=True, default=fields.Date.today, tracking=True)
    payment_mode = fields.Selection([
        ("cash", "Cash"),
        ("cheque", "Cheque"),
        ("deposit", "Deposit"),
        ("e_transfer", "e Transfer"),
    ], string="Payment Mode", required=True, tracking=True)
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
        for payment in self:
            if payment.company_id and payment.company_id.id != self.env.company.id:
                raise ValidationError("You Should Select The Current Company !!, Please Check")
    # endregion [Constrains]

    # region [Actions]

    def action_draft(self):
        for payment in self:
            if payment.journal_entry_id and payment.journal_entry_id.state != "draft":
                payment.journal_entry_id.sudo().button_draft()
                payment.journal_entry_id.unlink()
            payment.state = "draft"

    def action_cancel(self):
        for payment in self:
            if payment.journal_entry_id and payment.journal_entry_id.state != "cancel":
                payment.journal_entry_id.sudo().button_draft()
                payment.journal_entry_id.sudo().button_cancel()
            payment.state = "cancel"

    def action_post(self):
        for payment in self:
            journal_entry_id = self.env['account.move'].create({
                'name': payment.name,
                'ref': payment.name,
                'date': payment.payment_date,
                'move_type': 'entry',
            })
            if journal_entry_id:
                journal_entry_id = journal_entry_id.with_context(check_move_validity=False)
                move_line = self.env['account.move.line'].with_context(check_move_validity=False,
                                                                       skip_invoice_sync=True)
                line_ids = [
                    move_line.create(payment.prepare_debit_move_line_vals(move_id=journal_entry_id)),
                    move_line.create(payment.prepare_credit_move_line_vals(move_id=journal_entry_id)),
                ]
                if payment.tax_id:
                    line_ids.insert(1, move_line.create(payment.prepare_debit_tax_move_line_vals(move_id=journal_entry_id)))
                journal_entry_id.action_post()
                payment.journal_entry_id = journal_entry_id.id
            payment.state = "posted"

    def prepare_debit_move_line_vals(self, move_id=False):
        for payment in self:
            line_vals = {
                "account_id": payment.debit_account_id.id,
                "name": payment.description + " " + f" Debit Line For {payment.name}" if payment.description else f"Debit Line For {payment.name}",
                "analytic_distribution": payment.debit_analytic_distribution if payment.debit_analytic_distribution else False,
                "cs_project_id": payment.debit_cs_project_id.id if payment.debit_cs_project_id else False,
                "debit": payment.amount if payment.tax_id else payment.total_amount,
                'tax_ids': payment.tax_id.ids if payment.tax_id else False,
                "credit": 0.0,
            }
            if move_id:
                line_vals.update({"move_id": move_id.id})
            return line_vals

    def prepare_debit_tax_move_line_vals(self, move_id=False):
        for payment in self:
            default_account_tax_id = payment.tax_id.mapped('invoice_repartition_line_ids.account_id')
            repartition_tax_line = payment.tax_id.invoice_repartition_line_ids.filtered(
                lambda l: l.repartition_type == 'tax' and l.account_id)
            if not default_account_tax_id or not repartition_tax_line:
                raise ValidationError(f"Please Set Account In The {payment.tax_id.name}")
            line_vals = {
                "account_id": default_account_tax_id.id,
                "name": payment.description + " " + f"Debit Tax Line For {payment.name}" if payment.description else f"Debit Tax Line For {payment.name}",
                "analytic_distribution": payment.debit_analytic_distribution if payment.debit_analytic_distribution else False,
                "cs_project_id": payment.debit_cs_project_id.id if payment.debit_cs_project_id else False,
                'display_type': 'tax',
                'tax_repartition_line_id': repartition_tax_line.id,
                'tax_line_id': payment.tax_id.id,
                "debit": payment.amount_tax,
            }
            if move_id:
                line_vals.update({"move_id": move_id.id})
            return line_vals

    def prepare_credit_move_line_vals(self, move_id=False):
        for payment in self:
            line_vals = {
                "account_id": payment.credit_account_id.id,
                "partner_id": payment.payment_to_partner_id.id if payment.payment_to_partner_id else False,
                "name": payment.description + " " + f" Credit Line For {payment.name}" if payment.description else f"Credit Line For {payment.name}",
                "analytic_distribution": payment.credit_analytic_distribution if payment.credit_analytic_distribution else False,
                "cs_project_id": payment.credit_cs_project_id.id if payment.credit_cs_project_id else False,
                "credit": payment.total_amount,
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
            partner=self.payment_to_partner_id if self.payment_to_partner_id else False,
            currency=self.currency_id,
            product=False,
            taxes=self.tax_id,
            price_unit=self.amount,
            quantity=1,
            discount=0,
            price_subtotal=self.amount,
        )

    @api.depends('amount', 'tax_id', 'payment_to_partner_id', 'currency_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for payment in self:
            if payment.tax_id and payment.currency_id:
                tax_results = self.env['account.tax']._compute_taxes([
                    payment._convert_to_tax_base_line_dict()
                ])
                totals = list(tax_results['totals'].values())[0]
                amount_untaxed = totals['amount_untaxed']
                amount_tax = totals['amount_tax']

                payment.update({
                    'amount_tax': amount_tax,
                    'total_amount': amount_untaxed + amount_tax,
                })
            else:
                payment.amount_tax = 0.0
                payment.total_amount = payment.amount

    @api.depends("debit_account_id", "debit_account_id.cash_equivalents_subcategory",
                 "debit_account_id.accounts_receivable_subcategory")
    @api.onchange("debit_account_id", "debit_account_id.cash_equivalents_subcategory",
                  "debit_account_id.accounts_receivable_subcategory")
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
        lines_to_modify = self.env['pr.transaction.payment'].browse([
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
            'date': self.payment_date,
            **account_field_values,
            'unit_amount': 1,
            'amount': amount,
            'general_account_id': self.debit_account_id.id,
            'ref': self.name,
            'debit_transaction_payment_id': self.id,
            'user_id': self._uid,
            'company_id': self.company_id.id or self.env.company.id,
        }

    # endregion [Debit Analytic Distribution Methods]

    # region [Credit Analytic Distribution Methods]

    def _inverse_credit_analytic_distribution(self):
        """ Unlink and recreate analytic_lines when modifying the distribution."""
        lines_to_modify = self.env['pr.transaction.payment'].browse([
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
            'date': self.payment_date,
            **account_field_values,
            'unit_amount': 1,
            'amount': amount,
            'general_account_id': self.credit_account_id.id,
            'ref': self.name,
            'credit_transaction_payment_id': self.id,
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
        res.name = self.env['ir.sequence'].next_by_code('account.transaction.payment.seq.code') or ''
        return res

    def unlink(self):
        if self.state != 'draft':
            raise ValidationError("The Payment Should Be Draft To Can Delete !!")
        return super().unlink()

    # endregion [Crud]
