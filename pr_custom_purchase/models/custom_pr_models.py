from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class CustomPR(models.Model):
    _name = 'custom.pr'
    _description = 'Custom Purchase Requisition'

    name = fields.Char(string="PR Number", readonly=True, copy=False)
    pr_type = fields.Selection(
        [('standard', 'PR'), ('cash', 'Cash PR')],
        string="Type",
        default='standard',
        required=True,
    )
    requested_by = fields.Char(string="Requested By")
    requested_user_id = fields.Many2one('res.users', string="Requested User", readonly=True)
    date_request = fields.Datetime(string="Request Date", default=fields.Datetime.now, required=True, readonly=True)
    description = fields.Text(string="Description")
    department = fields.Char(string="Department")
    supervisor = fields.Char(string="Supervisor")
    supervisor_partner_id = fields.Char(string="supervisor_partner_id")
    required_date = fields.Date(string="Required Date", required=True, readonly=True)
    priority = fields.Selection(
        [("low", "Low"), ("medium", "Medium"), ("high", "High"), ("urgent", "Urgent")],
        string="Priority",
        required=True,
        default="low",
    )
    comments = fields.Text(string="Comments")
    notes = fields.Text(string="Notes")
    rejection_reason = fields.Text(string="Reason for Rejection")
    approval = fields.Selection(
        [("pending", "Pending"), ("rejected", "Rejected"), ("approved", "Approved")],
        default="pending",
        string="Internal Approval",
    )
    wo_variance_requires_approval = fields.Boolean(
        string="WO Variance Requires Approval",
        default=False,
        help="Checked when requested quantity/unit cost exceeds WO product baselines but total amount remains within allowed WO amount.",
    )

    total_excl_vat = fields.Float(
        string="Total Amount",
        compute="_compute_totals",
        store=True,
        currency_field="currency_id",
    )
    vat_amount = fields.Float(
        string="VAT (15%)",
        compute="_compute_totals",
        store=True,
        currency_field="currency_id",
    )
    total_incl_vat = fields.Float(
        string="Total Incl. VAT",
        compute="_compute_totals",
        store=True,
        currency_field="currency_id",
    )
    pr_created = fields.Boolean(string="PR Created", default=False)
    line_ids = fields.One2many('custom.pr.line', 'pr_id', string="PR Lines")
    expense_type = fields.Selection(
        [('opex', 'Opex'), ('capex', 'Capex')],
        string='Expense Type',
        required=True,
    )
    expense_bucket_id = fields.Many2one(
        'crossovered.budget',
        string='Expense',
        required=True,
        domain="[('expense_type', '=', expense_type), ('state', 'in', ['validate', 'done'])]",
    )
    allowed_cost_center_ids = fields.Many2many(
        "account.analytic.account",
        compute="_compute_allowed_cost_center_ids",
        store=False,
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('rfq_sent', 'RFQ Sent'),
            ('pending', 'Pending'),
            ('purchase', 'Purchase Order'),
            ('cancel', 'Cancelled'),
        ],
        string="Status",
        default='draft',
        tracking=True,
    )
    budget_increase_request_count = fields.Integer(compute="_compute_budget_increase_request_count")
    show_request_budget_increase_button = fields.Boolean(
        compute="_compute_show_request_budget_increase_button"
    )
    linked_requisition_status = fields.Selection(
        [
            ('missing', 'Not Created'),
            ('pending', 'Pending Approval'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        string="PR Approval Status",
        compute="_compute_linked_document_statuses",
    )
    linked_rfq_status = fields.Selection(
        [
            ('missing', 'Not Created'),
            ('draft', 'Draft'),
            ('sent', 'RFQ Sent'),
            ('pending', 'Pending Approval'),
            ('purchase', 'Purchase Order'),
            ('done', 'Locked'),
            ('cancel', 'Cancelled'),
        ],
        string="RFQ Status",
        compute="_compute_linked_document_statuses",
    )
    linked_quotation_status = fields.Selection(
        [
            ('missing', 'Not Submitted'),
            ('quote', 'Quote'),
            ('po', 'Purchase'),
        ],
        string="Quotation Status",
        compute="_compute_linked_document_statuses",
    )
    linked_po_status = fields.Selection(
        [
            ('missing', 'Not Created'),
            ('draft', 'RFQ'),
            ('sent', 'RFQ Sent'),
            ('pending', 'Pending'),
            ('purchase', 'Purchase Order'),
            ('done', 'Locked'),
            ('cancel', 'Cancelled'),
        ],
        string="Purchase Order Status",
        compute="_compute_linked_document_statuses",
    )

    @api.depends("expense_bucket_id", "expense_bucket_id.crossovered_budget_line",
                 "expense_bucket_id.crossovered_budget_line.analytic_account_id")
    def _compute_allowed_cost_center_ids(self):
        for rec in self:
            rec.allowed_cost_center_ids = rec.expense_bucket_id.crossovered_budget_line.mapped("analytic_account_id")

    def _compute_linked_document_statuses(self):
        rfq_priority = {'draft': 1, 'sent': 2, 'done': 3, 'cancel': 4}
        po_priority = {'draft': 1, 'sent': 2, 'pending': 3, 'purchase': 4, 'done': 5, 'cancel': 6}

        for rec in self:
            requisition = self.env['purchase.requisition'].sudo().search([('name', '=', rec.name)], limit=1)
            rec.linked_requisition_status = requisition.approval if requisition else 'missing'

            rfqs = self.env['purchase.order'].sudo().search([('pr_name', '=', rec.name)])
            if rfqs:
                best_rfq = max(rfqs, key=lambda rfq: rfq_priority.get(rfq.state, 0))
                rec.linked_rfq_status = best_rfq.state
            else:
                rec.linked_rfq_status = 'missing'

            rfqs_for_quote_status = self.env['purchase.order'].sudo().search([('pr_name', '=', rec.name)])
            if rfqs_for_quote_status:
                best_rfq_for_quote = max(rfqs_for_quote_status, key=lambda rfq: po_priority.get(rfq.state, 0))
                rec.linked_quotation_status = 'po' if best_rfq_for_quote.state in ('pending', 'purchase', 'done') else 'quote'
            else:
                rec.linked_quotation_status = 'missing'

            purchase_orders = self.env['purchase.order'].sudo().search([('pr_name', '=', rec.name)])
            if purchase_orders:
                best_po = max(purchase_orders, key=lambda po: po_priority.get(po.state, 0))
                rec.linked_po_status = best_po.state
            else:
                rec.linked_po_status = 'missing'

    def _compute_budget_increase_request_count(self):
        Request = self.env['budget.increase.request'].sudo()
        for rec in self:
            rec.budget_increase_request_count = Request.search_count([('custom_pr_id', '=', rec.id)])

    @api.depends('line_ids.total_price', 'line_ids.cost_center_id', 'line_ids.cost_center_id.budget_left')
    def _compute_show_request_budget_increase_button(self):
        for rec in self:
            amount_by_cost_center = {}
            for line in rec.line_ids:
                if not line.cost_center_id:
                    continue
                cc = line.cost_center_id
                amount_by_cost_center.setdefault(cc.id, {"cc": cc, "amount": 0.0})
                amount_by_cost_center[cc.id]["amount"] += line.total_price

            rec.show_request_budget_increase_button = any(
                item['amount'] > item['cc'].budget_left for item in amount_by_cost_center.values()
            )

    def _required_date_from_priority(self, priority):
        today = fields.Date.context_today(self)
        offsets = {
            'low': 30,
            'medium': 10,
            'high': 3,
            'urgent': 0,
        }
        return today + relativedelta(days=offsets.get(priority, 0))

    @api.onchange('priority')
    def _onchange_priority_set_required_date(self):
        for rec in self:
            if rec.priority:
                rec.required_date = rec._required_date_from_priority(rec.priority)

    @api.onchange('expense_type')
    def _onchange_expense_type(self):
        for rec in self:
            if rec.expense_bucket_id and rec.expense_bucket_id.expense_type != rec.expense_type:
                rec.expense_bucket_id = False

    @api.depends('line_ids.total_price')
    def _compute_totals(self):
        for rec in self:
            subtotal = sum(line.total_price for line in rec.line_ids)
            rec.total_excl_vat = subtotal
            rec.vat_amount = subtotal * 0.15
            rec.total_incl_vat = subtotal + rec.vat_amount

    @api.model
    def create(self, vals):
        if not vals.get('line_ids'):
            raise ValidationError(_("Please add at least one line."))
        if vals.get('priority'):
            vals['required_date'] = self._required_date_from_priority(vals['priority'])
        if vals.get('pr_type') == 'cash':
            vals['name'] = self.env['ir.sequence'].next_by_code('custom.cash.pr') or '/'
        else:
            vals['name'] = self.env['ir.sequence'].next_by_code('custom.pr') or '/'
        return super(CustomPR, self).create(vals)

    @api.model
    def default_get(self, fields_list):
        res = super(CustomPR, self).default_get(fields_list)

        # Get current user
        user = self.env.user
        employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)

        supervisor_user = user.supervisor_user_id

        if employee:
            res.update({
                'requested_by': employee.name,
                'requested_user_id': user.id,
                'department': employee.department_id.name if employee.department_id else False,
                'supervisor': supervisor_user.name if supervisor_user else (
                    employee.parent_id.name if employee.parent_id else False),
                'supervisor_partner_id': (
                    supervisor_user.partner_id.id if supervisor_user and supervisor_user.partner_id
                    else (
                        employee.parent_id.user_id.partner_id.id if employee.parent_id and employee.parent_id.user_id else False)
                ),
            })
        else:
            res.update({
                'requested_by': user.name,
                'requested_user_id': user.id,
                'supervisor': supervisor_user.name if supervisor_user else False,
                'supervisor_partner_id': supervisor_user.partner_id.id if supervisor_user and supervisor_user.partner_id else False,
            })

        return res

    def action_create_pr(self):
        self.ensure_one()
        rec = self

        # Check required fields
        if not rec.line_ids:
            raise ValidationError("You must add at least one line before submitting the Purchase Requisition.")
        if rec.expense_bucket_id.state not in ("validate", "done"):
            raise ValidationError(
                _("Only validated budgets can be used. Please submit and approve the selected budget first.")
            )

        # Enforce WO per-product mini-budget caps at submit time as a hard gate
        # (in addition to line-level constrains) so users cannot bypass via UI flow.
        rec.line_ids._check_work_order_product_limits()

        wo_variance_requires_approval = False
        for line in rec.line_ids:
            caps = line._get_wo_product_caps()
            if not caps:
                continue
            if line.quantity > caps['allowed_qty'] or line.unit_price > caps['allowed_unit_price']:
                wo_variance_requires_approval = True
                break

        if rec.wo_variance_requires_approval != wo_variance_requires_approval:
            rec.wo_variance_requires_approval = wo_variance_requires_approval

        # Validate cost center budget per line (supports multiple cost centers in one PR)
        amount_by_cost_center = {}
        for line in rec.line_ids:
            cost_center = line.cost_center_id.sudo()
            if not cost_center:
                raise ValidationError(
                    f"Please select a cost center for line '{line.description.display_name}'."
                )
            amount_by_cost_center.setdefault(cost_center.id, {"cc": cost_center, "amount": 0.0})
            amount_by_cost_center[cost_center.id]["amount"] += line.total_price

        for item in amount_by_cost_center.values():
            cost_center = item["cc"]
            required_amount = item["amount"]
            if required_amount > cost_center.budget_left:
                raise ValidationError(
                    f"This cost center {cost_center.display_name}has low budget for this PR "
                    f"Required budget is SAR. ({required_amount}) Remaining budget is SAR. ({cost_center.budget_left})."
                )

        # Validation: prevent 0 amount PR
        if rec.total_excl_vat == 0.00:
            raise ValidationError("Add Unit Price First.")

        # Check if an old PR exists for this record name

        # SIDISSUE1
        existing_pr = self.env['purchase.requisition'].sudo().search([('name', '=', rec.name)], limit=1)
        if existing_pr:
            existing_pr.sudo().unlink()

        # Create new Purchase Requisition
        requester = rec.requested_user_id.sudo() if rec.requested_user_id else self.env.user.sudo()
        supervisor_user = requester.supervisor_user_id if requester else False
        supervisor_name = rec.supervisor or (supervisor_user.name if supervisor_user else False)
        supervisor_partner_id = rec.supervisor_partner_id or (
            supervisor_user.partner_id.id if supervisor_user and supervisor_user.partner_id else False)

        requisition = self.env['purchase.requisition'].sudo().create({
            'name': rec.name,
            'date_request': rec.date_request,
            'requested_by': rec.requested_by,
            'department': rec.department,
            'supervisor': supervisor_name,
            'supervisor_partner_id': supervisor_partner_id,
            'required_date': rec.required_date,
            'priority': rec.priority,
            'notes': rec.notes,
            'comments': rec.comments,
            'pr_type': 'cash' if rec.pr_type == 'cash' else 'pr',
            'wo_variance_requires_approval': wo_variance_requires_approval,
            'expense_bucket_id': rec.expense_bucket_id.id,
            'expense_scope': rec.expense_bucket_id.scope,
            'expense_type': rec.expense_type,
        })

        # Create Lines
        for line in rec.line_ids:
            self.env['purchase.requisition.line'].sudo().create({
                'requisition_id': requisition.id,
                'description': line.description.id,
                'type': line.type,
                'cost_center_id': line.cost_center_id.id,
                'quantity': line.quantity,
                'unit': line.unit.name,
                'unit_price': line.unit_price,
            })

        rec.pr_created = True

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': "Success",
                'message': f"PR {requisition.name} has been created (old one replaced if existed).",
                'sticky': False,
            }
        }


    def action_reset_to_draft(self):
        for rec in self:
            linked_pos = self.env["purchase.order"].sudo().search([("pr_name", "=", rec.name)])
            if linked_pos.filtered(lambda po: po.state in ("purchase", "done")):
                raise ValidationError(_("Cannot reset PR %s because it already has a confirmed Purchase Order.") % rec.name)

            linked_pos.sudo().unlink()
            linked_rfqs = self.env["purchase.order"].sudo().search([("pr_name", "=", rec.name)])
            linked_rfqs.unlink()
            linked_reqs = self.env["purchase.requisition"].sudo().search([("name", "=", rec.name)])
            linked_reqs.unlink()

            rec.write({
                "state": "draft",
                "approval": "pending",
                "rejection_reason": False,
                "pr_created": False,
            })

    def action_open_budget_requests(self):
        self.ensure_one()
        return {
            'name': 'Budget Increase Requests',
            'type': 'ir.actions.act_window',
            'res_model': 'budget.increase.request',
            'view_mode': 'tree,form',
            'domain': [('custom_pr_id', '=', self.id)],
            'context': {'default_custom_pr_id': self.id},
        }

    def action_request_budget_increase(self):
        self.ensure_one()
        amount_by_cost_center = {}
        for line in self.line_ids:
            if not line.cost_center_id:
                continue
            cc = line.cost_center_id
            amount_by_cost_center.setdefault(cc.id, {"cc": cc, "amount": 0.0})
            amount_by_cost_center[cc.id]["amount"] += line.total_price

        exceeded_cost_centers = [
            item for item in amount_by_cost_center.values()
            if item['amount'] > item['cc'].budget_left
        ]

        if not exceeded_cost_centers:
            raise ValidationError(
                _("All cost center lines are within budget. Budget increase request is not required."))

        request = self.env['budget.increase.request'].create({
            'custom_pr_id': self.id,
            'reason': f'Budget increase requested for PR {self.name}.',
            'line_ids': [
                (0, 0, {
                    'cost_center_id': item['cc'].id,
                    'requested_increase': max(item['amount'] - item['cc'].budget_left, 1.0),
                })
                for item in exceeded_cost_centers
            ]
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Budget Increase Request',
            'res_model': 'budget.increase.request',
            'res_id': request.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def write(self, vals):
        if vals.get('priority'):
            vals['required_date'] = self._required_date_from_priority(vals['priority'])
        return super(CustomPR, self).write(vals)

    @api.constrains('expense_type', 'expense_bucket_id')
    def _check_expense_type_bucket(self):
        for rec in self:
            if rec.expense_bucket_id and rec.expense_type and rec.expense_bucket_id.expense_type != rec.expense_type:
                raise ValidationError(_('Expense bucket must match selected expense type.'))
            if rec.expense_bucket_id and rec.expense_bucket_id.state not in ("validate", "done"):
                raise ValidationError(_('Selected budget must be validated before it can be used in PR.'))


class CustomPRLine(models.Model):
    _name = 'custom.pr.line'
    _description = 'Custom PR Line'

    _sql_constraints = [
        ('custom_pr_line_qty_non_negative', 'CHECK(quantity >= 0)', 'Quantity cannot be negative.'),
        ('custom_pr_line_price_non_negative', 'CHECK(unit_price >= 0)', 'Unit Price cannot be negative.'),
    ]

    pr_id = fields.Many2one('custom.pr', string="Purchase Requisition", ondelete="cascade")
    description = fields.Many2one(
        'product.product',
        string="Product",
        required=True,
        ondelete="restrict",
        context={'display_default_code': False},
    )
    cost_center_id = fields.Many2one(
        'account.analytic.account',
        string='Cost Center',
        required=True,
        domain="[('id', 'in', pr_id.allowed_cost_center_ids)]",
    )

    @api.onchange('pr_id.expense_bucket_id')
    def _onchange_expense_bucket(self):
        for rec in self:
            bucket = rec.pr_id.expense_bucket_id
            allowed = bucket.crossovered_budget_line.mapped("analytic_account_id")
            if rec.cost_center_id and bucket and rec.cost_center_id not in allowed:
                rec.cost_center_id = False

    @api.constrains('cost_center_id', 'pr_id')
    def _check_cost_center_matches_bucket(self):
        for rec in self:
            bucket = rec.pr_id.expense_bucket_id
            allowed = bucket.crossovered_budget_line.mapped("analytic_account_id")
            if rec.cost_center_id and bucket and rec.cost_center_id not in allowed:
                raise ValidationError(_('Selected cost center must belong to the selected expense bucket.'))

    type = fields.Selection(
        [
            ('material', 'Material'),
            ('service', 'Service')
        ],
        string="Type",
        compute="_compute_type_from_product",
        store=True,
        readonly=True,
        required=False,
    )
    quantity = fields.Float(string="Quantity", default=1.0)
    # unit = fields.Selection(
    #     [
    #         ('Kilogram', 'Kilogram'),
    #         ('Gram', 'Gram'),
    #         ('Litre', 'Litre'),
    #         ('Millilitre', 'Millilitre'),
    #         ('Meter', 'Metre'),
    #         ('Each', 'Each'),
    #     ],
    #     string="Unit",
    #     required=True,
    # )
    unit = fields.Many2one(
        'uom.uom',
        string="Unit of Measure"
    )

    unit_price = fields.Float(
        string="Unit Cost",
        digits="Product Price",
        default=0.0,
    )

    @api.onchange("description", "unit")
    def _onchange_product_set_price(self):
        for rec in self:
            if not rec.description:
                rec.unit_price = 0.0
                return

            rec.unit_price = rec.description.standard_price or 0.0

            if rec.unit and rec.description.uom_id and rec.unit != rec.description.uom_id:
                rec.unit_price = rec.description.uom_id._compute_price(
                    rec.unit_price, rec.unit
                )

    total_price = fields.Float(string="Total", compute="_compute_total", store=True)

    @api.depends('quantity', 'unit_price')
    def _compute_total(self):
        for line in self:
            line.total_price = line.quantity * line.unit_price

    @api.onchange('description')
    def _onchange_description(self):
        for rec in self:
            if rec.description:
                rec.unit = rec.description.uom_id

    @api.depends('description', 'description.detailed_type')
    def _compute_type_from_product(self):
        for rec in self:
            if rec.description and rec.description.detailed_type == 'service':
                rec.type = 'service'
            else:
                rec.type = 'material'

    @api.constrains('quantity', 'unit_price')
    def _check_non_negative_values(self):
        for rec in self:
            if rec.quantity < 0:
                raise ValidationError('Quantity cannot be negative.')
            if rec.unit_price < 0:
                raise ValidationError('Unit Price cannot be negative.')

    def _get_wo_product_caps(self):
        """Return allowed qty/price/amount for this cost center + product from approved WO BOQ."""
        self.ensure_one()

        if not self.cost_center_id or not self.description:
            return False

        if 'pr.work.order.cost.center' not in self.env:
            return False

        wo_cc = self.env['pr.work.order.cost.center'].sudo().search([
            ('analytic_account_id', '=', self.cost_center_id.id),
            ('work_order_id.state', 'in',
             ['ops_approval', 'acc_approval', 'final_approval', 'approved', 'in_progress', 'done']),
        ], limit=1)

        if not wo_cc:
            return False

        boq_lines = wo_cc.work_order_id.boq_line_ids.filtered(
            lambda l: l.display_type not in ('line_section', 'line_note')
                      and l.section_name == wo_cc.section_name
                      and l.product_id
                      and l.product_id.id == self.description.id
        )

        if not boq_lines:
            return {
                'found_work_order': True,
                'allowed_qty': 0.0,
                'allowed_unit_price': 0.0,
                'allowed_amount': 0.0,
                'work_order': wo_cc.work_order_id,
                'section_name': wo_cc.section_name,
            }

        allowed_qty = sum(boq_lines.mapped('qty'))
        allowed_amount = sum(boq_lines.mapped('total'))
        allowed_unit_price = max(boq_lines.mapped('unit_cost') or [0.0])

        return {
            'found_work_order': True,
            'allowed_qty': allowed_qty,
            'allowed_unit_price': allowed_unit_price,
            'allowed_amount': allowed_amount,
            'work_order': wo_cc.work_order_id,
            'section_name': wo_cc.section_name,
        }

    def _get_trading_sale_product_caps(self):
        """Return allowed qty/price/amount for this cost center + product from confirmed Trading SO."""
        self.ensure_one()

        bucket = self.pr_id.expense_bucket_id
        if not bucket or bucket.scope != "trading" or not bucket.sale_order_id:
            return False
        if not self.cost_center_id or not self.description:
            return False

        sale_order = bucket.sale_order_id.sudo()
        so_lines = sale_order.order_line.filtered(
            lambda l: not l.display_type and l.product_id and l.product_id.id == self.description.id
        )
        if not so_lines:
            return {
                "sale_order": sale_order,
                "allowed_qty": 0.0,
                "allowed_unit_price": 0.0,
                "allowed_amount": 0.0,
            }

        relevant_lines = self.env["sale.order.line"]
        for line in so_lines:
            distribution = line.analytic_distribution or {}
            line_cc_ids = {int(key) for key in distribution.keys() if str(key).isdigit()}
            if line_cc_ids:
                if self.cost_center_id.id in line_cc_ids:
                    relevant_lines |= line
            elif len(self.pr_id.allowed_cost_center_ids) == 1 and self.cost_center_id in self.pr_id.allowed_cost_center_ids:
                relevant_lines |= line

        if not relevant_lines:
            return {
                "sale_order": sale_order,
                "allowed_qty": 0.0,
                "allowed_unit_price": 0.0,
                "allowed_amount": 0.0,
            }

        return {
            "sale_order": sale_order,
            "allowed_qty": sum(relevant_lines.mapped("product_uom_qty")),
            "allowed_unit_price": max(relevant_lines.mapped("price_unit") or [0.0]),
            "allowed_amount": sum(relevant_lines.mapped("price_subtotal")),
        }

    @api.constrains('cost_center_id', 'description', 'quantity', 'unit_price', 'pr_id')
    def _check_work_order_product_limits(self):
        for rec in self:
            if not rec.cost_center_id or not rec.description:
                continue

            caps = rec._get_wo_product_caps()
            if not caps:
                continue

            if not caps['allowed_qty']:
                raise ValidationError(_(
                    "Product '%(product)s' is not budgeted in approved Work Order '%(wo)s' section '%(section)s' for cost center '%(cc)s'."
                ) % {
                                          'product': rec.description.display_name,
                                          'wo': caps['work_order'].display_name,
                                          'section': caps['section_name'] or '-',
                                          'cc': rec.cost_center_id.display_name,
                                      })

            sibling_lines = rec.pr_id.line_ids.filtered(
                lambda l: l.cost_center_id.id == rec.cost_center_id.id
                          and l.description.id == rec.description.id
            )
            current_pr_amount = sum(sibling_lines.mapped('total_price'))

            already_requested_lines = self.env['custom.pr.line'].sudo().search([
                ('id', 'not in', rec.pr_id.line_ids.ids),
                ('cost_center_id', '=', rec.cost_center_id.id),
                ('description', '=', rec.description.id),
                ('pr_id.approval', '!=', 'rejected'),
            ])
            already_requested_amount = sum(already_requested_lines.mapped('total_price'))

            total_requested_amount = current_pr_amount + already_requested_amount

            if total_requested_amount > caps['allowed_amount']:
                raise ValidationError(_(
                    "Requested amount for '%(product)s' exceeds Work Order amount for cost center '%(cc)s'. Allowed: %(allowed)s, Requested (including other PRs): %(requested)s."
                ) % {
                                          'product': rec.description.display_name,
                                          'cc': rec.cost_center_id.display_name,
                                          'allowed': caps['allowed_amount'],
                                          'requested': total_requested_amount,
                                      })

    @api.constrains("cost_center_id", "description", "quantity", "unit_price", "pr_id")
    def _check_trading_sale_order_product_limits(self):
        for rec in self:
            if not rec.cost_center_id or not rec.description or not rec.pr_id:
                continue

            caps = rec._get_trading_sale_product_caps()
            if not caps:
                continue

            if not caps["allowed_qty"]:
                raise ValidationError(_(
                    "Product '%(product)s' is not available in Sale Order '%(so)s' for cost center '%(cc)s'."
                ) % {
                    "product": rec.description.display_name,
                    "so": caps["sale_order"].display_name,
                    "cc": rec.cost_center_id.display_name,
                })

            sibling_lines = rec.pr_id.line_ids.filtered(
                lambda l: l.cost_center_id.id == rec.cost_center_id.id
                and l.description.id == rec.description.id
            )
            current_pr_qty = sum(sibling_lines.mapped("quantity"))
            current_pr_amount = sum(sibling_lines.mapped("total_price"))

            other_lines = self.env["custom.pr.line"].sudo().search([
                ("id", "not in", rec.pr_id.line_ids.ids),
                ("cost_center_id", "=", rec.cost_center_id.id),
                ("description", "=", rec.description.id),
                ("pr_id.expense_bucket_id", "=", rec.pr_id.expense_bucket_id.id),
                ("pr_id.approval", "!=", "rejected"),
            ])
            total_requested_qty = current_pr_qty + sum(other_lines.mapped("quantity"))
            total_requested_amount = current_pr_amount + sum(other_lines.mapped("total_price"))

            if total_requested_qty > caps["allowed_qty"]:
                raise ValidationError(_(
                    "Requested quantity for '%(product)s' exceeds Sale Order '%(so)s' quantity for cost center '%(cc)s'. Allowed: %(allowed)s, Requested (including other PRs): %(requested)s."
                ) % {
                    "product": rec.description.display_name,
                    "so": caps["sale_order"].display_name,
                    "cc": rec.cost_center_id.display_name,
                    "allowed": caps["allowed_qty"],
                    "requested": total_requested_qty,
                })

            if rec.unit_price > caps["allowed_unit_price"]:
                raise ValidationError(_(
                    "Unit cost for '%(product)s' cannot exceed Sale Order '%(so)s' unit price for cost center '%(cc)s'. Allowed max: %(allowed)s, Entered: %(entered)s."
                ) % {
                    "product": rec.description.display_name,
                    "so": caps["sale_order"].display_name,
                    "cc": rec.cost_center_id.display_name,
                    "allowed": caps["allowed_unit_price"],
                    "entered": rec.unit_price,
                })

            if total_requested_amount > caps["allowed_amount"]:
                raise ValidationError(_(
                    "Requested amount for '%(product)s' exceeds Sale Order '%(so)s' amount for cost center '%(cc)s'. Allowed: %(allowed)s, Requested (including other PRs): %(requested)s."
                ) % {
                    "product": rec.description.display_name,
                    "so": caps["sale_order"].display_name,
                    "cc": rec.cost_center_id.display_name,
                    "allowed": caps["allowed_amount"],
                    "requested": total_requested_amount,
                })


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    pr_name = fields.Char(string="PR Name", readonly=True)

    def _update_pr_state(self):
        """Helper to sync PR state with the highest PO state for the same pr_name"""
        for order in self:
            if order.pr_name:
                pr = self.env['custom.pr'].sudo().search([('name', '=', order.pr_name)], limit=1)
                if pr:
                    all_pos = self.env['purchase.order'].sudo().search([('pr_name', '=', order.pr_name)])
                    priority = {'draft': 1, 'sent': 2, 'pending': 3, 'purchase': 4, 'cancel': 5}
                    best_po = max(all_pos, key=lambda po: priority.get(po.state, 0))

                    # Update PR state
                    mapping = {
                        'draft': 'draft',
                        'sent': 'rfq_sent',
                        'pending': 'pending',
                        'purchase': 'purchase',
                        'cancel': 'cancel',
                    }
                    pr.state = mapping.get(best_po.state, pr.state)

    @api.model
    def create(self, vals):
        order = super().create(vals)
        # When PO is created, immediately set PR → pending
        if order.pr_name:
            pr = self.env['custom.pr'].sudo().search([('name', '=', order.pr_name)], limit=1)
            if pr:
                pr.state = 'pending'
        return order

    def write(self, vals):
        res = super().write(vals)
        if 'state' in vals:
            self._update_pr_state()
        return res

    def print_quotation(self):
        """Override Print RFQ to use custom PetroRaq Draft Invoice report"""
        return self.env.ref('pr_custom_purchase.petroraq_purchase_order_action_id').report_action(self)