from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import format_amount, html_escape

SECTION_TYPES = [
    ("material", "Material"),
    ("labor", "Labor"),
    ("equipment", "Equipment"),
    ("subcontract", "Sub Contract / TPS"),
]


class PetroraqEstimation(models.Model):
    _name = "petroraq.estimation"
    _description = "Estimation"
    _inherit = ["mail.thread", "mail.activity.mixin", "base.revision"]

    current_revision_id = fields.Many2one(
        comodel_name="petroraq.estimation",
        string="Current revision",
        readonly=True,
        copy=True,
    )
    old_revision_ids = fields.One2many(
        comodel_name="petroraq.estimation",
        inverse_name="current_revision_id",
        string="Old revisions",
        readonly=True,
        domain=["|", ("active", "=", False), ("active", "=", True)],
        context={"active_test": False},
    )

    _sql_constraints = [
        (
            "revision_unique",
            "unique(unrevisioned_name, revision_number, company_id)",
            "Estimation Reference and revision must be unique per Company.",
        )
    ]

    approval_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("to_manager", "Manager Approve"),
            ("to_md", "MD Approve"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        default="draft",
        tracking=True,
        copy=False,
    )
    approval_comment = fields.Text("Approval Comment", tracking=True)
    show_reject_button = fields.Boolean(compute="_compute_show_reject_button")

    name = fields.Char(
        string="Estimation",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
    )
    partner_id = fields.Many2one("res.partner", string="Customer", required=True, tracking=True)
    date = fields.Date(string="Date", default=fields.Date.context_today, tracking=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )
    line_ids = fields.One2many(
        "petroraq.estimation.line",
        "estimation_id",
        string="Estimation Lines",
    )
    display_line_ids = fields.One2many(
        "petroraq.estimation.display.line",
        "estimation_id",
        string="Estimation Display Lines",
        readonly=True,
        copy=False,
    )

    material_line_ids = fields.One2many(
        "petroraq.estimation.line",
        "estimation_id",
        string="Material Lines",
        domain=[("section_type", "=", "material")],
    )
    labor_line_ids = fields.One2many(
        "petroraq.estimation.line",
        "estimation_id",
        string="Labor Lines",
        domain=[("section_type", "=", "labor")],
    )
    equipment_line_ids = fields.One2many(
        "petroraq.estimation.line",
        "estimation_id",
        string="Equipment Lines",
        domain=[("section_type", "=", "equipment")],
    )
    subcontract_line_ids = fields.One2many(
        "petroraq.estimation.line",
        "estimation_id",
        string="Sub Contract / TPS Lines",
        domain=[("section_type", "=", "subcontract")],
    )

    sale_order_id = fields.Many2one("sale.order", string="Quotation", readonly=True, copy=False)
    sale_order_state = fields.Selection(
        related="sale_order_id.state",
        string="Quotation Status",
        readonly=True,
    )
    quotation_approval_state = fields.Selection(
        related="sale_order_id.approval_state",
        string="Quotation Approval Status",
        readonly=True,
    )
    is_locked_for_edit = fields.Boolean(
        compute="_compute_is_locked_for_edit",
        string="Locked For Edit",
    )
    work_order_id = fields.Many2one("pr.work.order", string="Work Order", readonly=True, copy=False)

    material_total = fields.Monetary(
        string="Material Total",
        compute="_compute_totals",
        currency_field="currency_id",
        store=False,
    )
    labor_total = fields.Monetary(
        string="Labor Total",
        compute="_compute_totals",
        currency_field="currency_id",
        store=False,
    )
    equipment_total = fields.Monetary(
        string="Equipment Total",
        compute="_compute_totals",
        currency_field="currency_id",
        store=False,
    )
    subcontract_total = fields.Monetary(
        string="Sub Contract / TPS Total",
        compute="_compute_totals",
        currency_field="currency_id",
        store=False,
    )
    total_amount = fields.Monetary(
        string="Total",
        compute="_compute_totals",
        currency_field="currency_id",
        store=False,
    )
    overhead_percent = fields.Float(
        string="Over Head (%)",
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
        string="Over Head Amount",
        compute="_compute_totals",
        currency_field="currency_id",
        store=False,
    )
    risk_amount = fields.Monetary(
        string="Risk Amount",
        compute="_compute_totals",
        currency_field="currency_id",
        store=False,
    )
    buffer_total_amount = fields.Monetary(
        string="Computed Total Amount",
        compute="_compute_totals",
        currency_field="currency_id",
        store=False,
        help="Total amount including overhead and risk (no profit).",
    )
    profit_amount = fields.Monetary(
        string="Profit Amount",
        compute="_compute_totals",
        currency_field="currency_id",
        store=False,
    )
    total_with_profit = fields.Monetary(
        string="Total With Profit",
        compute="_compute_totals",
        currency_field="currency_id",
        store=False,
    )

    @api.model
    def create(self, vals):
        if vals.get("name", _("New")) == _("New"):
            vals["name"] = self.env["ir.sequence"].next_by_code("petroraq.estimation") or _("New")
        return super().create(vals)

    def copy(self, default=None):
        default = dict(default or {})
        if "line_ids" not in default:
            line_vals = []
            for line in self.line_ids:
                data = line.copy_data()[0]
                data.pop("estimation_id", None)
                line_vals.append((0, 0, data))
            default["line_ids"] = line_vals
        return super().copy(default)

    def _ensure_unlocked(self):
        if self.env.context.get("allow_estimation_write"):
            return
        locked = self.filtered("is_locked_for_edit")
        if locked:
            raise UserError(_("This estimation is locked because a quotation has been created."))

    @api.depends("sale_order_id", "sale_order_id.approval_state")
    def _compute_is_locked_for_edit(self):
        locked_states = {"to_manager", "to_md", "approved"}
        for record in self:
            record.is_locked_for_edit = bool(
                record.sale_order_id and record.sale_order_id.approval_state in locked_states
            )

    def write(self, vals):
        self._ensure_unlocked()
        return super().write(vals)

    def unlink(self):
        self._ensure_unlocked()
        return super().unlink()

    @api.depends_context("uid")
    @api.depends("approval_state")
    def _compute_show_reject_button(self):
        user = self.env.user
        for record in self:
            record.show_reject_button = (
                    (record.approval_state == "to_manager" and user.has_group(
                        "petroraq_sale_workflow.group_sale_approval_manager"))
                    or
                    (record.approval_state == "to_md" and user.has_group(
                        "petroraq_sale_workflow.group_sale_approval_md"))
            )

    @api.onchange("partner_id")
    def _onchange_partner_company(self):
        for record in self:
            if record.partner_id.company_id and record.partner_id.company_id != record.company_id:
                record.company_id = record.partner_id.company_id

    @api.depends(
        "line_ids.subtotal",
        "line_ids.section_type",
        "overhead_percent",
        "risk_percent",
        "profit_percent",
    )
    def _compute_totals(self):
        for record in self:
            material_total = sum(record.line_ids.filtered(lambda l: l.section_type == "material").mapped("subtotal"))
            labor_total = sum(record.line_ids.filtered(lambda l: l.section_type == "labor").mapped("subtotal"))
            equipment_total = sum(record.line_ids.filtered(lambda l: l.section_type == "equipment").mapped("subtotal"))
            subcontract_total = sum(
                record.line_ids.filtered(lambda l: l.section_type == "subcontract").mapped("subtotal"))
            record.material_total = material_total
            record.labor_total = labor_total
            record.equipment_total = equipment_total
            record.subcontract_total = subcontract_total
            base_total = material_total + labor_total + equipment_total + subcontract_total
            overhead_amount = base_total * (record.overhead_percent or 0.0) / 100.0
            risk_amount = base_total * (record.risk_percent or 0.0) / 100.0
            buffer_total = base_total + overhead_amount + risk_amount
            profit_amount = buffer_total * (record.profit_percent or 0.0) / 100.0

            record.total_amount = base_total
            record.overhead_amount = overhead_amount
            record.risk_amount = risk_amount
            record.buffer_total_amount = buffer_total
            record.profit_amount = profit_amount
            record.total_with_profit = buffer_total + profit_amount

    @api.onchange("overhead_percent", "risk_percent", "profit_percent")
    def _onchange_percent_validation(self):
        for field in ("overhead_percent", "risk_percent", "profit_percent"):
            value = self[field]
            if value < 0:
                raise UserError(_("Percentage cannot be negative."))
            if value > 100:
                raise UserError(_("Percentage cannot exceed 100%."))

    @api.constrains("overhead_percent", "risk_percent", "profit_percent")
    def _check_percentages(self):
        for record in self:
            for field_name in ("overhead_percent", "risk_percent", "profit_percent"):
                value = record[field_name]
                if value < 0:
                    raise ValidationError(_("Percentage cannot be negative."))
                if value > 100:
                    raise ValidationError(_("Percentage cannot exceed 100%."))

    def action_create_sale_order(self):
        self.ensure_one()
        order = self._ensure_sale_order()
        return {
            "type": "ir.actions.act_window",
            "name": _("Quotation"),
            "res_model": "sale.order",
            "res_id": order.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_revisions(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Estimations"),
            "res_model": "petroraq.estimation",
            "view_mode": "tree,form",
            "domain": ["|", ("active", "=", False), ("active", "=", True)],
            "context": {
                "active_test": 0,
                "search_default_current_revision_id": self.id,
                "default_current_revision_id": self.id,
            },
            "target": "current",
        }

    def create_revision(self):
        return super(PetroraqEstimation, self.with_context(allow_estimation_write=True)).create_revision()

    def _ensure_sale_order(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_("Please set a customer before creating a quotation."))
        if self.sale_order_id:
            return self.sale_order_id

        term = self.env.ref("petroraq_sale_workflow.payment_term_immediate", raise_if_not_found=False)
        company = self.company_id
        if self.partner_id.company_id:
            company = self.partner_id.company_id
        partner = self.partner_id.with_company(company)
        addresses = partner.address_get(["invoice", "delivery"])
        order_vals = self._prepare_sale_order_vals(company, addresses, term)
        previous_order = self._get_previous_revision_sale_order()
        if previous_order:
            order = previous_order.with_company(company).copy_revision_with_context()
            order.write(order_vals)
        else:
            order = self.env["sale.order"].with_company(company).create(order_vals)

        self.with_context(allow_estimation_write=True).sale_order_id = order.id
        return order

    def _prepare_sale_order_vals(self, company, addresses, term):
        order_vals = {
            "partner_id": self.partner_id.id,
            "company_id": company.id,
            "currency_id": company.currency_id.id,
            "inquiry_type": "construction",
            "payment_term_id": term.id if term else False,
            "partner_invoice_id": addresses.get("invoice"),
            "partner_shipping_id": addresses.get("delivery"),
            "estimation_id": self.id,
        }
        if self.order_inquiry_id:
            order_vals["order_inquiry_id"] = self.order_inquiry_id.id
        return order_vals

    def _get_previous_revision_sale_order(self):
        self.ensure_one()
        revisions = self.with_context(active_test=False).old_revision_ids.filtered("sale_order_id")
        if not revisions:
            return False
        previous_revision = revisions.sorted(
            key=lambda r: (r.revision_number or 0, r.id)
        )[-1]
        return previous_revision.sale_order_id

    def _prepare_work_order_boq_lines(self, work_order):
        section_map = {
            "material": _("Material"),
            "labor": _("Labor"),
            "equipment": _("Equipment"),
            "subcontract": _("Sub Contract / TPS"),
        }
        lines = []
        estimation_lines = self.line_ids.sorted(lambda l: (l.section_type or "", l.id))
        for section_type in SECTION_TYPES:
            section_lines = estimation_lines.filtered(lambda l: l.section_type == section_type[0])
            if not section_lines:
                continue
            section_name = section_map.get(section_type[0], section_type[1])
            lines.append({
                "work_order_id": work_order.id,
                "display_type": "line_section",
                "name": section_name,
                "section_name": section_name,
            })
            for line in section_lines:
                if not line.product_id:
                    lines.append({
                        "work_order_id": work_order.id,
                        "display_type": "line_note",
                        "name": line.name or section_name,
                        "section_name": section_name,
                    })
                    continue
                qty = line.quantity_hours if line.section_type in ("labor", "equipment") else (line.quantity or 0.0)
                uom = line.uom_id or line.product_id.uom_id
                lines.append({
                    "work_order_id": work_order.id,
                    "display_type": "product",
                    "name": line.name or (line.product_id.display_name if line.product_id else section_name),
                    "product_id": line.product_id.id,
                    "uom_id": uom.id if uom else False,
                    "qty": qty,
                    "unit_cost": line.unit_cost or 0.0,
                    "section_name": section_name,
                })
        return lines

    def _rebuild_display_lines(self):
        section_map = {
            "material": _("Material"),
            "labor": _("Labor"),
            "equipment": _("Equipment"),
            "subcontract": _("Sub Contract / TPS"),
        }
        DisplayLine = self.env["petroraq.estimation.display.line"]
        for estimation in self:
            estimation.display_line_ids.unlink()
            sequence = 1
            estimation_lines = estimation.line_ids.sorted(lambda l: (l.section_type or "", l.id))
            for section_type, section_label in SECTION_TYPES:
                section_lines = estimation_lines.filtered(lambda l: l.section_type == section_type)
                if not section_lines:
                    continue
                section_name = section_map.get(section_type, section_label)
                DisplayLine.create({
                    "estimation_id": estimation.id,
                    "display_type": "line_section",
                    "name": section_name,
                    "sequence": sequence,
                    "section_type": section_type,
                })
                sequence += 1
                for line in section_lines:
                    display_vals = {
                        "estimation_id": estimation.id,
                        "display_type": False,
                        "name": line.name
                                or (line.product_id.display_name if line.product_id else section_name),
                        "product_id": line.product_id.id if line.product_id else False,
                        "uom_id": line.uom_id.id if line.uom_id else False,
                        "quantity": line.quantity or 0.0,
                        "quantity_hours": line.quantity_hours or 0.0,
                        "unit_cost": line.unit_cost or 0.0,
                        "sequence": sequence,
                        "section_type": section_type,
                    }
                    if not line.product_id:
                        display_vals["display_type"] = "line_note"
                    DisplayLine.create(display_vals)
                    sequence += 1

    def action_create_work_order(self):
        self.ensure_one()
        if self.work_order_id:
            return {
                "type": "ir.actions.act_window",
                "name": _("Work Order"),
                "res_model": "pr.work.order",
                "res_id": self.work_order_id.id,
                "view_mode": "form",
                "target": "current",
            }
        order = self._ensure_sale_order()
        if order.state != "sale":
            raise UserError(_("You can only create a work order after the quotation is confirmed."))

        if order.work_order_id:
            self.with_context(allow_estimation_write=True).work_order_id = order.work_order_id.id
            return {
                "type": "ir.actions.act_window",
                "name": _("Work Order"),
                "res_model": "pr.work.order",
                "res_id": order.work_order_id.id,
                "view_mode": "form",
                "target": "current",
            }

        Project = self.env["project.project"]
        WorkOrder = self.env["pr.work.order"]

        project_vals = {
            "name": order.order_inquiry_id.description if order.order_inquiry_id else (order.name or self.name),
            "partner_id": order.partner_id.id,
            "company_id": order.company_id.id,
        }
        if order.analytic_account_id:
            project_vals["analytic_account_id"] = order.analytic_account_id.id

        project = Project.create(project_vals)

        work_order_vals = {
            "company_id": order.company_id.id,
            "sale_order_id": order.id,
            "partner_id": order.partner_id.id,
            "project_id": project.id,
            "contract_amount": order.final_grand_total,
        }
        if order.analytic_account_id:
            work_order_vals["analytic_account_id"] = order.analytic_account_id.id

        work_order = WorkOrder.create(work_order_vals)

        for picking in order.picking_ids:
            picking.move_ids_without_package.write({
                "work_order_id": work_order.id,
            })

        section_map = {
            "material": _("Material"),
            "labor": _("Labor"),
            "equipment": _("Equipment"),
            "subcontract": _("Sub Contract / TPS"),
        }
        sections = [
            section_map.get(section_type[0], section_type[1])
            for section_type in SECTION_TYPES
            if self.line_ids.filtered(lambda l: l.section_type == section_type[0])
        ]

        section_amounts = {
            section_map.get(section_type[0], section_type[1]): sum(
                self.line_ids.filtered(lambda l: l.section_type == section_type[0]).mapped("subtotal")
            )
            for section_type in SECTION_TYPES
            if self.line_ids.filtered(lambda l: l.section_type == section_type[0])
        }

        wo_cost_center_model = self.env["pr.work.order.cost.center"]
        analytic_model = self.env["account.analytic.account"]
        analytic_plan = self.env.ref("pr_account.pr_account_analytic_plan_our_project")

        for section_name in sections:
            analytic_vals = {
                "name": f"{order.name} - {section_name}",
                "company_id": order.company_id.id,
                "plan_id": analytic_plan.id,
                "partner_id": order.partner_id.id,
            }
            if "budget_type" in analytic_model._fields:
                analytic_vals["budget_type"] = "capex"
            if "budget_allowance" in analytic_model._fields:
                analytic_vals["budget_allowance"] = section_amounts.get(section_name, 0.0)

            analytic = analytic_model.create(analytic_vals)

            wo_cost_center_model.create({
                "work_order_id": work_order.id,
                "section_name": section_name,
                "analytic_account_id": analytic.id,
                "partner_id": order.partner_id.id,
                "department_id": False,
                "section_id": False,
            })


        for line_vals in self._prepare_work_order_boq_lines(work_order):
            work_order.boq_line_ids.create(line_vals)

        for boq in work_order.boq_line_ids:
            if boq.display_type == 'line_section':
                self.env['project.task'].create({
                    'name': boq.name,
                    'project_id': project.id,
                    'work_order_id': work_order.id,
                    'company_id': work_order.company_id.id,
                })

        order.write({
            "work_order_id": work_order.id,
            "project_id": project.id,
            "analytic_account_id": work_order.analytic_account_id.id if work_order.analytic_account_id else False,
        })

        self.with_context(allow_estimation_write=True).work_order_id = work_order.id
        return {
            "type": "ir.actions.act_window",
            "name": _("Work Order"),
            "res_model": "pr.work.order",
            "res_id": work_order.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_confirm_estimation(self):
        for record in self:
            if not record.line_ids:
                raise UserError(_("Please add at least one estimation line."))
            record.approval_state = "to_manager"
            record.approval_comment = False

    def action_manager_approve(self):
        for record in self:
            if record.approval_state != "to_manager":
                raise UserError(_("This estimation is not awaiting manager approval."))
            record.approval_state = "to_md"

    def action_md_approve(self):
        for record in self:
            if record.approval_state != "to_md":
                raise UserError(_("This estimation is not awaiting MD approval."))
            record.approval_state = "approved"

    def action_reject(self):
        for record in self:
            if record.approval_state not in ("to_manager", "to_md", "draft"):
                raise UserError(_("Only waiting approvals can be rejected."))
            record.approval_state = "rejected"

    def action_reset_to_draft(self):
        for record in self:
            if record.approval_state == "rejected":
                record.approval_state = "draft"


class PetroraqEstimationLine(models.Model):
    _name = "petroraq.estimation.line"
    _description = "Estimation Line"
    _order = "section_type, id"

    estimation_id = fields.Many2one(
        "petroraq.estimation",
        string="Estimation",
        required=True,
        ondelete="cascade",
    )

    section_type = fields.Selection(
        SECTION_TYPES,
        string="Section",
        required=True,
        default=lambda self: self.env.context.get("default_section_type"),
    )

    product_id = fields.Many2one("product.product", string="Product")
    name = fields.Char(string="Description")

    # For Labor/Equipment the business wants:
    # (count) * (days) * (8 hours/day) = qty (hours)
    resource_count = fields.Float(string="Count", default=1.0)
    days = fields.Float(string="Days", default=1.0)
    hours_per_day = fields.Float(string="Hours/Day", default=8.0)

    quantity_hours = fields.Float(
        string="Total Hours",
        compute="_compute_quantity_hours",
        store=False,
        readonly=True,
    )

    quantity = fields.Float(
        string="Quantity",
        default=1.0,
        help="Used for Material/Subcontract. For Labor/Equipment the quantity is computed as Total Hours.",
    )

    qty_available = fields.Float(
        string="On Hand",
        related="product_id.qty_available",
        readonly=True,
    )
    virtual_available = fields.Float(
        string="Forecast",
        related="product_id.virtual_available",
        readonly=True,
    )
    free_qty = fields.Float(
        string="Free to Use",
        related="product_id.free_qty",
        readonly=True,
    )

    uom_id = fields.Many2one("uom.uom", string="Unit of Measure")

    currency_id = fields.Many2one(
        "res.currency",
        compute="_compute_currency_id",
        store=True,
        readonly=True,
    )

    unit_cost = fields.Monetary(string="Unit Cost", currency_field="currency_id")

    subtotal = fields.Monetary(
        string="Subtotal",
        currency_field="currency_id",
        compute="_compute_subtotal",
        store=False,
    )

    @api.depends("estimation_id.currency_id")
    def _compute_currency_id(self):
        for line in self:
            line.currency_id = line.estimation_id.currency_id if line.estimation_id else False

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for line in self:
            if not line.product_id:
                continue
            line.name = line.product_id.display_name
            # For Labor/Equipment we always calculate in hours.
            if line.section_type in ("labor", "equipment"):
                hour_uom = self.env.ref("uom.product_uom_hour", raise_if_not_found=False)
                line.uom_id = hour_uom.id if hour_uom else line.product_id.uom_id
            else:
                line.uom_id = line.product_id.uom_id
            line.unit_cost = line.product_id.standard_price

    @api.onchange("section_type")
    def _onchange_section_type(self):
        """Keep labor/equipment aligned with the business rule: 8h/day fixed and UoM is Hours."""
        for line in self:
            if line.section_type in ("labor", "equipment"):
                line.hours_per_day = 8.0
                hour_uom = self.env.ref("uom.product_uom_hour", raise_if_not_found=False)
                if hour_uom:
                    line.uom_id = hour_uom.id

    @api.depends("section_type", "resource_count", "days", "hours_per_day")
    def _compute_quantity_hours(self):
        for line in self:
            if line.section_type in ("labor", "equipment"):
                line.quantity_hours = (line.resource_count or 0.0) * (line.days or 0.0) * (line.hours_per_day or 0.0)
            else:
                line.quantity_hours = 0.0

    @api.depends(
        "section_type",
        "quantity",
        "quantity_hours",
        "unit_cost",
    )
    def _compute_subtotal(self):
        for line in self:
            qty = line.quantity_hours if line.section_type in ("labor", "equipment") else (line.quantity or 0.0)
            line.subtotal = qty * (line.unit_cost or 0.0)

    @api.model_create_multi
    def create(self, vals_list):
        estimations = self.env["petroraq.estimation"]
        for vals in vals_list:
            if vals.get("estimation_id"):
                estimations |= self.env["petroraq.estimation"].browse(vals["estimation_id"])
        estimations._ensure_unlocked()

        records = super().create(vals_list)
        records.mapped("estimation_id")._rebuild_display_lines()
        return records

    def write(self, vals):
        self.mapped("estimation_id")._ensure_unlocked()
        estimations = self.mapped("estimation_id")
        res = super().write(vals)
        (estimations | self.mapped("estimation_id"))._rebuild_display_lines()
        return res

    def unlink(self):
        self.mapped("estimation_id")._ensure_unlocked()
        estimations = self.mapped("estimation_id")
        res = super().unlink()
        estimations._rebuild_display_lines()
        return res


class PetroraqEstimationDisplayLine(models.Model):
    _name = "petroraq.estimation.display.line"
    _description = "Estimation Display Line"
    _order = "sequence, id"

    estimation_id = fields.Many2one(
        "petroraq.estimation",
        string="Estimation",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    display_type = fields.Selection(
        [
            ("line_section", "Section"),
            ("line_note", "Note"),
        ],
        default=False,
    )
    section_type = fields.Selection(SECTION_TYPES, string="Section")
    product_id = fields.Many2one("product.product", string="Product")
    name = fields.Char(string="Description")
    quantity = fields.Float(string="Quantity")
    quantity_hours = fields.Float(string="Total Hours")
    uom_id = fields.Many2one("uom.uom", string="Unit of Measure")
    currency_id = fields.Many2one(
        "res.currency",
        related="estimation_id.currency_id",
        store=True,
        readonly=True,
    )
    unit_cost = fields.Monetary(string="Unit Cost", currency_field="currency_id")
    subtotal = fields.Monetary(
        string="Subtotal",
        currency_field="currency_id",
        compute="_compute_subtotal",
        store=False,
    )
    section_subtotal_amount = fields.Monetary(
        string="Section Subtotal",
        compute="_compute_section_subtotal_amount",
        store=False,
        currency_field="currency_id",
        help="Subtotal of the lines within this section.",
    )
    section_subtotal_display = fields.Html(
        string="Section Subtotal Display",
        compute="_compute_section_subtotal_amount",
        sanitize=False,
        help="Formatted subtotal snippet for section headers.",
    )

    @api.depends(
        "section_type",
        "quantity",
        "quantity_hours",
        "unit_cost",
    )
    def _compute_subtotal(self):
        for line in self:
            qty = line.quantity_hours if line.section_type in ("labor", "equipment") else (line.quantity or 0.0)
            line.subtotal = qty * (line.unit_cost or 0.0)

    @api.depends(
        "display_type",
        "sequence",
        "section_type",
        "quantity",
        "quantity_hours",
        "unit_cost",
        "estimation_id.display_line_ids.display_type",
        "estimation_id.display_line_ids.sequence",
        "estimation_id.display_line_ids.section_type",
        "estimation_id.display_line_ids.quantity",
        "estimation_id.display_line_ids.quantity_hours",
        "estimation_id.display_line_ids.unit_cost",
    )
    def _compute_section_subtotal_amount(self):
        label = _("Sub Total")
        for line in self:
            line.section_subtotal_amount = 0.0
            line.section_subtotal_display = False

        for estimation in self.mapped("estimation_id"):
            subtotal = 0.0
            current_section = None
            ordered_lines = estimation.display_line_ids.sorted(key=lambda l: (l.sequence or 0, l.id or 0))

            for line in ordered_lines:
                if line.display_type == "line_section":
                    if current_section:
                        current_section._set_section_subtotal_values(subtotal, label)
                    current_section = line
                    subtotal = 0.0
                    line.section_subtotal_amount = 0.0
                    line.section_subtotal_display = False
                    continue

                if line.display_type:
                    continue

                qty = line.quantity_hours if line.section_type in ("labor", "equipment") else (line.quantity or 0.0)
                subtotal += qty * (line.unit_cost or 0.0)

            if current_section:
                current_section._set_section_subtotal_values(subtotal, label)

    def _set_section_subtotal_values(self, amount, label):
        self.ensure_one()
        currency = self.currency_id or self.estimation_id.currency_id
        amount_display = format_amount(self.env, amount or 0.0, currency) if currency else f"{(amount or 0.0):.2f}"

        self.section_subtotal_amount = amount
        self.section_subtotal_display = (
            f"<span class='o_section_subtotal_chip_label'>{html_escape(label)}</span>"
            f"<span class='o_section_subtotal_chip_value'>{html_escape(amount_display)}</span>"
        )