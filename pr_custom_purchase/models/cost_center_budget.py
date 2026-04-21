from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    expense_bucket_id = fields.Many2one(
        "pr.expense.bucket",
        string="Expense",
        help="Expense bucket (Capex/Opex for Department/Project) this cost center belongs to.",
    )

    budget_type = fields.Selection(
        [("opex", "Opex"), ("capex", "Capex")],
        string="Budget Type",
    )
    budget_code = fields.Char(string="Budget Code")
    budget_allowance = fields.Float(string="Budget Allowance")
    budget_spent = fields.Float(string="Budget Spent", compute="_compute_budget_metrics", store=False)
    budget_left = fields.Float(string="Budget Left", compute="_compute_budget_metrics", store=False)

    @api.depends("budget_allowance", "budget_code", "budget_type")
    def _compute_budget_metrics(self):
        PurchaseOrder = self.env["purchase.order"].sudo()
        BudgetLine = self.env["crossovered.budget.lines"].sudo()
        for rec in self:
            spent = 0.0
            if rec.id:
                pos = PurchaseOrder.search([
                    ("state", "in", ["pending", "purchase", "done"]),
                    ("order_line.analytic_distribution", "!=", False),
                ])
                for po in pos:
                    for line in po.order_line:
                        distribution = line.analytic_distribution or {}
                        percentage = distribution.get(str(rec.id), 0.0)
                        try:
                            percentage = float(percentage)
                        except (TypeError, ValueError):
                            percentage = 0.0
                        if not percentage:
                            continue
                        spent += (line.price_subtotal or 0.0) * (percentage / 100.0)

            effective_allowance = rec.budget_allowance or 0.0
            if rec.id and BudgetLine:
                approved_lines = BudgetLine.search([
                    ("analytic_account_id", "=", rec.id),
                    ("crossovered_budget_id.state", "in", ["validate", "done"]),
                ])
                approved_allowance = sum(approved_lines.mapped("planned_amount"))
                if approved_allowance > 0.0:
                    effective_allowance = approved_allowance

            rec.budget_spent = spent
            rec.budget_left = effective_allowance - spent

    @api.model
    def get_cost_center_budget(self, budget_type, budget_code):
        if not budget_type or not budget_code:
            return False

        return self.sudo().search([
            ("budget_type", "=", budget_type),
            ("budget_code", "=", budget_code),
        ], limit=1)

    @api.model
    def validate_budget_or_raise(self, budget_type, budget_code, required_amount=0.0):
        rec = self.get_cost_center_budget(budget_type, budget_code)
        if not rec:
            raise ValidationError(_("No cost center found for the selected budget type/code."))

        if rec.budget_left <= 0:
            raise ValidationError(_("No budget left for cost center %s.") % (rec.budget_code or rec.display_name))

        if required_amount and rec.budget_left < required_amount:
            raise ValidationError(
                _("Insufficient budget for cost center %s. Remaining: %s, Required: %s")
                % (rec.budget_code or rec.display_name, rec.budget_left, required_amount)
            )

        return rec

    @api.constrains("budget_allowance", "expense_bucket_id")
    def _check_budget_within_bucket(self):
        for rec in self:
            if not rec.expense_bucket_id:
                continue
            bucket = rec.expense_bucket_id
            total = sum(bucket.line_ids.mapped("budget_allowance"))
            if total > bucket.budget_amount:
                raise ValidationError(
                    _("Total cost center budget (%s) cannot exceed bucket budget (%s).")
                    % (total, bucket.budget_amount)
                )