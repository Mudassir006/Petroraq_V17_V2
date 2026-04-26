from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PRWorkOrder(models.Model):
    _name = "pr.work.order"
    _description = "Construction Work Order"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    def _notify_group_for_approval(self, group_xml_id, summary, body_html):
        self.ensure_one()
        group = self.env.ref(group_xml_id, raise_if_not_found=False)
        if not group:
            return
        activity_type = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        for user in group.users.filtered(lambda u: u.active):
            if activity_type:
                self.activity_schedule(
                    activity_type_id=activity_type.id,
                    user_id=user.id,
                    summary=summary,
                    note=body_html,
                )
            if user.email:
                self.env["mail.mail"].sudo().create({
                    "email_from": "hr@petroraq.com",
                    "email_to": user.email,
                    "subject": summary,
                    "body_html": body_html,
                }).send()

    def _reset_approval_metadata(self):
        self.write({
            "ops_approver_id": False,
            "ops_approved_date": False,
            "acc_approver_id": False,
            "acc_approved_date": False,
            "final_approver_id": False,
            "final_approved_date": False,
            "rejected_by": False,
            "rejected_date": False,
            "rejection_reason": False,
        })

    def action_reset_to_draft(self):
        for rec in self:
            if rec.state == "draft":
                continue

            rec._remove_linked_expense_bucket()

            rec.write({"state": "draft"})
            rec._reset_approval_metadata()
            rec.message_post(body=_("Work Order has been reset to draft."))

    def _remove_linked_expense_bucket(self):
        for rec in self:
            if not rec.expense_bucket_id:
                continue
            linked_pr_count = self.env["custom.pr"].sudo().search_count([
                ("expense_bucket_id", "=", rec.expense_bucket_id.id)
            ])
            if linked_pr_count:
                raise UserError(
                    _(
                        "Cannot delete expense bucket %s because it is already linked to Purchase Requisitions."
                    ) % rec.expense_bucket_id.display_name
                )
            rec.expense_bucket_id.sudo().unlink()
            rec.expense_bucket_id = False

    name = fields.Char(
        string="Work Order",
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _("New"),
        tracking=True,
    )
    # budget_id = fields.Many2one("crossovered.budget", string="Budget", readonly=True)

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )
    boq_line_ids = fields.One2many(
        "pr.work.order.boq",
        "work_order_id",
        string="BOQ / Budget Lines"
    )

    sale_order_id = fields.Many2one("sale.order", string="Sale Order", ondelete="restrict", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Customer", related="sale_order_id.partner_id", store=True)
    po_number = fields.Char(string="Customer PO", tracking=True)

    project_id = fields.Many2one("project.project", string="Construction Project", ondelete="restrict")
    analytic_account_id = fields.Many2one("account.analytic.account", string="Cost Center", ondelete="restrict")
    expense_bucket_id = fields.Many2one(
        "crossovered.budget",
        string="Expense Bucket",
        copy=False,
        readonly=True,
    )
    expense_bucket_count = fields.Integer(
        string="Expense Bucket Count",
        compute="_compute_expense_bucket_count",
    )
    cost_center_ids = fields.One2many(
        "pr.work.order.cost.center",
        "work_order_id",
        string="Cost Centers"
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("ops_approval", "Operations Approval"),
            ("acc_approval", "Accounts Approval"),
            ("final_approval", "Final Approval"),
            ("approved", "Approved"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        default="draft",
        tracking=True,
    )

    date_start = fields.Date(string="Planned Start Date", )
    date_end = fields.Date(string="Planned End Date")

    # Budget / amounts
    contract_amount = fields.Monetary(
        string="Contract Amount",
        currency_field="currency_id",
        help="Total selling value (from SO).",
        compute="_compute_budgeted_cost",
        store=True
    )
    budgeted_cost = fields.Monetary(string="Budgeted Cost", currency_field="currency_id",
                                    compute="_compute_budgeted_cost", store=True)

    @api.depends("boq_line_ids.total")
    def _compute_budgeted_cost(self):
        for order in self:
            order.budgeted_cost = sum(
                order.boq_line_ids.mapped("total")
            )
            order.contract_amount = order.sale_order_id.amount_total

    budgeted_margin = fields.Monetary(
        string="Budgeted Margin",
        currency_field="currency_id",
        compute="_compute_budgeted_margin",
        store=True,
    )

    overhead_percent = fields.Float(
        string="Overhead (%)",
        default=0.0,
        digits=(16, 2),
    )
    risk_percent = fields.Float(
        string="Risk (%)",
        default=0.0,
        digits=(16, 2),
    )
    profit_percent = fields.Float(
        string="Profit (%)",
        default=0.0,
        digits=(16, 2),
    )
    overhead_amount = fields.Monetary(
        string="Overhead Amount",
        currency_field="currency_id",
        compute="_compute_cost_buffers",
        store=True,
    )
    risk_amount = fields.Monetary(
        string="Risk Amount",
        currency_field="currency_id",
        compute="_compute_cost_buffers",
        store=True,
    )
    profit_amount = fields.Monetary(
        string="Profit Amount",
        currency_field="currency_id",
        compute="_compute_cost_buffers",
        store=True,
    )
    total_expected_cost = fields.Monetary(
        string="Total Expected Cost",
        currency_field="currency_id",
        compute="_compute_cost_buffers",
        store=True,
        help="Budgeted cost plus overhead and risk buffers.",
    )
    total_with_profit = fields.Monetary(
        string="Total With Profit",
        currency_field="currency_id",
        compute="_compute_cost_buffers",
        store=True,
    )

    actual_revenue = fields.Monetary(
        string="Actual Revenue",
        currency_field="currency_id",
        compute="_compute_actuals",
        store=True,
    )
    actual_cost = fields.Monetary(
        string="Actual Cost",
        currency_field="currency_id",
        compute="_compute_actuals",
        store=True,
    )
    actual_margin = fields.Monetary(
        string="Actual Margin",
        currency_field="currency_id",
        compute="_compute_actuals",
        store=True,
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
    )

    # Links to other resources
    task_ids = fields.One2many("project.task", "work_order_id", string="Tasks")
    stock_move_ids = fields.One2many("stock.move", "work_order_id", string="Material Movements")
    vendor_bill_ids = fields.One2many("account.move", "work_order_id", domain=[("move_type", "=", "in_invoice")])
    customer_invoice_ids = fields.One2many("account.move", "work_order_id", domain=[("move_type", "=", "out_invoice")])

    # Simple tracking of resources (you can split later)
    labour_ids = fields.One2many("account.analytic.line", "work_order_id", string="Timesheets / Labour")
    equipment_note = fields.Text(string="Equipment / Machinery Notes")
    materials_note = fields.Text(string="Materials Notes")

    # Approvals
    ops_approver_id = fields.Many2one("res.users", string="Operations Approver")
    ops_approved_date = fields.Datetime(string="Operations Approved On")

    acc_approver_id = fields.Many2one("res.users", string="Accounts Approver")
    acc_approved_date = fields.Datetime(string="Accounts Approved On")

    final_approver_id = fields.Many2one("res.users", string="Final Approver")
    final_approved_date = fields.Datetime(string="Final Approved On")

    note = fields.Text(string="Internal Notes")

    rejection_reason = fields.Text(string="Rejection Reason", tracking=True)
    rejected_by = fields.Many2one("res.users", string="Rejected By", tracking=True)
    rejected_date = fields.Datetime(string="Rejected On", tracking=True)

    drawings_attachment_ids = fields.Many2many(
        "ir.attachment",
        "pr_work_order_drawings_attachment_rel",
        "work_order_id",
        "attachment_id",
        string="Drawings Attachments",
        help="Drawings required for this work order.",
    )
    scope_attachment_ids = fields.Many2many(
        "ir.attachment",
        "pr_work_order_scope_attachment_rel",
        "work_order_id",
        "attachment_id",
        string="Scope of Work Attachments",
        help="Scope of work documents required for this work order.",
    )
    boq_attachment_ids = fields.Many2many(
        "ir.attachment",
        "pr_work_order_boq_attachment_rel",
        "work_order_id",
        "attachment_id",
        string="BOQ Attachments",
        help="BOQ documents required for this work order.",
    )

    @api.constrains("drawings_attachment_ids", "scope_attachment_ids", "boq_attachment_ids")
    def _check_required_attachments(self):
        for rec in self:
            if not rec.drawings_attachment_ids:
                raise ValidationError(_("Please upload at least one Drawing attachment."))
            if not rec.scope_attachment_ids:
                raise ValidationError(_("Please upload at least one Scope of Work attachment."))
            if not rec.boq_attachment_ids:
                raise ValidationError(_("Please upload at least one BOQ attachment."))

    @api.depends("expense_bucket_id")
    def _compute_expense_bucket_count(self):
        for rec in self:
            rec.expense_bucket_count = 1 if rec.expense_bucket_id else 0

    def action_view_expense_bucket(self):
        self.ensure_one()
        if not self.expense_bucket_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "name": _("Budget"),
            "res_model": "crossovered.budget",
            "view_mode": "form",
            "res_id": self.expense_bucket_id.id,
            "target": "current",
        }

    @api.depends("contract_amount", "budgeted_cost")
    def _compute_budgeted_margin(self):
        for rec in self:
            rec.budgeted_margin = (rec.contract_amount or 0.0) - (rec.budgeted_cost or 0.0)

    @api.depends("budgeted_cost", "overhead_percent", "risk_percent", "profit_percent")
    def _compute_cost_buffers(self):
        for rec in self:
            budget = rec.budgeted_cost or 0.0
            overhead = budget * (rec.overhead_percent or 0.0) / 100.0
            risk = budget * (rec.risk_percent or 0.0) / 100.0
            buffer_total = budget + overhead + risk
            profit = buffer_total * (rec.profit_percent or 0.0) / 100.0
            rec.overhead_amount = overhead
            rec.risk_amount = risk
            rec.total_expected_cost = buffer_total
            rec.profit_amount = profit
            rec.total_with_profit = buffer_total + profit

    @api.depends("analytic_account_id")
    def _compute_actuals(self):
        AnalyticLine = self.env["account.analytic.line"]
        for rec in self:
            rec.actual_revenue = rec.actual_cost = rec.actual_margin = 0.0
            if not rec.analytic_account_id:
                continue

            lines = AnalyticLine.read_group(
                [
                    ("account_id", "=", rec.analytic_account_id.id),
                    ("company_id", "=", rec.company_id.id),
                ],
                ["amount"],
                [],
            )
            # In analytic: revenue is positive, cost negative (usually)
            amount = lines and lines[0]["amount"] or 0.0
            # Split into cost & revenue
            # (If you want more accuracy, do two read_groups with domain on 'amount > 0' and '< 0')
            revenue = amount if amount > 0 else 0.0
            cost = -amount if amount < 0 else 0.0
            rec.actual_revenue = revenue
            rec.actual_cost = cost
            rec.actual_margin = revenue - cost

    # -------------------------------------------------
    # Business logic / workflow
    # -------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("pr.work.order") or _("New")
        return super().create(vals_list)

    def action_submit_ops(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Only draft work orders can be submitted for approval"))
            rec._ensure_project_expense_bucket(sync_budget=False)
            rec.state = "ops_approval"
            rec.rejection_reason = ""
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            record_url = f"{base_url}/web#id={rec.id}&model=pr.work.order&view_type=form"
            rec._notify_group_for_approval(
                "pr_work_order.custom_group_work_order_operations",
                _("Work Order %s waiting for operations approval") % rec.name,
                _("""<p>Dear Approver,</p><p>Work Order <b>%s</b> requires Operations approval.</p><p><a href=\"%s\">Open Work Order</a></p>""") % (
                rec.name, record_url),
            )
            # # ---------------------------------------
            # # AUTO CREATE BUDGET (ONLY IF NOT EXISTS)
            # # ---------------------------------------
            # if not rec.budget_id:
            #     Budget = rec.env["crossovered.budget"]
            #     BudgetLine = rec.env["crossovered.budget.lines"]
            #
            #     budget = Budget.create({
            #         "name": f"Budget for {rec.name}",
            #         "company_id": rec.company_id.id,
            #         "user_id": rec.env.user.id,
            #         "date_from": rec.date_start or fields.Date.today(),
            #         "date_to": rec.date_end or fields.Date.today(),
            #     })

            # for cc in rec.cost_center_ids:
            #     BudgetLine.create({
            #         "crossovered_budget_id": budget.id,
            #         "analytic_account_id": cc.analytic_account_id.id,
            #         "date_from": rec.date_start or fields.Date.today(),
            #         "date_to": rec.date_end or fields.Date.today(),
            #         "planned_amount": -abs(cc.estimated_cost),
            #     })
            #
            # rec.budget_id = budget.id

    def action_open_create_pr_wizard(self):
        self.ensure_one()

        if not self.env.user.has_group("pr_custom_purchase.group_custom_pr_end_user"):
            raise UserError(_("Only End Users can create PR from Work Order."))

        if self.state not in ["acc_approval", "final_approval", "approved", "in_progress", "done"]:
            raise UserError(_("PR can be created only after Operations approval."))

        if not self.boq_line_ids.filtered(
                lambda l: l.display_type not in ("line_section", "line_note") and l.product_id):
            raise UserError(_("No BOQ product lines found to create PR."))

        return {
            "type": "ir.actions.act_window",
            "name": _("Create PR"),
            "res_model": "pr.work.order.create.pr.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_work_order_id": self.id,
            },
        }

    def action_ops_approve(self):
        for rec in self:
            if rec.state != "ops_approval":
                continue

            rec.ops_approver_id = self.env.user
            rec.ops_approved_date = fields.Datetime.now()
            rec.state = "acc_approval"
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            record_url = f"{base_url}/web#id={rec.id}&model=pr.work.order&view_type=form"
            rec._notify_group_for_approval(
                "pr_work_order.custom_group_work_order_accounts",
                _("Work Order %s waiting for accounts approval") % rec.name,
                _("""<p>Dear Approver,</p><p>Work Order <b>%s</b> requires Accounts approval.</p><p><a href=\"%s\">Open Work Order</a></p>""") % (
                rec.name, record_url),
            )
            rec._ensure_project_expense_bucket(sync_budget=True)

    def _ensure_project_expense_bucket(self, sync_budget=False):
        Budget = self.env["crossovered.budget"].sudo()
        BudgetLine = self.env["crossovered.budget.lines"].sudo()
        today = fields.Date.context_today(self)

        for rec in self:
            cost_centers = rec.cost_center_ids.mapped("analytic_account_id").filtered(lambda a: a)
            if not cost_centers:
                continue

            total_budget = sum(cost_centers.mapped("budget_allowance"))

            if not rec.expense_bucket_id:
                bucket = Budget.create({
                    "name": _("%s - CAPEX Budget") % rec.name,
                    "scope": "project",
                    "expense_type": "capex",
                    "work_order_id": rec.id,
                    "source_budget_limit": total_budget,
                    "date_from": rec.date_start or today,
                    "date_to": rec.date_end or today,
                    "company_id": rec.company_id.id,
                    "user_id": self.env.user.id,
                })
                rec.sudo().write({"expense_bucket_id": bucket.id})
            else:
                bucket = rec.expense_bucket_id.sudo()
                if bucket.work_order_id != rec:
                    bucket.write({"work_order_id": rec.id})

            existing_cc_ids = set(bucket.crossovered_budget_line.mapped("analytic_account_id").ids)
            for analytic in cost_centers:
                if analytic.id in existing_cc_ids:
                    continue
                BudgetLine.create({
                    "crossovered_budget_id": bucket.id,
                    "analytic_account_id": analytic.id,
                    "date_from": bucket.date_from or today,
                    "date_to": bucket.date_to or today,
                    "planned_amount": analytic.budget_allowance or 0.0,
                })

            if sync_budget and not bucket.source_budget_limit:
                bucket.write({
                    "source_budget_limit": rec.budgeted_cost or total_budget,
                })

    def action_acc_approve(self):
        for rec in self:
            if rec.state != "acc_approval":
                continue
            budget = rec.expense_bucket_id.sudo()
            if budget and (budget.state not in ("validate", "done") or budget.approval_state != "approved"):
                raise UserError(
                    _(
                        "Budget %s must be fully approved before Accounts can approve this Work Order. "
                        "Current budget status: %s / %s."
                    ) % (budget.display_name, budget.state, budget.approval_state)
                )
            rec.acc_approver_id = self.env.user
            rec.acc_approved_date = fields.Datetime.now()
            rec.state = "final_approval"
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            record_url = f"{base_url}/web#id={rec.id}&model=pr.work.order&view_type=form"
            rec._notify_group_for_approval(
                "pr_work_order.custom_group_work_order_management",
                _("Work Order %s waiting for final approval") % rec.name,
                _("""<p>Dear Approver,</p><p>Work Order <b>%s</b> requires Management final approval.</p><p><a href=\"%s\">Open Work Order</a></p>""") % (
                rec.name, record_url),
            )

    def action_final_approve(self):
        for rec in self:
            if rec.state != "final_approval":
                continue
            rec.final_approver_id = self.env.user
            rec.final_approved_date = fields.Datetime.now()
            rec.state = "approved"

    def action_reject(self):
        self.ensure_one()

        if self.state in ("done", "cancel"):
            raise UserError(_("You cannot reject a completed or cancelled Work Order."))

        return {
            "name": _("Reject Work Order"),
            "type": "ir.actions.act_window",
            "res_model": "pr.work.order.reject.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_work_order_id": self.id,
            },
        }

    def action_start_operations(self):
        for rec in self:
            if rec.state not in ("approved", "in_progress"):
                raise UserError(_("Work Order must be approved before starting operations."))
            rec.state = "in_progress"

    def action_mark_done(self):
        for rec in self:
            rec.state = "done"

    def action_cancel(self):
        for rec in self:
            rec._remove_linked_expense_bucket()
            rec.state = "cancel"


