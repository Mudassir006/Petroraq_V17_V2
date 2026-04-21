from odoo import api, fields, models, _, Command
from odoo.tools import  float_compare
from odoo.exceptions import ValidationError
import  logging
_logger = logging.getLogger(__name__)



class AccountCashPayment(models.Model):
    # region [Initial]
    _name = 'pr.account.cash.payment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Cash Payment'
    _order = "id"
    _rec_name = 'name'
    # endregion [Initial]

    # region [Fields]

    name = fields.Char(string="Number", required=False, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', index=True, required=True,
                                 default=lambda self: self.env.company,
                                 tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id', store=True,
                                  tracking=True)
    account_id = fields.Many2one('account.account', string='Code', required=True,
                                 ondelete='restrict', tracking=True, index=True,)
    account_name = fields.Char(string='Name', related="account_id.name", store=True,
                                     tracking=True)
    # === Analytic fields === #
    analytic_line_ids = fields.One2many(
        comodel_name='account.analytic.line', inverse_name='cash_payment_id',
        string='Analytic lines',
    )
    analytic_distribution = fields.Json(
        string="Cost Centers",
        inverse="_inverse_analytic_distribution",
    )
    analytic_precision = fields.Integer(
        store=False,
        default=lambda self: self.env["decimal.precision"].precision_get(
            "Percentage Analytic"
        ),
    )
    description = fields.Text(string="Description", required=False, tracking=True)
    accounting_date = fields.Date(string="Date", required=True, tracking=True, default=fields.Date.today)
    state = fields.Selection([
        ("draft", "Draft"),
        ("submit", "Submitted"),
        ("finance_approve", "Accounts Approval"),
        ("posted", "Finance Approval"),
        ("cancel", "Cancelled"),
    ], string="Status", tracking=True, default="draft")
    accounting_manager_state = fields.Selection([
        ("draft", "Draft"),
        ("submit", "Pending Approval"),
        ("finance_approve", "Pending Approval"),
        ("posted", "Posted"),
        ("cancel", "Cancelled"),
    ], string="Acc Man Status", tracking=True, default="draft")
    cash_payment_line_ids = fields.One2many("pr.account.cash.payment.line", "cash_payment_id", string="Cash Payment Lines")
    total_amount = fields.Float(string="Amount", compute="_compute_total_amount", store=True, tracking=True)
    approved_amount = fields.Float(string="Approved Amount", compute="_compute_approved_amount", store=True,
                                   tracking=True)
    rejected_amount = fields.Float(string="Rejected Amount", compute="_compute_rejected_amount", store=True,
                                   tracking=True)
    journal_entry_id = fields.Many2one("account.move", string="Journal Entry", readonly=True, tracking=True)
    check_process_state = fields.Boolean(compute="_compute_check_process_state")

    # endregion [Fields]

    # region [Constrains]

    @api.constrains("company_id")
    def _check_company(self):
        for cash_payment in self:
            if cash_payment.company_id and cash_payment.company_id.id != self.env.company.id:
                raise ValidationError("You Should Select The Current Company !!, Please Check"
                                      "")

    # endregion [Constrains

    # region [Compute Methods]

    @api.depends("cash_payment_line_ids", "cash_payment_line_ids.total_amount", "cash_payment_line_ids.state")
    def _compute_total_amount(self):
        for cash_payment in self:
            if cash_payment.cash_payment_line_ids:
                cash_payment.total_amount = sum(cash_payment.cash_payment_line_ids.mapped("total_amount"))
            else:
                cash_payment.total_amount = 0.0

    @api.depends("cash_payment_line_ids", "cash_payment_line_ids.total_amount", "cash_payment_line_ids.state")
    def _compute_approved_amount(self):
        for rec in self:
            if rec.cash_payment_line_ids:
                rec.approved_amount = sum(
                    rec.cash_payment_line_ids.filtered(lambda l: l.state == "approve").mapped("total_amount"))
            else:
                rec.approved_amount = 0.0

    @api.depends("cash_payment_line_ids", "cash_payment_line_ids.total_amount", "cash_payment_line_ids.state")
    def _compute_rejected_amount(self):
        for rec in self:
            if rec.cash_payment_line_ids:
                rec.rejected_amount = sum(
                    rec.cash_payment_line_ids.filtered(lambda l: l.state == "reject").mapped("total_amount"))
            else:
                rec.rejected_amount = 0.0

    @api.depends("cash_payment_line_ids", "cash_payment_line_ids.state")
    def _compute_check_process_state(self):
        for rec in self:
            if rec.cash_payment_line_ids:
                if all(line.state in ["approve", "reject"] for line in rec.cash_payment_line_ids):
                    rec.check_process_state = True
                else:
                    rec.check_process_state = False
            else:
                rec.check_process_state = False

    # endregion [Compute Methods]

    # region [Actions]

    def make_all_draft(self):
        cash_payment_ids = self.env["pr.account.cash.payment"].sudo().search([("id", "!=", False)])
        if cash_payment_ids:
            for rec in cash_payment_ids:
                rec.sudo().action_post()

    def action_draft(self):
        """
        Reset CPV/BPV to draft state
        """
        for record in self:
            # Check if journal entry exists and is not already deleted
            if record.journal_entry_id and record.journal_entry_id.exists():
                try:
                    # Unpost if posted
                    if record.journal_entry_id.state == "posted":
                        record.journal_entry_id.sudo().button_draft()

                    # Delete the journal entry
                    record.journal_entry_id.sudo().unlink()
                except Exception as e:
                    _logger.warning(f"Failed to unlink journal entry for {record.name}: {str(e)}")

            # ✅ CRITICAL: Clear the journal_entry_id field
            record.journal_entry_id = False

            # Reset states
            record.state = "draft"
            record.accounting_manager_state = "draft"

    def action_submit(self):
        for rec in self:
            if rec.cash_payment_line_ids:
                for line in rec.cash_payment_line_ids:
                    line.sudo().write({"state": "submit"})
            rec.state = "submit"
            rec.accounting_manager_state = "submit"

    def action_finance_approve(self):
        for bank_payment in self:
            bank_payment.state = "finance_approve"
            bank_payment.accounting_manager_state = "finance_approve"

    def action_post(self):
        """
        Post CPV/BPV and create journal entry
        """
        for cash_payment in self:
            # ✅ CHECK 1: Prevent duplicate posting - check if valid JE exists
            if cash_payment.journal_entry_id and cash_payment.journal_entry_id.exists():
                # Journal entry already exists and is not deleted
                if cash_payment.journal_entry_id.state == 'draft':
                    # Check if it's valid before posting
                    total_debit = sum(line.debit for line in cash_payment.journal_entry_id.line_ids)
                    total_credit = sum(line.credit for line in cash_payment.journal_entry_id.line_ids)

                    if total_debit == 0 and total_credit == 0:
                        # It's a zero-amount JE, delete it and create new
                        cash_payment.journal_entry_id.unlink()
                        cash_payment.journal_entry_id = False
                    else:
                        # Valid JE exists, just post it
                        cash_payment.journal_entry_id.action_post()
                        cash_payment.state = "posted"
                        cash_payment.accounting_manager_state = "posted"
                        continue
                elif cash_payment.journal_entry_id.state == 'posted':
                    # Already posted
                    cash_payment.state = "posted"
                    cash_payment.accounting_manager_state = "posted"
                    continue
            elif cash_payment.journal_entry_id and not cash_payment.journal_entry_id.exists():
                # Broken reference - clear it
                cash_payment.journal_entry_id = False

            # ✅ CHECK 2: Validate there are approved lines
            approved_lines = cash_payment.cash_payment_line_ids.filtered(lambda l: l.state == "approve")
            if not approved_lines:
                # Get all line states for better error message
                line_states = cash_payment.cash_payment_line_ids.mapped('state')
                raise ValidationError(
                    f"Cannot post {cash_payment.name}: No approved payment lines found.\n\n"
                    f"You have {len(cash_payment.cash_payment_line_ids)} line(s) with states: {', '.join(set(line_states))}\n\n"
                    f"Please approve at least one payment line before posting.\n\n"
                    f"Line details:\n" +
                    "\n".join([f"  • Line {i + 1}: {line.description or 'No description'} - State: {line.state}"
                               for i, line in enumerate(cash_payment.cash_payment_line_ids)])
                )

            # ✅ CHECK 3: Validate approved amount
            if not cash_payment.approved_amount or cash_payment.approved_amount <= 0:
                raise ValidationError(
                    f"Cannot post {cash_payment.name}: Approved amount must be greater than zero.\n"
                    f"Current approved amount: {cash_payment.approved_amount}"
                )

            # ✅ CHECK 4: Check for existing JE with same reference (defensive check)
            existing_move = self.env['account.move'].search([
                ('ref', '=', cash_payment.name),
                ('state', '!=', 'cancel')
            ], limit=1)

            if existing_move:
                # Check if it's a valid JE or a zero-amount duplicate
                total_debit = sum(line.debit for line in existing_move.line_ids)
                total_credit = sum(line.credit for line in existing_move.line_ids)

                if total_debit == 0 and total_credit == 0:
                    # It's a zero-amount duplicate, delete it
                    if existing_move.state == 'posted':
                        existing_move.button_draft()
                    existing_move.unlink()
                    _logger.warning(
                        f"CPV/BPV {cash_payment.name}: Deleted existing zero-amount journal entry {existing_move.name}"
                    )
                else:
                    # Valid JE exists, link it
                    cash_payment.journal_entry_id = existing_move.id
                    if existing_move.state == 'draft':
                        existing_move.action_post()
                    cash_payment.state = "posted"
                    cash_payment.accounting_manager_state = "posted"
                    _logger.info(
                        f"CPV/BPV {cash_payment.name}: Linked to existing journal entry {existing_move.name}"
                    )
                    continue

            # ✅ CHECK 5: Validate we have payment lines
            if not cash_payment.cash_payment_line_ids:
                raise ValidationError(
                    f"Cannot post {cash_payment.name}: No payment lines found."
                )

            # Create the journal entry
            journal_entry_id = self.env['account.move'].create({
                'ref': cash_payment.name,
                'date': cash_payment.accounting_date,
                'move_type': 'entry',
            })

            if journal_entry_id:
                journal_entry_id = journal_entry_id.with_context(check_move_validity=False)
                move_line = self.env['account.move.line'].with_context(
                    check_move_validity=False,
                    skip_invoice_sync=True
                )

                # Create credit line (payment account)
                credit_line = move_line.create(
                    cash_payment.prepare_credit_move_line_vals(move_id=journal_entry_id)
                )
                line_ids = [credit_line]

                # Create debit lines for APPROVED lines only
                debit_amount = 0.0
                for line in approved_lines:
                    debit_line = move_line.create(
                        line.prepare_debit_move_line_vals(move_id=journal_entry_id)
                    )
                    line_ids.append(debit_line)
                    debit_amount += debit_line.debit

                    # Create tax line if applicable
                    if line.tax_id:
                        tax_line = move_line.create(
                            line.prepare_debit_tax_move_line_vals(move_id=journal_entry_id)
                        )
                        line_ids.append(tax_line)
                        debit_amount += tax_line.debit

                # ✅ CHECK 6: Validate the JE is balanced and non-zero
                credit_amount = credit_line.credit

                if debit_amount == 0 or credit_amount == 0:
                    # Something went wrong, delete the JE
                    journal_entry_id.unlink()
                    raise ValidationError(
                        f"Cannot post {cash_payment.name}: Journal entry would have zero amount.\n"
                        f"Debit: {debit_amount}, Credit: {credit_amount}\n"
                        f"This usually means no lines are approved or approved amount is zero."
                    )

                if abs(debit_amount - credit_amount) > 0.01:  # Allow small rounding differences
                    journal_entry_id.unlink()
                    raise ValidationError(
                        f"Cannot post {cash_payment.name}: Journal entry is not balanced.\n"
                        f"Total Debit: {debit_amount}\n"
                        f"Total Credit: {credit_amount}\n"
                        f"Difference: {abs(debit_amount - credit_amount)}"
                    )

                # Post the journal entry
                try:
                    journal_entry_id.action_post()
                    cash_payment.journal_entry_id = journal_entry_id.id
                except Exception as e:
                    # If posting fails, delete the JE and raise error
                    journal_entry_id.unlink()
                    raise ValidationError(
                        f"Failed to post journal entry for {cash_payment.name}: {str(e)}"
                    )

            # Update payment state
            cash_payment.state = "posted"
            cash_payment.accounting_manager_state = "posted"

    def action_cancel(self):
        for cash_payment in self:
            if cash_payment.journal_entry_id and cash_payment.journal_entry_id.state != "cancel":
                cash_payment.journal_entry_id.sudo().button_draft()
                cash_payment.journal_entry_id.sudo().button_cancel()
            cash_payment.state = "cancel"
            cash_payment.accounting_manager_state = "cancel"

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

    def prepare_credit_move_line_vals(self, move_id=False):
        """Prepare credit line values"""
        self.ensure_one()

        line_vals = {
            "account_id": self.account_id.id,
            "name": self.description if self.description else f"Credit For {self.name}",
            "analytic_distribution": self.analytic_distribution if self.analytic_distribution else False,
            "credit": self.approved_amount,
            "debit": 0.0,
        }
        if move_id:
            line_vals.update({"move_id": move_id.id})
        return line_vals

    def action_approve_remaining_lines(self):
        for rec in self:
            for line in rec.cash_payment_line_ids:
                if line.state == "submit":
                    line.sudo().write({"state": "approve"})

    def action_reject_remaining_lines(self):
        for rec in self:
            for line in rec.cash_payment_line_ids:
                if line.state == "submit":
                    line.sudo().write({"state": "reject"})

    # endregion [Actions]

    # region [Analytic Distribution Methods]

    def _inverse_analytic_distribution(self):
        """ Unlink and recreate analytic_lines when modifying the distribution."""
        lines_to_modify = self.env['pr.account.cash.payment'].browse([
            line.id for line in self if line.state == "posted"
        ])
        lines_to_modify.analytic_line_ids.unlink()
        lines_to_modify._create_analytic_lines()

    def _create_analytic_lines(self):
        """ Create analytic items upon validation of an account.move.line having an analytic distribution.
        """
        # self._validate_analytic_distribution()
        analytic_line_vals = []
        for cash_payment in self:
            analytic_line_vals.extend(cash_payment._prepare_analytic_lines())

        self.env['account.analytic.line'].create(analytic_line_vals)

    def _prepare_analytic_lines(self):
        self.ensure_one()
        analytic_line_vals = []
        if self.analytic_distribution:
            # distribution_on_each_plan corresponds to the proportion that is distributed to each plan to be able to
            # give the real amount when we achieve a 100% distribution
            distribution_on_each_plan = {}
            for account_ids, distribution in self.analytic_distribution.items():
                line_values = self._prepare_analytic_distribution_line(float(distribution), account_ids,
                                                                       distribution_on_each_plan)
                if not self.currency_id.is_zero(line_values.get('amount')):
                    analytic_line_vals.append(line_values)
        return analytic_line_vals

    def _prepare_analytic_distribution_line(self, distribution, account_ids, distribution_on_each_plan):
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
            'date': self.accounting_date,
            **account_field_values,
            'unit_amount': 1,
            'amount': amount,
            'general_account_id': self.account_id.id,
            'ref': self.name,
            'cash_payment_id': self.id,
            'user_id': self._uid,
            'company_id': self.company_id.id or self.env.company.id,
        }

    # endregion [Analytic Distribution Methods]

    # region [Crud]

    @api.model
    def create(self, vals):
        '''
        We Inherit Create Method To Pass Sequence Fo Field Name
        '''
        res = super().create(vals)
        res.name = self.env['ir.sequence'].next_by_code('pr.account.cash.payment.seq.code') or ''
        return res

    def unlink(self):
        if self.state != 'draft':
            raise ValidationError("This Cash Payment Should Be Draft To Can Delete !!")
        return super().unlink()

    # endregion [Crud]

