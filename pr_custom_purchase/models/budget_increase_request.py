from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class BudgetIncreaseRequest(models.Model):
    _name = "budget.increase.request"
    _description = "Budget Increase Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(string="Request Number", default="New", readonly=True, copy=False)
    request_date = fields.Date(string="Request Date", default=fields.Date.context_today, required=True)
    requested_by_id = fields.Many2one("res.users", string="Requested By", default=lambda self: self.env.user, readonly=True)
    custom_pr_id = fields.Many2one("custom.pr", string="Custom PR")
    requisition_id = fields.Many2one("purchase.requisition", string="Purchase Requisition")
    custom_pr_line_ids = fields.One2many(
        related="custom_pr_id.line_ids",
        string="PR Products",
        readonly=True,
    )
    reason = fields.Text(string="Reason", required=True)
    state = fields.Selection([
        ("draft", "Draft"),
        ("pm_approval", "Pending Project Manager"),
        ("accounts_approval", "Pending Accounts"),
        ("md_approval", "Pending Managing Director"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ], default="draft", tracking=True)
    rejection_reason = fields.Text(string="Rejection Reason", readonly=True, tracking=True)
    line_ids = fields.One2many("budget.increase.request.line", "request_id", string="Cost Center Lines", required=True)

    can_pm_approve = fields.Boolean(compute="_compute_role_flags")
    can_accounts_approve = fields.Boolean(compute="_compute_role_flags")
    can_md_approve = fields.Boolean(compute="_compute_role_flags")
    can_reject = fields.Boolean(compute="_compute_role_flags")

    @api.depends_context("uid")
    def _compute_role_flags(self):
        user = self.env.user
        is_pm = user.has_group("pr_custom_purchase.project_manager")
        is_accounts = user.has_group("account.group_account_manager") or user.has_group("account.group_account_user")
        is_md = user.has_group("pr_custom_purchase.managing_director")
        for rec in self:
            rec.can_pm_approve = is_pm
            rec.can_accounts_approve = is_accounts
            rec.can_md_approve = is_md
            rec.can_reject = (
                (rec.state == "draft" and rec.requested_by_id == user)
                or (rec.state == "pm_approval" and is_pm)
                or (rec.state == "accounts_approval" and is_accounts)
                or (rec.state == "md_approval" and is_md)
            )

    @api.model
    def create(self, vals):
        if vals.get("name", "New") == "New":
            vals["name"] = self.env["ir.sequence"].next_by_code("budget.increase.request") or "New"
        return super().create(vals)

    @api.constrains("line_ids")
    def _check_lines(self):
        for rec in self:
            if not rec.line_ids:
                raise ValidationError(_("Add at least one cost center line."))

    def _schedule_group_activity(self, xmlids, summary, note):
        users = self.env["res.users"]
        for xmlid in xmlids:
            group = self.env.ref(xmlid, raise_if_not_found=False)
            if group:
                users |= group.users
        users = users.filtered(lambda u: u.active)
        activity_type = self.env.ref("mail.mail_activity_data_todo")
        for req in self:
            for user in users:
                req.activity_schedule(
                    activity_type_id=activity_type.id,
                    user_id=user.id,
                    summary=summary,
                    note=note,
                )
            emails = ",".join(users.filtered(lambda u: u.email).mapped("email"))
            if emails:
                self.env["mail.mail"].sudo().create({
                    "email_from": "hr@petroraq.com",
                    "email_to": emails,
                    "subject": summary,
                    "body_html": f"<p>{note}</p>",
                }).send()

    def action_submit(self):
        for rec in self:
            if rec.state != "draft":
                continue
            if not rec.line_ids:
                raise UserError(_("Add at least one cost center line."))
            rec.state = "pm_approval"
        self._schedule_group_activity(
            ["pr_custom_purchase.project_manager"],
            _("Budget Increase Approval Needed"),
            _("Please review budget increase request <b>%s</b>.") % self.name,
        )

    def action_pm_approve(self):
        for rec in self:
            if rec.state != "pm_approval":
                continue
            if not rec.can_pm_approve:
                raise UserError(_("Only Project Manager can approve at this stage."))
            rec.state = "accounts_approval"
        self._schedule_group_activity(
            ["account.group_account_manager", "account.group_account_user"],
            _("Budget Increase Approval Needed"),
            _("Please review budget increase request <b>%s</b>.") % self.name,
        )

    def action_accounts_approve(self):
        for rec in self:
            if rec.state != "accounts_approval":
                continue
            if not rec.can_accounts_approve:
                raise UserError(_("Only Accounts can approve at this stage."))
            rec.state = "md_approval"
        self._schedule_group_activity(
            ["pr_custom_purchase.managing_director"],
            _("Budget Increase Approval Needed"),
            _("Please review budget increase request <b>%s</b>.") % self.name,
        )

    def action_md_approve(self):
        BudgetLine = self.env["crossovered.budget.lines"].sudo()
        for rec in self:
            if rec.state != "md_approval":
                continue
            if not rec.can_md_approve:
                raise UserError(_("Only Managing Director can approve at this stage."))
            for line in rec.line_ids:
                line.cost_center_id.sudo().budget_allowance += line.requested_increase
                budget_lines = BudgetLine.search([
                    ("analytic_account_id", "=", line.cost_center_id.id),
                ])
                for budget_line in budget_lines:
                    budget_line.planned_amount = (budget_line.planned_amount or 0.0) + line.requested_increase
            rec.state = "approved"

    def action_reset_to_draft(self):
        for rec in self:
            rec.write({"state": "draft", "rejection_reason": False})
            rec.message_post(body=_("Budget increase request has been reset to draft."))

    def action_reject(self):
        self.ensure_one()
        if not self.can_reject:
            raise UserError(_("You cannot reject this request at the current stage."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Reject Budget Increase"),
            "res_model": "budget.increase.reject.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }


class BudgetIncreaseRejectWizard(models.TransientModel):
    _name = "budget.increase.reject.wizard"
    _description = "Budget Increase Rejection Wizard"

    request_id = fields.Many2one("budget.increase.request", string="Request", required=True)
    rejection_reason = fields.Text(string="Rejection Reason", required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        self.request_id.write({"state": "rejected", "rejection_reason": self.rejection_reason})
        return {"type": "ir.actions.act_window_close"}


class BudgetIncreaseRequestLine(models.Model):
    _name = "budget.increase.request.line"
    _description = "Budget Increase Request Line"

    request_id = fields.Many2one("budget.increase.request", required=True, ondelete="cascade")
    cost_center_id = fields.Many2one("account.analytic.account", string="Cost Center", required=True)
    current_budget = fields.Float(string="Current Budget", related="cost_center_id.budget_allowance", readonly=True)
    budget_left = fields.Float(string="Budget Left", related="cost_center_id.budget_left", readonly=True)
    requested_increase = fields.Float(string="Requested Amount", required=True)
    remarks = fields.Char(string="Remarks")

    _sql_constraints = [
        ("requested_increase_positive", "CHECK(requested_increase > 0)", "Requested increase must be greater than zero."),
    ]
