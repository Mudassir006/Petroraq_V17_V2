from odoo import models, fields, api, _
from odoo.exceptions import AccessError
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class PurchaseQuotation(models.Model):
    _name = "purchase.quotation"
    _description = "Purchase Quotation"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    # Basic Info
    vendor_id = fields.Many2one("res.partner", string="Vendor")
    rfq_origin = fields.Char(string="RFQ Origin")
    custom_rfq_id = fields.Many2one("purchase.order", string="RFQ", ondelete="set null")
    requisition_id = fields.Many2one("purchase.requisition", string="Purchase Requisition",
                                     related="custom_rfq_id.requisition_id", store=True, readonly=True)
    vendor_ref = fields.Char(string="Vendor Reference")
    pr_name = fields.Char(string="PR Name", readonly=True)
    notes = fields.Text(string="Notes")
    order_deadline = fields.Datetime(string="Deadline")
    expected_arrival = fields.Datetime(string="Quotation Date")
    project_id = fields.Many2one("project.project", string="Project")

    # Supplier Info
    supplier_name = fields.Char(string="Supplier Name")
    contact_person = fields.Char(string="Contact Person")
    company_address = fields.Char(string="Company Address")
    phone_number = fields.Char(string="Phone Number")
    email_address = fields.Char(string="Email Address")
    supplier_id = fields.Char(string="Supplier ID")
    quotation_ref = fields.Char(string="Quotation Reference")
    # Reason tab field for end user/supervisor workflow
    rejection_reason = fields.Text(string="Reason for Rejection")

    # Payment Terms
    terms_net = fields.Boolean("Net")
    terms_30days = fields.Boolean("30 Days")
    terms_advance = fields.Boolean("Advance %")
    terms_advance_specify = fields.Char("Specify Advance Terms")
    terms_delivery = fields.Boolean("On Delivery")
    terms_other = fields.Boolean("Other")
    terms_others_specify = fields.Char("Specify Other Terms")

    # Production / Material Availability
    ex_stock = fields.Boolean("Ex-Stock")
    required_days = fields.Boolean("Production Required")
    production_days = fields.Char("Production Days Needed")

    # Delivery Terms
    ex_work = fields.Boolean("Ex-Works")
    delivery_site = fields.Boolean("Site Delivery")

    # Delivery Date Expected
    delivery_date = fields.Date("Expected Delivery Date")

    # Delivery Method
    delivery_courier = fields.Boolean("Courier")
    delivery_pickup = fields.Boolean("Pickup")
    delivery_freight = fields.Boolean("Freight")
    delivery_others = fields.Boolean("Other")
    delivery_others_specify = fields.Char("Specify Other Delivery")

    # Partial Order Acceptance
    partial_yes = fields.Boolean("Partial Order Acceptable")
    partial_no = fields.Boolean("Partial Order Not Acceptable")

    # total
    total_excl_vat = fields.Float(
        string="Total Amount", compute="_compute_totals", store=True
    )
    vat_amount = fields.Float(
        string="VAT Amount @ 15%", compute="_compute_totals", store=True
    )
    total_incl_vat = fields.Float(
        string="Total Amount Including VAT", compute="_compute_totals", store=True
    )
    is_best = fields.Boolean(
        string="Best Quotation", compute="_compute_is_best", store=True
    )
    is_best_badge = fields.Char(
        string="Best Quotation", compute="_compute_is_best_badge", store=False
    )

    # budget
    budget_type = fields.Selection(
        [("opex", "Opex"), ("capex", "Capex")],
        string="Budget Type",
    )
    budget_code = fields.Char(string="Budget Code")
    cost_center_id = fields.Many2one("account.analytic.account", string="Cost Center", compute="_compute_cost_center",
                                     store=False)
    project_budget_allowance = fields.Float(
        string="Budget Allowance",
        compute="_compute_cost_center",
        store=False,
    )
    budget_left = fields.Float(
        string="Budget Left", compute="_compute_cost_center", store=False
    )
    status = fields.Selection(
        [("quote", "Quote"), ("po", "Purchase")],
        default="quote",
        string="Status",
    )

    linked_rfq_state = fields.Selection([
        ("missing", "Not Created"),
        ("draft", "Draft"),
        ("sent", "RFQ Sent"),
        ("pending", "Pending Approval"),
        ("purchase", "Purchase Order"),
        ("done", "Locked"),
        ("cancel", "Cancelled"),
    ], string="RFQ Status", compute="_compute_linked_statuses")
    linked_pr_state = fields.Selection([
        ("missing", "Not Created"),
        ("draft", "Draft"),
        ("rfq_sent", "RFQ Sent"),
        ("pending", "Pending"),
        ("purchase", "Purchase Order"),
        ("cancel", "Cancelled"),
    ], string="PR Status", compute="_compute_linked_statuses")
    linked_po_state = fields.Selection([
        ("missing", "Not Created"),
        ("draft", "RFQ"),
        ("sent", "RFQ Sent"),
        ("pending", "Pending"),
        ("purchase", "Purchase Order"),
        ("done", "Locked"),
        ("cancel", "Cancelled"),
    ], string="PO Status", compute="_compute_linked_statuses")

    show_create_po_button = fields.Boolean(
        compute="_compute_button_visibility", store=False
    )
    # PR Info
    requested_by = fields.Char(string="Requested By")
    department = fields.Char(string="Department")
    supervisor = fields.Char(string="Supervisor")
    supervisor_partner_id = fields.Char(string="supervisor_partner_id")

    # Lines
    line_ids = fields.One2many(
        "purchase.quotation.line", "quotation_id", string="Quotation Lines"
    )

    def _compute_linked_statuses(self):
        po_priority = {"draft": 1, "sent": 2, "pending": 3, "purchase": 4, "done": 5, "cancel": 6}
        for rec in self:
            rec.linked_rfq_state = rec.custom_rfq_id.state if rec.custom_rfq_id else "missing"
            pr = self.env["custom.pr"].sudo().search([("name", "=", rec.pr_name)], limit=1) if rec.pr_name else False
            rec.linked_pr_state = pr.state if pr else "missing"

            domain = [("pr_name", "=", rec.pr_name)] if rec.pr_name else []
            if rec.vendor_id:
                domain.append(("partner_id", "=", rec.vendor_id.id))
            linked_pos = self.env["purchase.order"].sudo().search(domain) if domain else self.env["purchase.order"]
            rec.linked_po_state = max(linked_pos, key=lambda po: po_priority.get(po.state, 0)).state if linked_pos else "missing"

    @api.depends("budget_type", "budget_code")
    def _compute_cost_center(self):
        CostCenter = self.env["account.analytic.account"].sudo()
        for rec in self:
            cc = CostCenter.search([
                ("budget_type", "=", rec.budget_type),
                ("budget_code", "=", rec.budget_code),
            ], limit=1) if rec.budget_type and rec.budget_code else False
            rec.cost_center_id = cc.id if cc else False
            rec.project_budget_allowance = cc.budget_allowance if cc else 0.0
            rec.budget_left = cc.budget_left if cc else 0.0

    @api.depends("line_ids.price_unit", "line_ids.quantity")
    def _compute_totals(self):
        for record in self:
            total_excl = sum(
                line.price_unit * line.quantity for line in record.line_ids
            )
            record.total_excl_vat = total_excl
            record.vat_amount = total_excl * 0.15
            record.total_incl_vat = total_excl + record.vat_amount

    @api.depends("custom_rfq_id", "rfq_origin", "pr_name", "total_excl_vat", "status")
    def _compute_is_best(self):
        """Mark only one best quotation per PR (fallback RFQ) using the lowest total."""
        group_keys = {(rec.pr_name, rec.rfq_origin) for rec in self if rec.pr_name or rec.rfq_origin}
        if not group_keys:
            for rec in self:
                rec.is_best = False
            return

        domain = [
            "|",
            ("pr_name", "in", [pr for pr, _rfq in group_keys if pr]),
            ("rfq_origin", "in", [rfq for _pr, rfq in group_keys if rfq]),
        ]
        all_quotations = self.env["purchase.quotation"].search(domain)

        grouped = {}
        for rec in all_quotations:
            group_key = rec.pr_name or rec.rfq_origin
            grouped.setdefault(group_key, self.env["purchase.quotation"])
            grouped[group_key] |= rec

        for group in grouped.values():
            valid_records = group.filtered(lambda r: r.total_excl_vat > 0 and r.status == "quote")
            group.is_best = False
            if valid_records:
                best_rec = min(valid_records, key=lambda r: (r.total_excl_vat, r.id))
                best_rec.is_best = True

    @api.depends("is_best")
    def _compute_is_best_badge(self):
        for rec in self:
            rec.is_best_badge = "Best" if rec.is_best else ""

    @api.depends("status")
    def _compute_button_visibility(self):
        """Button visible only if status is 'quote'
        AND no PO exists in pending/purchase state."""
        for rec in self:
            show_button = False
            if rec.status == "quote":
                origin_name = rec.custom_rfq_id.name or rec.rfq_origin
                po_exists = self.env["purchase.order"].search_count(
                    [("origin", "=", origin_name), ("state", "in", ["pending", "purchase"])])
                show_button = po_exists == 0
            rec.show_create_po_button = show_button

    # create purchase order
    def action_create_purchase_order(self):
        raise UserError(_("Purchase Orders are now created from RFQ comparison. Please use the RFQ Compare action."))

    @api.model
    def create(self, vals):
        record = super(PurchaseQuotation, self).create(vals)

        # Always target procurement_admin group
        procurement_admin_group = self.env.ref(
            "pr_custom_purchase.procurement_admin", raise_if_not_found=False
        )

        if procurement_admin_group:
            for user in procurement_admin_group.users:
                record.activity_schedule(
                    "mail.mail_activity_data_todo",
                    summary="New Purchase Quotation Created",
                    note=f"A new purchase quotation (ID: {record.id}) has been created "
                         f"with a total amount of {record.total_incl_vat:.2f}.",
                    user_id=user.id,
                )

        return record


class PurchaseQuotationLine(models.Model):
    _name = "purchase.quotation.line"
    _description = "Purchase Quotation Line"

    quotation_id = fields.Many2one(
        "purchase.quotation", string="Quotation", ondelete="cascade"
    )
    name = fields.Char(string="Description")
    quantity = fields.Float(string="Quantity")
    unit = fields.Char(string="Unit")
    type = fields.Selection(
        [
            ('material', 'Material'),
            ('service', 'Service')
        ],
        string="Type",
        default='material',
        required=True
    )
    price_unit = fields.Float(string="Unit Cost")
    cost_center_id = fields.Many2one("account.analytic.account", string="Cost Center", required=True)
    subtotal = fields.Float(string="Subtotal", compute="_compute_subtotal", store=True)
    tax_15 = fields.Float(string="15% Tax", compute="_compute_subtotal", store=True)
    grand_total = fields.Float(
        string="Grand Total", compute="_compute_subtotal", store=True
    )
    description = fields.Char(string="Description")

    @api.depends("quantity", "price_unit")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price_unit
            line.tax_15 = line.subtotal * 0.15
            line.grand_total = line.subtotal + line.tax_15
