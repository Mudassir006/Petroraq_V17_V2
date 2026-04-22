from odoo import _, api, fields, models
from odoo.exceptions import UserError
from markupsafe import escape


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
    product_breakdown_html = fields.Html(
        string="Products Breakdown",
        compute="_compute_product_breakdown",
    )
    product_breakdown_total = fields.Monetary(
        string="Products Grand Total",
        currency_field="company_currency_id",
        compute="_compute_product_breakdown",
    )
    company_currency_id = fields.Many2one(
        "res.currency",
        compute="_compute_company_currency_id",
    )

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

    @api.depends("company_id")
    def _compute_company_currency_id(self):
        for rec in self:
            rec.company_currency_id = rec.company_id.currency_id

    @api.depends(
        "sale_order_id.order_line",
        "sale_order_id.order_line.display_type",
        "sale_order_id.order_line.product_id",
        "sale_order_id.order_line.product_uom_qty",
        "sale_order_id.order_line.price_subtotal",
        "work_order_id.boq_line_ids",
        "work_order_id.boq_line_ids.display_type",
        "work_order_id.boq_line_ids.product_id",
        "work_order_id.boq_line_ids.qty",
        "work_order_id.boq_line_ids.total",
        "work_order_id.boq_line_ids.section_name",
    )
    def _compute_product_breakdown(self):
        for rec in self:
            section_data = {}
            grand_total = 0.0

            def _line_key(product):
                return product.display_name if product else _("Unnamed Product")

            if rec.work_order_id:
                for line in rec.work_order_id.boq_line_ids:
                    if line.display_type in ("line_section", "line_note") or not line.product_id:
                        continue
                    section = line.section_name or _("Unsectioned")
                    section_data.setdefault(section, {})
                    key = _line_key(line.product_id)
                    section_data[section].setdefault(key, {"qty": 0.0, "amount": 0.0})
                    section_data[section][key]["qty"] += line.qty or 0.0
                    section_data[section][key]["amount"] += line.total or 0.0
                    grand_total += line.total or 0.0
            elif rec.sale_order_id:
                section = _("Products")
                section_data.setdefault(section, {})
                current_section = section
                for line in rec.sale_order_id.order_line:
                    if line.display_type == "line_section":
                        current_section = line.name or _("Unsectioned")
                        section_data.setdefault(current_section, {})
                        continue
                    if line.display_type in ("line_note",) or not line.product_id:
                        continue
                    key = _line_key(line.product_id)
                    section_data[current_section].setdefault(key, {"qty": 0.0, "amount": 0.0})
                    section_data[current_section][key]["qty"] += line.product_uom_qty or 0.0
                    section_data[current_section][key]["amount"] += line.price_subtotal or 0.0
                    grand_total += line.price_subtotal or 0.0

            if not section_data:
                rec.product_breakdown_html = _("<p>No source Sale Order/Work Order products found.</p>")
                rec.product_breakdown_total = 0.0
                continue

            currency = rec.company_currency_id or rec.company_id.currency_id
            html = []
            for section_name, products in section_data.items():
                html.append(f"<h4>{escape(section_name)}</h4>")
                html.append("<table class='table table-sm o_list_table'>")
                html.append("<thead><tr><th>Product</th><th class='text-end'>Quantity</th><th class='text-end'>Total</th></tr></thead>")
                html.append("<tbody>")
                section_total = 0.0
                for product_name, values in products.items():
                    section_total += values["amount"]
                    html.append(
                        "<tr>"
                        f"<td>{escape(product_name)}</td>"
                        f"<td class='text-end'>{values['qty']:.2f}</td>"
                        f"<td class='text-end'>{currency.symbol or ''} {values['amount']:.2f}</td>"
                        "</tr>"
                    )
                html.append(
                    "<tr>"
                    "<td><strong>Section Total</strong></td>"
                    "<td></td>"
                    f"<td class='text-end'><strong>{currency.symbol or ''} {section_total:.2f}</strong></td>"
                    "</tr>"
                )
                html.append("</tbody></table>")

            html.append(f"<h3>{_('Grand Total')}: {currency.symbol or ''} {grand_total:.2f}</h3>")
            rec.product_breakdown_html = "".join(html)
            rec.product_breakdown_total = grand_total
