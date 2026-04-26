from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    work_order_id = fields.Many2one("pr.work.order", string="Work Order", readonly=True)
    project_id = fields.Many2one("project.project", string="Construction Project", readonly=True)
    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Cost Center",
        readonly=True,
        help="Cost center linked to this project / work order."
    )
    inquiry_type = fields.Selection(
        [('construction', 'Contracting'), ('trading', 'Trading')],
        string="Inquiry Type",
        default="trading",
    )
    trading_expense_bucket_id = fields.Many2one(
        "crossovered.budget",
        string="Trading Budget",
        copy=False,
        readonly=True,
    )
    expense_bucket_id = fields.Many2one(
        "crossovered.budget",
        string="Budget",
        compute="_compute_expense_bucket_id",
    )
    expense_bucket_count = fields.Integer(
        string="Expense Bucket Count",
        compute="_compute_expense_bucket_id",
    )

    @api.depends("trading_expense_bucket_id", "work_order_id", "work_order_id.expense_bucket_id")
    def _compute_expense_bucket_id(self):
        for order in self:
            bucket = order.trading_expense_bucket_id or order.work_order_id.expense_bucket_id
            order.expense_bucket_id = bucket
            order.expense_bucket_count = 1 if bucket else 0

    def _get_trading_bucket_source_amount(self):
        self.ensure_one()
        cost_based_total = sum(
            (line.cost_price_unit or 0.0) * (line.product_uom_qty or 0.0)
            for line in self.order_line.filtered(
                lambda l: not l.display_type and not l.is_downpayment
            )
        )
        return cost_based_total or self.base_cost_total or 0.0

    def _ensure_trading_expense_bucket(self):
        Budget = self.env["crossovered.budget"].sudo()
        BudgetLine = self.env["crossovered.budget.lines"].sudo()
        AnalyticAccount = self.env["account.analytic.account"].sudo()
        today = fields.Date.context_today(self)
        for order in self:
            if order.inquiry_type != "trading":
                continue
            source_amount = order._get_trading_bucket_source_amount()
            if source_amount <= 0.0:
                continue

            if not order.trading_expense_bucket_id:
                bucket = Budget.create({
                    "name": _("%s - Trading Budget") % (order.name or _("Quotation")),
                    "scope": "trading",
                    "expense_type": "capex",
                    "sale_order_id": order.id,
                    "source_budget_limit": source_amount,
                    "date_from": today,
                    "date_to": today,
                    "company_id": order.company_id.id,
                    "user_id": self.env.user.id,
                })
                order.sudo().write({"trading_expense_bucket_id": bucket.id})
            else:
                bucket = order.trading_expense_bucket_id.sudo()
                write_vals = {}
                if bucket.sale_order_id != order:
                    write_vals["sale_order_id"] = order.id
                if not bucket.source_budget_limit:
                    write_vals["source_budget_limit"] = source_amount
                if write_vals:
                    bucket.write(write_vals)

            trading_cc = bucket.crossovered_budget_line[:1].analytic_account_id
            if not trading_cc:
                cc_vals = {
                    "name": _("%s - Trading") % (order.name or _("Trading")),
                    "company_id": order.company_id.id,
                    "partner_id": order.partner_id.id,
                    "budget_type": "capex",
                    "budget_allowance": source_amount,
                }
                plan_ref = self.env.ref("pr_account.pr_account_analytic_plan_our_project", raise_if_not_found=False)
                if plan_ref and "plan_id" in AnalyticAccount._fields:
                    cc_vals["plan_id"] = plan_ref.id
                trading_cc = AnalyticAccount.create(cc_vals)
                BudgetLine.create({
                    "crossovered_budget_id": bucket.id,
                    "analytic_account_id": trading_cc.id,
                    "date_from": bucket.date_from or today,
                    "date_to": bucket.date_to or today,
                    "planned_amount": source_amount,
                })
            else:
                bucket_line = bucket.crossovered_budget_line.filtered(
                    lambda l: l.analytic_account_id == trading_cc
                )[:1]
                if bucket_line:
                    bucket_line.write({
                        "planned_amount": source_amount,
                    })

    def _remove_trading_expense_bucket(self):
        for order in self:
            if not order.trading_expense_bucket_id:
                continue
            linked_pr_count = self.env["custom.pr"].sudo().search_count([
                ("expense_bucket_id", "=", order.trading_expense_bucket_id.id)
            ])
            if linked_pr_count:
                raise UserError(
                    _(
                        "Cannot delete trading expense bucket %s because it is already linked to Purchase Requisitions."
                    ) % order.trading_expense_bucket_id.display_name
                )
            order.trading_expense_bucket_id.sudo().unlink()
            order.trading_expense_bucket_id = False

    def write(self, vals):
        res = super().write(vals)
        if "inquiry_type" in vals:
            self.filtered(lambda o: o.inquiry_type != "trading")._remove_trading_expense_bucket()
            self.filtered(lambda o: o.inquiry_type == "trading" and o.state in ("sale", "done"))._ensure_trading_expense_bucket()
        return res

    def _action_cancel(self):
        self._remove_trading_expense_bucket()
        return super()._action_cancel()

    def action_draft(self):
        self._remove_trading_expense_bucket()
        return super().action_draft()

    def action_reset_to_draft(self):
        self._remove_trading_expense_bucket()
        return super().action_reset_to_draft()

    def create_revision(self):
        self._remove_trading_expense_bucket()
        return super().create_revision()

    def action_confirm(self):
        res = super().action_confirm()
        self.filtered(lambda o: o.inquiry_type == "trading")._ensure_trading_expense_bucket()
        return res

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

    def action_create_work_order(self):
        """Create Work Order + Project and copy BOQ lines from SO"""

        self.ensure_one()
        order = self

        # If WO already exists → open instead of creating
        if order.work_order_id:
            return {
                "type": "ir.actions.act_window",
                "res_model": "pr.work.order",
                "view_mode": "form",
                "res_id": order.work_order_id.id,
            }

        Project = self.env["project.project"]
        WorkOrder = self.env["pr.work.order"]

        existing_projects = (
            order.project_id
            or order.order_line.mapped("project_id")
        )
        project = existing_projects[:1] if existing_projects else False

        # --------------------------
        # 1) Create Project (only if not already created by SO confirmation)
        # --------------------------
        if not project:
            project_vals = {
                "name": order.order_inquiry_id.description or order.name,
                "partner_id": order.partner_id.id,
                "company_id": order.company_id.id,
            }
            if order.analytic_account_id:
                project_vals["analytic_account_id"] = order.analytic_account_id.id

            project = Project.create(project_vals)

        # --------------------------
        # 2) Create Work Order Header
        # --------------------------
        analytic_account = order.analytic_account_id or project.analytic_account_id
        work_order_vals = {
            # "name": order.name,
            "company_id": order.company_id.id,
            "sale_order_id": order.id,
            "partner_id": order.partner_id.id,
            "project_id": project.id if project else False,
            "contract_amount": order.final_grand_total,
        }
        if analytic_account:
            work_order_vals["analytic_account_id"] = analytic_account.id

        work_order = WorkOrder.create(work_order_vals)

        # --------------------------
        # 3) LINK EXISTING PICKINGS / MOVES TO THIS WO  🔥
        # --------------------------
        for picking in order.picking_ids:
            picking.move_ids_without_package.write({
                "work_order_id": work_order.id,
            })

        # --------------------------
        # 4) Auto-create Cost Centers (one per SO Section)
        # --------------------------
        wo_cost_center_model = self.env["pr.work.order.cost.center"]
        analytic_model = self.env["account.analytic.account"]

        sections = [
            l for l in order.order_line
            if l.display_type == "line_section"
        ]

        section_amounts = {}
        current_section = False
        for line in order.order_line:
            if line.display_type == "line_section":
                current_section = line.name
                section_amounts.setdefault(current_section, 0.0)
                continue
            if line.display_type:
                continue
            if current_section:
                section_amounts[current_section] = section_amounts.get(current_section, 0.0) + (line.price_subtotal or 0.0)

        for sec in sections:
            analytic_vals = {
                "name": f"{order.name} - {sec.name}",
                "company_id": order.company_id.id,
                "plan_id": self.env.ref("pr_account.pr_account_analytic_plan_our_project").id,
                "partner_id": order.partner_id.id,
            }
            if "budget_type" in analytic_model._fields:
                analytic_vals["budget_type"] = "capex"
            if "budget_allowance" in analytic_model._fields:
                analytic_vals["budget_allowance"] = section_amounts.get(sec.name, 0.0)

            analytic = analytic_model.create(analytic_vals)

            wo_cost_center_model.create({
                "work_order_id": work_order.id,
                "section_name": sec.name,
                "analytic_account_id": analytic.id,
                "partner_id": order.partner_id.id,
                "department_id": False,
                "section_id": False,
            })

        current_section = False

        for line in order.order_line:
            if line.display_type == "line_section":
                current_section = line.name

            work_order.boq_line_ids.create({
                "work_order_id": work_order.id,
                "display_type": line.display_type or False,
                "name": line.name,
                "product_id": line.product_id.id if not line.display_type else False,
                "uom_id": line.product_uom.id if not line.display_type else False,
                "qty": line.product_uom_qty if not line.display_type else 0,
                # "unit_cost": 0,
                "section_name": current_section,
            })

        # --------------------------
        # 5) Auto Create Tasks from BOQ Sections
        # --------------------------
        if project:
            for boq in work_order.boq_line_ids:
                if boq.display_type == "line_section":
                    self.env["project.task"].create({
                        "name": boq.name,
                        "project_id": project.id,
                        "work_order_id": work_order.id,
                        "company_id": work_order.company_id.id,
                    })

        # --------------------------
        # 6) Link SO fields
        # --------------------------
        order.write({
            "work_order_id": work_order.id,
            "project_id": project.id if project else False,
            "analytic_account_id": work_order.analytic_account_id.id if work_order.analytic_account_id else False,
        })

        # --------------------------
        # 7) Open created Work Order
        # --------------------------
        return {
            "type": "ir.actions.act_window",
            "res_model": "pr.work.order",
            "view_mode": "form",
            "res_id": work_order.id,
        }

    def action_work_order(self):
        self.ensure_one()
        work_order_id = self.work_order_id
        if not work_order_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'pr.work.order',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': work_order_id.id,
            'views': [(False, 'form')],
        }
