from odoo import api, fields, models, _


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