class WorkOrderBOQ(models.Model):
    _name = "pr.work.order.boq"
    _description = "Work Order BOQ / Budget Lines"
    _order = "sequence, id"

    work_order_id = fields.Many2one("pr.work.order", ondelete="cascade")
    sequence = fields.Integer(default=10)
    section_name = fields.Char("Section")

    display_type = fields.Selection([
        ('line_section', 'Section'),
        ('line_note', 'Note'),
        ('product', 'Product'),
    ], default='product')

    name = fields.Char("Description", required=True)

    product_id = fields.Many2one("product.product", string="Product", tracking=True)
    uom_id = fields.Many2one("uom.uom", string="Unit")
    qty = fields.Float("Qty")

    unit_cost = fields.Float("Unit Cost")

    total = fields.Float("Total", compute="_compute_total", store=True)

    can_edit_boq = fields.Boolean(
        compute="_compute_can_edit_boq",
        store=False
    )

    @api.depends()
    def _compute_can_edit_boq(self):
        user = self.env.user
        can_edit = (
                user.has_group("pr_work_order.custom_group_work_order_user")
                or user.has_group("pr_work_order.custom_group_work_order_management")
        )
        for line in self:
            line.can_edit_boq = can_edit

    @api.depends("qty", "unit_cost")
    def _compute_total(self):
        for rec in self:
            rec.total = (rec.qty or 0.0) * (rec.unit_cost or 0.0)


