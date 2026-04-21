from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class CustomPurchaseRFQ(models.Model):
    _name = "custom.purchase.rfq"
    _description = "Custom RFQ"
    _inherit = "purchase.order"
    _order = "id desc"

    # In classical inheritance, explicit Many2many relation names from purchase.order
    # must be redefined to avoid table/column collisions on the child model.
    approval_action_user_ids = fields.Many2many(
        "res.users",
        "custom_purchase_rfq_approval_action_user_rel",
        "rfq_id",
        "user_id",
        string="Users Who Acted",
        copy=False,
    )

    requisition_id = fields.Many2one("purchase.requisition", string="Source PR", readonly=True, ondelete="set null")
    pr_name = fields.Char(string="PR Number", readonly=True)
    date_request = fields.Date(string="Date of Request")
    requested_by = fields.Char(string="Requested By")
    department = fields.Char(string="Department")
    supervisor = fields.Char(string="Supervisor")
    supervisor_partner_id = fields.Char(string="Supervisor Partner")
    related_rfq_ids = fields.One2many(
        "purchase.order",
        compute="_compute_related_rfqs",
        string="Related RFQs",
    )
    quotation_count = fields.Integer(compute="_compute_quotation_count")
    line_ids = fields.One2many("custom.purchase.rfq.line", "rfq_id", string="RFQ Lines")

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
    linked_quotation_status = fields.Selection([
        ("missing", "Not Submitted"),
        ("quote", "RFQ"),
        ("po", "Purchase Order"),
    ], string="RFQ / PO Status", compute="_compute_linked_statuses")

    def _compute_linked_statuses(self):
        po_priority = {"draft": 1, "sent": 2, "pending": 3, "purchase": 4, "done": 5, "cancel": 6}
        rfq_priority = {"draft": 1, "sent": 2, "pending": 3, "purchase": 4, "done": 5, "cancel": 6}

        for rec in self:
            pr = self.env["custom.pr"].sudo().search([("name", "=", rec.pr_name)], limit=1) if rec.pr_name else False
            rec.linked_pr_state = pr.state if pr else "missing"

            linked_pos = self.env["purchase.order"].sudo().search([("origin", "=", rec.name)]) if rec.name else self.env["purchase.order"]
            if linked_pos:
                rec.linked_po_state = max(linked_pos, key=lambda po: po_priority.get(po.state, 0)).state
            else:
                rec.linked_po_state = "missing"

            related_rfqs = rec.related_rfq_ids.filtered(lambda r: r.id != rec.id)
            if related_rfqs:
                max_state = max(related_rfqs, key=lambda r: rfq_priority.get(r.state, 0)).state
                rec.linked_quotation_status = "po" if max_state in ("pending", "purchase", "done") else "quote"
            else:
                rec.linked_quotation_status = "missing"

    @api.depends("requisition_id")
    def _compute_related_rfqs(self):
        for rec in self:
            if rec.requisition_id:
                rec.related_rfq_ids = self.env["purchase.order"].sudo().search([
                    ("requisition_id", "=", rec.requisition_id.id),
                ])
            else:
                rec.related_rfq_ids = self.env["purchase.order"]

    @api.depends("related_rfq_ids")
    def _compute_quotation_count(self):
        for rec in self:
            rec.quotation_count = len(rec.related_rfq_ids.filtered(lambda r: r.id != rec.id))

    @api.model
    def create(self, vals):
        if not vals.get("name") or vals.get("name") == "New":
            vals["name"] = self.env["ir.sequence"].sudo().next_by_code("custom.purchase.rfq") or "CRFQ0001"
        return super().create(vals)

    def action_send_rfq_email(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_("Please set a vendor before sending RFQ."))
        return self.action_rfq_send()



    def action_reset_to_draft(self):
        for rec in self:
            linked_po = self.env["purchase.order"].sudo().search_count([
                ("origin", "=", rec.name),
                ("state", "in", ["purchase", "done"]),
            ])
            if linked_po:
                raise UserError(_("Cannot reset RFQ %s because a confirmed Purchase Order already exists.") % rec.name)

            rec.write({
                "state": "draft",
                "pe_approved": False,
                "pm_approved": False,
                "od_approved": False,
                "md_approved": False,
                "rejection_reason": False,
            })
            rec.message_post(body=_("RFQ/PO reset to draft and approval flags cleared."))

    def action_open_rfq_comparison(self):
        self.ensure_one()
        comparable_rfqs = self.related_rfq_ids.filtered(lambda rfq: rfq.id != self.id and rfq.order_line)
        if not comparable_rfqs:
            label = self.requisition_id.name or self.pr_name or self.name
            raise UserError(_("No comparable RFQs are available for %s yet.") % label)
        wizard = self.env["rfq.comparison.wizard"].create_for_custom_rfq(self)
        return {
            "type": "ir.actions.act_window",
            "name": _("RFQ Comparison"),
            "res_model": "rfq.comparison.wizard",
            "view_mode": "form",
            "target": "current",
            "res_id": wizard.id,
            "context": {"form_view_initial_mode": "edit"},
        }

    def action_view_quotations(self):
        self.ensure_one()
        action = self.env.ref("purchase.purchase_rfq").read()[0]
        domain = [("id", "in", self.related_rfq_ids.filtered(lambda r: r.id != self.id).ids)]
        action["domain"] = domain
        action["context"] = {
            "group_by": "requisition_id",
        }
        return action


class CustomPurchaseRFQLine(models.Model):
    _name = "custom.purchase.rfq.line"
    _description = "Custom RFQ Line"

    rfq_id = fields.Many2one("custom.purchase.rfq", string="RFQ", required=True, ondelete="cascade")
    name = fields.Char(string="Description", required=True)
    type = fields.Selection(
        [("material", "Material"), ("service", "Service")],
        string="Type",
        default="material",
        required=True,
    )
    quantity = fields.Float(string="Quantity", default=1.0)
    unit = fields.Char(string="Unit")
    price_unit = fields.Float(string="Estimated Unit Price")
    cost_center_id = fields.Many2one("account.analytic.account", string="Cost Center", required=True)
    subtotal = fields.Float(string="Subtotal", compute="_compute_subtotal", store=True)

    @api.depends("quantity", "price_unit")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price_unit

    @api.constrains("quantity", "price_unit")
    def _check_non_negative_values(self):
        for line in self:
            if line.quantity < 0:
                raise ValidationError(_("Quantity cannot be negative."))
            if line.price_unit < 0:
                raise ValidationError(_("Unit Price cannot be negative."))