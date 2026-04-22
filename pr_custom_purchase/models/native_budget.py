from markupsafe import escape

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
    sale_order_id = fields.Many2one("sale.order", string="Sale Order")
    work_order_id = fields.Many2one("pr.work.order", string="Work Order")
    source_budget_limit = fields.Float(string="Source Budget Limit")
    source_products_html = fields.Html(
        string="Source Products",
        compute="_compute_source_products_data",
        sanitize=False,
        readonly=True,
    )
    source_products_total = fields.Monetary(
        string="Source Products Total",
        compute="_compute_source_products_data",
        currency_field="company_currency_id",
        readonly=True,
    )
    company_currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="company_id.currency_id",
        readonly=True,
    )
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

    def _compute_source_products_data(self):
        for rec in self:
            rows = []
            total = 0.0
            current_section = False

            if rec.work_order_id:
                for line in rec.work_order_id.boq_line_ids.sorted(key=lambda l: (l.sequence, l.id)):
                    if line.display_type == "line_section":
                        current_section = line.name or line.section_name
                        continue
                    if line.display_type == "line_note":
                        continue
                    section_name = line.section_name or current_section or _("General")
                    line_total = line.total or ((line.qty or 0.0) * (line.unit_cost or 0.0))
                    rows.append({
                        "section": section_name,
                        "product": line.product_id.display_name or line.name or "",
                        "qty": line.qty or 0.0,
                        "unit_price": line.unit_cost or 0.0,
                        "line_total": line_total,
                    })
                    total += line_total
            elif rec.sale_order_id:
                for line in rec.sale_order_id.order_line.sorted(key=lambda l: (l.sequence, l.id)):
                    if line.display_type == "line_section":
                        current_section = line.name
                        continue
                    if line.display_type == "line_note":
                        continue
                    section_name = current_section or _("General")
                    line_total = line.price_subtotal or ((line.product_uom_qty or 0.0) * (line.price_unit or 0.0))
                    rows.append({
                        "section": section_name,
                        "product": line.product_id.display_name or line.name or "",
                        "qty": line.product_uom_qty or 0.0,
                        "unit_price": line.price_unit or 0.0,
                        "line_total": line_total,
                    })
                    total += line_total

            if not rows:
                rec.source_products_html = "<p>%s</p>" % escape(_("No source products found from Sale Order / Work Order."))
                rec.source_products_total = 0.0
                continue

            html_rows = []
            current = None
            section_total = 0.0
            for row in rows:
                if current != row["section"]:
                    if current is not None:
                        html_rows.append(
                            f"<tr class='o_subtotal'><td colspan='4'><b>{escape(_('Section Total'))}</b></td>"
                            f"<td class='text-end'><b>{section_total:,.2f}</b></td></tr>"
                        )
                    current = row["section"]
                    section_total = 0.0
                    html_rows.append(
                        f"<tr class='table-secondary'><td colspan='5'><b>{escape(current)}</b></td></tr>"
                    )
                section_total += row["line_total"]
                html_rows.append(
                    "<tr>"
                    f"<td></td><td>{escape(row['product'])}</td>"
                    f"<td class='text-end'>{row['qty']:,.2f}</td>"
                    f"<td class='text-end'>{row['unit_price']:,.2f}</td>"
                    f"<td class='text-end'>{row['line_total']:,.2f}</td>"
                    "</tr>"
                )
            html_rows.append(
                f"<tr class='o_subtotal'><td colspan='4'><b>{escape(_('Section Total'))}</b></td>"
                f"<td class='text-end'><b>{section_total:,.2f}</b></td></tr>"
            )
            html_rows.append(
                f"<tr class='table-primary'><td colspan='4'><b>{escape(_('Grand Total'))}</b></td>"
                f"<td class='text-end'><b>{total:,.2f}</b></td></tr>"
            )

            rec.source_products_html = (
                "<table class='table table-sm table-hover o_list_table'>"
                "<thead><tr>"
                f"<th>{escape(_('Section'))}</th>"
                f"<th>{escape(_('Product'))}</th>"
                f"<th class='text-end'>{escape(_('Qty'))}</th>"
                f"<th class='text-end'>{escape(_('Unit Price'))}</th>"
                f"<th class='text-end'>{escape(_('Total'))}</th>"
                "</tr></thead>"
                f"<tbody>{''.join(html_rows)}</tbody></table>"
            )
            rec.source_products_total = total