class AccountCashPaymentLine(models.Model):
    # region [Initial]
    _name = 'pr.account.cash.payment.line'
    _description = 'Cash Payment Line'
    # endregion [Initial]

    # region [Fields]

    cash_payment_id = fields.Many2one('pr.account.cash.payment', 'Cash Payment', required=True)
    company_id = fields.Many2one('res.company', string='Company', related="cash_payment_id.company_id", store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', related="cash_payment_id.currency_id", store=True)
    cs_project_id = fields.Many2one("account.analytic.account", string="Project",
                                    domain="[('analytic_plan_type', '=', 'project')]", tracking=True)
    partner_id = fields.Many2one('res.partner', string='Project Manager', tracking=True)
    account_id = fields.Many2one('account.account', string='Code', required=True,
                                 ondelete='restrict', tracking=True, index=True)
    account_name = fields.Char(string='Name', related="account_id.name", store=True,
                               tracking=True)
    description = fields.Text(string="Description", required=False, tracking=True)
    reference_number = fields.Char(string="Reference Number", required=False)
    # === Analytic fields === #
    analytic_line_ids = fields.One2many(
        comodel_name='account.analytic.line', inverse_name='cash_payment_line_id',
        string='Analytic lines',
    )
    analytic_distribution = fields.Json(
        string="Cost Centers",
        inverse="_inverse_analytic_distribution",
    )
    analytic_precision = fields.Integer(
        related="cash_payment_id.analytic_precision",
        store=False,
    )
    amount = fields.Float(string="Amount", tracking=True)
    tax_id = fields.Many2one('account.tax', string='Taxes', ondelete='restrict', check_company=True, domain="[('type_tax_use', '=', 'purchase')]")
    amount_tax = fields.Float(string="Tax Amount", tracking=True, compute="_compute_amount", store=True)
    total_amount = fields.Float(string="Total Amount", tracking=True, compute="_compute_amount", store=True)
    state = fields.Selection([
        ("draft", "Draft"),
        ("submit", "Submitted"),
        ("approve", "Approved"),
        ("reject", "Rejected"),
    ], string="Status", default="draft", tracking=True)
    parent_state = fields.Selection([
        ("draft", "Draft"),
        ("submit", "Submitted"),
        ("finance_approve", "Accounts Approval"),
        ("posted", "Finance Approval"),
        ("cancel", "Cancelled"),
    ], related="cash_payment_id.state", store=True, string="Parent Status")
    check_cost_centers_block = fields.Boolean(compute="_compute_check_cost_centers_block")
    # endregion [Fields]

    # region [Onchange Methods]

    @api.onchange("account_id")
    def _onchange_account_id(self):
        for line in self:
            if line.account_id:
                line.analytic_distribution = False
                line.partner_id = False

    @api.onchange("cs_project_id")
    def _onchange_cs_project_id(self):
        for line in self:
            project_ids = self.env["account.analytic.account"].sudo().search(
                [("analytic_plan_type", "=", "project")]).mapped("id")

            analytic_distribution = {}
            if line.cs_project_id:
                # Analytic Distribution
                if line.cs_project_id.department_id:
                    analytic_distribution.update({
                        str(line.cs_project_id.department_id.id): 100.0
                    })
                if line.cs_project_id.section_id:
                    analytic_distribution.update({
                        str(line.cs_project_id.section_id.id): 100.0
                    })
                analytic_distribution.update({
                    str(line.cs_project_id.id): 100.0
                })

                # Project Manager
                if line.cs_project_id.project_partner_id:
                    line.partner_id = line.cs_project_id.project_partner_id.id
            line.analytic_distribution = analytic_distribution
            # Analytic Distribution

    # endregion [Onchange Methods]

    # region [Constrains]

    @api.constrains("amount")
    def _check_amount(self):
        for cash_payment_line in self:
            if cash_payment_line.amount <= 0:
                raise ValidationError("Amount Must Be Greater Than 0 ( Zero ) !!")

    # endregion [Constrains]

    # region [Compute Methods]

    def _convert_to_tax_base_line_dict(self):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            partner=False,
            currency=self.currency_id,
            product=False,
            taxes=self.tax_id,
            price_unit=self.amount,
            quantity=1,
            discount=0,
            price_subtotal=self.amount,
        )

    @api.depends('amount', 'tax_id', 'currency_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for cash_payment_line in self:
            if cash_payment_line.tax_id and cash_payment_line.currency_id:
                tax_results = self.env['account.tax']._compute_taxes([
                    cash_payment_line._convert_to_tax_base_line_dict()
                ])
                totals = list(tax_results['totals'].values())[0]
                amount_untaxed = totals['amount_untaxed']
                amount_tax = totals['amount_tax']

                cash_payment_line.update({
                    'amount_tax': amount_tax,
                    'total_amount': amount_untaxed + amount_tax,
                })
            else:
                cash_payment_line.amount_tax = 0.0
                cash_payment_line.total_amount = cash_payment_line.amount

    # @api.depends("account_id", "account_id.cash_equivalents_subcategory", "account_id.accounts_receivable_subcategory")
    # @api.onchange("account_id", "account_id.cash_equivalents_subcategory", "account_id.accounts_receivable_subcategory")
    @api.depends("account_id", "account_id.main_head")
    @api.onchange("account_id", "account_id.main_head")
    def _compute_check_cost_centers_block(self):
        for line in self:
            if line.account_id and line.account_id.main_head in ["revenue", "expense"]:
                line.check_cost_centers_block = True
            else:
                line.check_cost_centers_block = False

    # endregion [Compute Methods]

    # region [Actions]

    def action_line_approve(self):
        for line in self:
            line.sudo().write({"state": "approve"})

    def action_line_reject(self):
        for line in self:
            line.sudo().write({"state": "reject"})

    # endregion [Actions]

    # region [Move Line Vals]

    def prepare_debit_move_line_vals(self, move_id=False):
        """Prepare debit line values"""
        self.ensure_one()

        line_vals = {
            "account_id": self.account_id.id,
            "partner_id": self.partner_id.id if self.partner_id else False,
            "name": self.description if self.description else f"Debit Line For {self.cash_payment_id.name}",
            "analytic_distribution": self.analytic_distribution if self.analytic_distribution else False,
            "cs_project_id": self.cs_project_id.id if self.cs_project_id else False,
            "debit": self.amount if self.tax_id else self.total_amount,
            'tax_ids': self.tax_id.ids if self.tax_id else False,
            "credit": 0.0,
        }
        if move_id:
            line_vals.update({"move_id": move_id.id})
        return line_vals

    def prepare_debit_tax_move_line_vals(self, move_id=False):
        """Prepare debit tax line values"""
        self.ensure_one()

        default_account_tax_id = self.tax_id.mapped('refund_repartition_line_ids.account_id')
        repartition_tax_line = self.tax_id.refund_repartition_line_ids.filtered(
            lambda l: l.repartition_type == 'tax' and l.account_id
        )

        if not default_account_tax_id or not repartition_tax_line:
            raise ValidationError(f"Please Set Account In The {self.tax_id.name}")

        line_vals = {
            "account_id": default_account_tax_id.id,
            "partner_id": self.partner_id.id if self.partner_id else False,
            "name": self.description if self.description else f"Debit Tax Line For {self.cash_payment_id.name}",
            "analytic_distribution": self.analytic_distribution if self.analytic_distribution else False,
            "cs_project_id": self.cs_project_id.id if self.cs_project_id else False,
            'display_type': 'tax',
            'tax_repartition_line_id': repartition_tax_line.id,
            'tax_line_id': self.tax_id.id,
            "debit": self.amount_tax,
            "credit": 0.0,
        }
        if move_id:
            line_vals.update({"move_id": move_id.id})
        return line_vals

    # endregion [Move Line Vals]

    # region [Analytic Distribution Methods]

    def _inverse_analytic_distribution(self):
        """ Unlink and recreate analytic_lines when modifying the distribution."""
        lines_to_modify = self.env['pr.account.cash.payment.line'].browse([
            line.id for line in self if line.parent_state == "posted"
        ])
        lines_to_modify.analytic_line_ids.unlink()
        lines_to_modify._create_analytic_lines()

    def _create_analytic_lines(self):
        """ Create analytic items upon validation of an account.move.line having an analytic distribution.
        """
        # self._validate_analytic_distribution()
        analytic_line_vals = []
        for cash_payment_line in self:
            analytic_line_vals.extend(cash_payment_line._prepare_analytic_lines())

        self.env['account.analytic.line'].create(analytic_line_vals)

    def _prepare_analytic_lines(self):
        self.ensure_one()
        analytic_line_vals = []
        if self.analytic_distribution:
            # distribution_on_each_plan corresponds to the proportion that is distributed to each plan to be able to
            # give the real amount when we achieve a 100% distribution
            distribution_on_each_plan = {}
            for account_ids, distribution in self.analytic_distribution.items():
                line_values = self._prepare_analytic_distribution_line(float(distribution), account_ids,
                                                                             distribution_on_each_plan)
                if not self.currency_id.is_zero(line_values.get('amount')):
                    analytic_line_vals.append(line_values)
        return analytic_line_vals

    def _prepare_analytic_distribution_line(self, distribution, account_ids, distribution_on_each_plan):
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
        default_name = self.description
        return {
            'name': default_name,
            'date': self.cash_payment_id.accounting_date,
            **account_field_values,
            'unit_amount': 1,
            'amount': amount,
            'general_account_id': self.account_id.id,
            'ref': self.cash_payment_id.name,
            'cash_payment_line_id': self.id,
            'user_id': self._uid,
            'company_id': self.company_id.id or self.env.company.id,
        }

    # endregion [Analytic Distribution Methods]

