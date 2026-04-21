from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ExpenseBucket(models.Model):
    _name = "pr.expense.bucket"
    _description = "PR Expense "
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True, tracking=True)
    scope = fields.Selection(
        [("department", "Department"), ("project", "Project")],
        string="Applies To",
        required=True,
        default="department",
        tracking=True,
    )
    expense_type = fields.Selection(
        [("opex", "Opex"), ("capex", "Capex")],
        string="Expense Type",
        required=True,
        tracking=True,
    )
    department_id = fields.Many2one("hr.department", string="Department", tracking=True)
    budget_amount = fields.Float(string=" Budget", required=True, tracking=True)

    state = fields.Selection([
        ("draft", "Draft"),
        ("pm_approval", "Pending Department/Project Manager"),
        ("accounts_approval", "Pending Accounts"),
        ("md_approval", "Pending Managing Director"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ], default="draft", tracking=True)
    rejection_reason = fields.Text(readonly=True, tracking=True)

    line_ids = fields.One2many("pr.expense.bucket.line", "bucket_id", string="Cost Centers")
    cost_center_ids = fields.Many2many(
        "account.analytic.account",
        compute="_compute_cost_center_ids",
        string="Cost Centers",
        store=False,
    )

    cost_center_budget_total = fields.Float(
        string="Cost Center Budget Total",
        compute="_compute_cost_center_budget_total",
    )
    budget_left = fields.Float(
        string="Budget Left",
        compute="_compute_budget_left",
    )
    native_budget_id = fields.Many2one(
        "crossovered.budget",
        string="Analytic Budget",
        copy=False,
        readonly=True,
    )

    can_pm_approve = fields.Boolean(compute="_compute_role_flags")
    can_accounts_approve = fields.Boolean(compute="_compute_role_flags")
    can_md_approve = fields.Boolean(compute="_compute_role_flags")
    can_reject = fields.Boolean(compute="_compute_role_flags")

    @api.depends("line_ids", "line_ids.cost_center_id")
    def _compute_cost_center_ids(self):
        for rec in self:
            rec.cost_center_ids = rec.line_ids.mapped("cost_center_id")

    @api.depends("line_ids", "line_ids.budget_allowance")
    def _compute_cost_center_budget_total(self):
        for rec in self:
            rec.cost_center_budget_total = sum(rec.line_ids.mapped("budget_allowance"))

    @api.depends("budget_amount", "cost_center_budget_total")
    def _compute_budget_left(self):
        for rec in self:
            rec.budget_left = (rec.budget_amount or 0.0) - (rec.cost_center_budget_total or 0.0)

    @api.depends_context("uid")
    def _compute_role_flags(self):
        user = self.env.user
        is_project_manager = user.has_group("pr_custom_purchase.project_manager")
        is_accounts = user.has_group("account.group_account_manager") or user.has_group("account.group_account_user")
        is_md = user.has_group("pr_custom_purchase.managing_director")
        for rec in self:
            is_department_manager = bool(
                rec.scope == "department"
                and rec.department_id.manager_id.user_id
                and rec.department_id.manager_id.user_id == user
            )
            rec.can_pm_approve = is_department_manager or (rec.scope == "project" and is_project_manager)
            rec.can_accounts_approve = is_accounts
            rec.can_md_approve = is_md
            rec.can_reject = (
                    (rec.state == "draft")
                    or (rec.state == "pm_approval" and rec.can_pm_approve)
                    or (rec.state == "accounts_approval" and is_accounts)
                    or (rec.state == "md_approval" and is_md)
            )

    def _get_department_manager_users(self):
        self.ensure_one()
        manager_user = self.department_id.manager_id.user_id
        return manager_user if manager_user and manager_user.active else self.env["res.users"]

    def _notify_group(self, group_xml_ids, summary, note):
        activity_type = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        users = self.env["res.users"]
        for xmlid in group_xml_ids:
            group = self.env.ref(xmlid, raise_if_not_found=False)
            if group:
                users |= group.users
        users = users.filtered(lambda u: u.active)

        for rec in self:
            for user in users:
                if activity_type:
                    rec.activity_schedule(
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

    def _notify_users(self, users, summary, note):
        activity_type = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        users = users.filtered(lambda u: u.active)
        for rec in self:
            for user in users:
                if activity_type:
                    rec.activity_schedule(
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

    def action_reset_to_draft(self):
        for rec in self:
            rec.write({
                "state": "draft",
                "rejection_reason": False,
            })
            rec.message_post(body=_("Expense  has been reset to draft."))

    @api.onchange("scope")
    def _onchange_scope(self):
        for rec in self:
            if rec.scope != "department":
                rec.department_id = False

    @api.constrains("scope", "department_id")
    def _check_scope_target(self):
        for rec in self:
            if rec.scope == "department" and not rec.department_id:
                raise ValidationError(_("Department is required when scope is Department."))

    @api.constrains("line_ids", "budget_amount")
    def _check_allocated_budget(self):
        for rec in self:
            total = sum(rec.line_ids.mapped("budget_allowance"))
            if total > rec.budget_amount:
                raise ValidationError(_(
                    "Total cost center budget (%s) cannot exceed bucket budget (%s)."
                ) % (total, rec.budget_amount))

    def write(self, vals):
        protected_fields = {"name", "scope", "expense_type", "department_id", "budget_amount",
                            "line_ids"}
        if any(field in vals for field in protected_fields):
            for rec in self:
                if rec.state != "draft":
                    raise UserError(_("Submitted expense bucket cannot be edited."))
        res = super().write(vals)
        if any(field in vals for field in {"name", "budget_amount", "line_ids"}):
            self._sync_native_budget()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_native_budget()
        return records

    def _sync_native_budget(self):
        Budget = self.env["crossovered.budget"].sudo()
        BudgetLine = self.env["crossovered.budget.lines"].sudo()
        today = fields.Date.context_today(self)
        for rec in self:
            if not rec.native_budget_id:
                rec.native_budget_id = Budget.create({
                    "name": _("Budget - %s") % (rec.name or rec.display_name),
                    "company_id": self.env.company.id,
                    "date_from": today,
                    "date_to": today,
                    "user_id": self.env.user.id,
                }).id
            budget = rec.native_budget_id.sudo()

            existing = {line.analytic_account_id.id: line for line in budget.crossovered_budget_line}
            wanted = {}
            for bucket_line in rec.line_ids.filtered("cost_center_id"):
                amount = bucket_line.budget_allowance or 0.0
                analytic = bucket_line.cost_center_id
                wanted[analytic.id] = wanted.get(analytic.id, 0.0) + amount

            for analytic_id, planned in wanted.items():
                if analytic_id in existing:
                    existing[analytic_id].write({"planned_amount": planned})
                else:
                    BudgetLine.create({
                        "crossovered_budget_id": budget.id,
                        "analytic_account_id": analytic_id,
                        "date_from": budget.date_from or today,
                        "date_to": budget.date_to or today,
                        "planned_amount": planned,
                    })

            for analytic_id, line in existing.items():
                if analytic_id not in wanted:
                    line.unlink()

    def action_submit(self):
        for rec in self:
            if rec.state != "draft":
                continue
            if not rec.line_ids:
                raise UserError(_("Add at least one cost center line."))

            if rec.scope == "department" and not rec._get_department_manager_users():
                raise UserError(
                    _("Please set a Department Manager user for the selected department before submitting."))

            rec.state = "pm_approval"
            if rec.scope == "department":
                rec._notify_users(
                    rec._get_department_manager_users(),
                    _("Expense  Approval Needed"),
                    _("Expense  <b>%s</b> is waiting for Department Manager approval.") % rec.display_name,
                )
            else:
                rec._notify_group(
                    ["pr_custom_purchase.project_manager"],
                    _("Expense  Approval Needed"),
                    _("Expense  <b>%s</b> is waiting for Project Manager approval.") % rec.display_name,
                )

    def action_pm_approve(self):
        for rec in self:
            if rec.state != "pm_approval":
                continue
            if not rec.can_pm_approve:
                if rec.scope == "department":
                    raise UserError(_("Only Department Manager can approve at this stage."))
                raise UserError(_("Only Project Manager can approve at this stage."))
            rec.state = "accounts_approval"
            rec._notify_group(["account.group_account_manager", "account.group_account_user"],
                              _("Expense  Approval Needed"),
                              _("Expense  <b>%s</b> is waiting for Accounts approval.") % rec.display_name)

    def action_accounts_approve(self):
        for rec in self:
            if rec.state != "accounts_approval":
                continue
            if not rec.can_accounts_approve:
                raise UserError(_("Only Accounts can approve at this stage."))
            rec.state = "md_approval"
            rec._notify_group(["pr_custom_purchase.managing_director"], _("Expense  Approval Needed"),
                              _("Expense  <b>%s</b> is waiting for Managing Director approval.") % rec.display_name)

    def action_md_approve(self):
        for rec in self:
            if rec.state != "md_approval":
                continue
            if not rec.can_md_approve:
                raise UserError(_("Only Managing Director can approve at this stage."))
            for line in rec.line_ids:
                line.cost_center_id.budget_allowance = (line.cost_center_id.budget_allowance or 0.0) + (
                        line.budget_allowance or 0.0)
                if line.budget_type:
                    line.cost_center_id.budget_type = line.budget_type
            rec.state = "approved"

    def action_reject(self):
        self.ensure_one()
        if not self.can_reject:
            raise UserError(_("You cannot reject this request at the current stage."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Reject Expense "),
            "res_model": "pr.expense.bucket.reject.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_bucket_id": self.id},
        }

    def unlink(self):
        budgets = self.mapped("native_budget_id").sudo()
        res = super().unlink()
        for budget in budgets:
            if budget.exists():
                budget.unlink()
        return res


class ExpenseBucketLine(models.Model):
    _name = "pr.expense.bucket.line"
    _description = "PR Expense  Line"

    bucket_id = fields.Many2one("pr.expense.bucket", required=True, ondelete="cascade")
    cost_center_id = fields.Many2one("account.analytic.account", string="Cost Center", required=True)
    budget_code = fields.Char(related="cost_center_id.budget_code", readonly=True)
    budget_type = fields.Selection([("opex", "Opex"), ("capex", "Capex")], string="Budget Type", )
    budget_allowance = fields.Float(string="Budget Allowance", )
    budget_left = fields.Float(related="cost_center_id.budget_left", readonly=True)

    _sql_constraints = [
        ("expense_bucket_line_unique", "unique(bucket_id, cost_center_id)",
         "Cost center already selected in this bucket."),
    ]

    @api.constrains("cost_center_id", "bucket_id")
    def _check_cost_center_bucket_limits(self):
        for rec in self:
            if rec.cost_center_id.expense_bucket_id and rec.cost_center_id.expense_bucket_id != rec.bucket_id:
                raise ValidationError(_("This cost center already belongs to another expense bucket."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            bucket = self.env["pr.expense.bucket"].browse(vals.get("bucket_id"))
            if bucket and bucket.state != "draft":
                raise UserError(_("Submitted expense bucket cannot be edited."))
        records = super().create(vals_list)
        for rec in records:
            rec.cost_center_id.expense_bucket_id = rec.bucket_id.id
            rec.bucket_id._sync_native_budget()
        return records

    def write(self, vals):
        if any(field in vals for field in ["bucket_id", "cost_center_id", "budget_type", "budget_allowance"]):
            for rec in self:
                if rec.bucket_id.state != "draft":
                    raise UserError(_("Submitted expense bucket cannot be edited."))
        buckets = self.mapped("bucket_id")
        previous = {rec.id: rec.cost_center_id.id for rec in self}
        res = super().write(vals)
        for rec in self:
            if rec.cost_center_id:
                rec.cost_center_id.expense_bucket_id = rec.bucket_id.id
            previous_id = previous.get(rec.id)
            if previous_id and previous_id != rec.cost_center_id.id:
                old_cc = self.env["account.analytic.account"].browse(previous_id)
                if old_cc.exists() and old_cc.expense_bucket_id == rec.bucket_id:
                    old_cc.expense_bucket_id = False
        (buckets | self.mapped("bucket_id"))._sync_native_budget()
        return res

    def unlink(self):
        buckets = self.mapped("bucket_id")
        for rec in self:
            if rec.bucket_id.state != "draft":
                raise UserError(_("Submitted expense bucket cannot be edited."))
            if rec.cost_center_id and rec.cost_center_id.expense_bucket_id == rec.bucket_id:
                rec.cost_center_id.expense_bucket_id = False
        res = super().unlink()
        buckets._sync_native_budget()
        return res

    @api.onchange("cost_center_id")
    def _onchange_cost_center_id(self):
        for rec in self:
            if rec.cost_center_id and not rec.budget_type:
                rec.budget_type = rec.cost_center_id.budget_type


class ExpenseBucketRejectWizard(models.TransientModel):
    _name = "pr.expense.bucket.reject.wizard"
    _description = "Expense  Reject Wizard"

    bucket_id = fields.Many2one("pr.expense.bucket", required=True)
    rejection_reason = fields.Text(required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        self.bucket_id.write({
            "state": "rejected",
            "rejection_reason": self.rejection_reason,
        })
        return {"type": "ir.actions.act_window_close"}