class WorkOrderCostCenter(models.Model):
    _name = "pr.work.order.cost.center"
    _description = "Work Order Dynamic Cost Centers"
    _order = "sequence"
    _rec_name = "section_name"

    work_order_id = fields.Many2one("pr.work.order", ondelete="cascade")

    section_name = fields.Char("Section")
    analytic_account_id = fields.Many2one("account.analytic.account", string="Cost Center")
    sequence = fields.Integer(default=10)

    partner_id = fields.Many2one("res.partner", string="Partner")

    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id
    )

    estimated_cost = fields.Monetary(
        string="Total Cost",
        currency_field="currency_id",
        compute="_compute_estimated_cost",
        store=True,
    )
    department_id = fields.Many2one('account.analytic.account', string="Department",
                                    domain="[('analytic_plan_type', '=', 'department')]")
    section_id = fields.Many2one('account.analytic.account', string="Section",
                                 domain="[('analytic_plan_type', '=', 'section')]")
    spent_amount = fields.Monetary(
        string="Spent",
        currency_field="currency_id",
        compute="_compute_spent_amount",
        store=False,
    )

    remaining_amount = fields.Monetary(
        string="Remaining",
        currency_field="currency_id",
        compute="_compute_remaining_amount",
        store=False,
    )

    def _compute_spent_amount(self):
        AnalyticLine = self.env["account.analytic.line"]
        for rec in self:
            if not rec.analytic_account_id:
                rec.spent_amount = 0.0
                continue

            lines = AnalyticLine.search([
                ("account_id", "=", rec.analytic_account_id.id),
                ("move_line_id.move_id.state", "=", "posted"),
            ])

            rec.spent_amount = abs(sum(lines.mapped("amount")))

    def _compute_remaining_amount(self):
        for rec in self:
            rec.remaining_amount = (rec.estimated_cost or 0.0) - (rec.spent_amount or 0.0)

    @api.depends(
        "work_order_id.boq_line_ids.qty",
        "work_order_id.boq_line_ids.unit_cost",
        "work_order_id.boq_line_ids.total",
        "work_order_id.boq_line_ids.section_name",
        "section_name",
        "analytic_account_id",
    )
    def _compute_estimated_cost(self):
        for rec in self:
            lines = rec.work_order_id.boq_line_ids.filtered(
                lambda l: l.display_type not in ("line_section", "line_note")
                          and l.section_name == rec.section_name
            )
            rec.estimated_cost = sum(lines.mapped("total"))

            analytic = rec.analytic_account_id
            if not analytic:
                continue

            analytic_vals = {}
            if "budget_type" in analytic._fields:
                analytic_vals["budget_type"] = "capex"
            if "budget_allowance" in analytic._fields:
                analytic_vals["budget_allowance"] = rec.estimated_cost

            if analytic_vals:
                analytic.sudo().write(analytic_vals)

    @api.onchange("department_id", "section_id")
    def _sync_fields_to_analytic_account(self):
        for rec in self:
            analytic = rec.analytic_account_id
            if analytic:
                analytic.write({
                    "department_id": rec.department_id.id,
                    "section_id": rec.section_id.id,
                })


class PRWorkOrderRejectWizard(models.TransientModel):
    _name = "pr.work.order.reject.wizard"
    _description = "Reject Work Order"

    work_order_id = fields.Many2one(
        "pr.work.order",
        string="Work Order",
        required=True,
        readonly=True,
    )

    reason = fields.Text(string="Rejection Reason", required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        wo = self.work_order_id

        if wo.state in ("done", "cancel"):
            raise UserError(_("You cannot reject a completed or cancelled Work Order."))

        wo.write({
            "state": "draft",
            "rejection_reason": self.reason,
            "rejected_by": self.env.user.id,
            "rejected_date": fields.Datetime.now(),
        })

        wo._reset_approval_metadata()
        wo.write({
            "rejection_reason": self.reason,
            "rejected_by": self.env.user.id,
            "rejected_date": fields.Datetime.now(),
        })

        wo.message_post(
            body=_(
                "<b>Work Order Rejected</b><br/>"
                "<b>Reason:</b> %s"
            ) % self.reason
        )

        return {"type": "ir.actions.act_window_close"}
