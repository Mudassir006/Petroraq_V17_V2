from odoo import models, fields, api

class CustomPRQuotation(models.Model):
    _name = 'custom.pr.quotation'
    _description = 'Purchase Requisition Quotation'

    # Basic Info
    vendor_id = fields.Many2one("res.partner", string="Vendor")
    rfq_origin = fields.Char(string="RFQ Origin")
    vendor_ref = fields.Char(string="Vendor Reference")
    notes = fields.Text(string="Notes")
    order_deadline = fields.Datetime(string="Deadline")
    expected_arrival = fields.Datetime(string="Quotation Date")

    # Supplier Info
    supplier_name = fields.Char(string="Supplier Name")
    contact_person = fields.Char(string="Contact Person")
    company_address = fields.Char(string="Company Address")
    phone_number = fields.Char(string="Phone Number")
    email_address = fields.Char(string="Email Address")
    supplier_id = fields.Char(string="Supplier ID")
    quotation_ref = fields.Char(string="Quotation Reference")

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

    line_ids = fields.One2many('custom.pr.quotation.line', 'quotation_id', string="Quotation Lines")


class CustomPRQuotationLine(models.Model):
    _name = 'custom.pr.quotation.line'
    _description = 'Purchase Requisition Quotation Line'

    quotation_id = fields.Many2one('custom.pr.quotation', string="Quotation", ondelete="cascade")
    description = fields.Char(string="Description")
    quantity = fields.Float(string="Quantity", default=1.0)
    unit = fields.Selection(
        [
            ('Kilogram', 'Kilogram'),
            ('Gram', 'Gram'),
            ('Litre', 'Litre'),
            ('Millilitre', 'Millilitre'),
            ('Meter', 'Metre'),
            ('Each', 'Each'),
        ],
        string="Unit",
        required=True,
    )
    unit_price = fields.Float(string="Unit Price")
    price_subtotal = fields.Float(string="Subtotal", compute="_compute_subtotal", store=True)

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        for rec in self:
            rec.price_subtotal = rec.quantity * rec.unit_price
