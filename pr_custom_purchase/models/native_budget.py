from odoo import _, api, fields, models
from odoo.exceptions import UserError


class CrossoveredBudget(models.Model):
    _inherit = "crossovered.budget"
    _rec_name = "budget_sequence"

    budget_sequence = fields.Char(string="Budget Code", readonly=True, default='New')
    expense_type = fields.Selection(
        [("opex", "Opex"), ("capex", "Capex")],
        string="Expense Type",
        required=True,
    )
    scope = fields.Selection(
        [("department", "Department"), ("project", "Project"), ("trading", "Trading")],
        string="Applies To",
    )
    department_id = fields.Many2one("hr.department", string="Department")
    department_manager_user_id = fields.Many2one(
        "res.users",
        string="Department Manager",
        related="department_id.manager_id.user_id",
        readonly=True,
    )
    source_budget_limit = fields.Float(string="Source Budget Limit")
    po_reference = fields.Char(string="PO Reference")
    approval_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("pm_approval", "Pending Department/Project Manager"),
            ("accounts_approval", "Pending Accounts"),
            ("md_approval", "Pending Managing Director"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Approval Stage",
        default="draft",
        tracking=True,
    )
    can_pm_approve = fields.Boolean(compute="_compute_role_flags")
    can_accounts_approve = fields.Boolean(compute="_compute_role_flags")
    can_md_approve = fields.Boolean(compute="_compute_role_flags")

    def name_get(self):
        result = []
        for rec in self:
            if rec.budget_sequence and rec.name:
                display_name = f"{rec.budget_sequence} - {rec.name}"
            else:
                display_name = rec.budget_sequence or rec.name or _("New Budget")
            result.append((rec.id, display_name))
        return result

    @api.depends_context("uid")
    def _compute_role_flags(self):
        user = self.env.user
        is_pm = user.has_group("pr_custom_purchase.project_manager")
        is_accounts = user.has_group("account.group_account_manager") or user.has_group("account.group_account_user")
        is_md = user.has_group("pr_custom_purchase.managing_director")
        for rec in self:
            is_department_manager = bool(
                rec.department_id
                and rec.department_manager_user_id
                and rec.department_manager_user_id == user
            )
            rec.can_pm_approve = is_department_manager or is_pm
            rec.can_accounts_approve = is_accounts
            rec.can_md_approve = is_md

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("budget_sequence") or vals.get("budget_sequence") in ("/", _("New"), "New"):
                vals["budget_sequence"] = self.env["ir.sequence"].next_by_code("crossovered.budget.custom") or _("New")
            if vals.get("department_id") and not vals.get("scope"):
                vals["scope"] = "department"
        return super().create(vals_list)

    def action_budget_confirm(self):
        for rec in self:
            if rec.department_id and not rec.department_manager_user_id:
                raise UserError(
                    _("Please set a Department Manager user for the selected department before submitting."))
        res = super().action_budget_confirm()
        for rec in self:
            if rec.state == "confirm" and rec.approval_state == "draft":
                rec.approval_state = "pm_approval"
        return res

    def action_pm_approve(self):
        for rec in self:
            if rec.state != "confirm" or rec.approval_state != "pm_approval":
                continue
            if not rec.can_pm_approve:
                raise UserError(_("Only Department Manager or Project Manager can approve at this stage."))
            rec.approval_state = "accounts_approval"

    def action_accounts_approve(self):
        for rec in self:
            if rec.state != "confirm" or rec.approval_state != "accounts_approval":
                continue
            if not rec.can_accounts_approve:
                raise UserError(_("Only Accounts can approve at this stage."))
            rec.approval_state = "md_approval"

    def action_budget_validate(self):
        for rec in self:
            if rec.state == "confirm" and rec.approval_state != "md_approval":
                raise UserError(_("Budget requires PM, Accounts, and MD approvals before validation."))
        res = super().action_budget_validate()
        for rec in self:
            if rec.state in ("validate", "done"):
                rec.approval_state = "approved"
                rec._sync_cost_center_budget_allowance()
        return res

    def action_budget_done(self):
        res = super().action_budget_done()
        for rec in self:
            if rec.state == "done":
                rec.approval_state = "approved"
                rec._sync_cost_center_budget_allowance()
        return res

    def action_budget_cancel(self):
        res = super().action_budget_cancel()
        self.filtered(lambda b: b.state == "cancel").write({"approval_state": "rejected"})
        return res

    def action_resubmit_approval(self):
        for rec in self:
            if rec.approval_state != "rejected":
                continue
            if rec.state == "cancel":
                rec.action_budget_draft()
                rec.action_budget_confirm()
                continue
            if rec.state == "confirm":
                rec.write({"approval_state": "pm_approval"})
                continue
            raise UserError(_("Only cancelled/confirmed rejected budgets can be resubmitted."))

    def _sync_cost_center_budget_allowance(self):
        """Reflect approved budget lines into Cost Center budget allowances."""
        BudgetLine = self.env["crossovered.budget.lines"].sudo()
        AnalyticAccount = self.env["account.analytic.account"].sudo()

        for rec in self:
            analytics = rec.crossovered_budget_line.mapped("analytic_account_id").filtered(lambda a: a)
            if not analytics:
                continue

            grouped = BudgetLine.read_group(
                domain=[
                    ("analytic_account_id", "in", analytics.ids),
                    ("crossovered_budget_id.state", "in", ["validate", "done"]),
                ],
                fields=["analytic_account_id", "planned_amount:sum"],
                groupby=["analytic_account_id"],
                lazy=False,
            )
            totals = {
                item["analytic_account_id"][0]: item.get("planned_amount_sum", item.get("planned_amount", 0.0))
                for item in grouped
                if item.get("analytic_account_id")
            }

            for analytic in AnalyticAccount.browse(analytics.ids):
                analytic.budget_allowance = totals.get(analytic.id, 0.0)

    def write(self, vals):
        if vals.get("state") == "draft" and "approval_state" not in vals:
            vals["approval_state"] = "draft"
        return super().write(vals)
