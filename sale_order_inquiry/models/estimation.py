from odoo import fields, models


class PetroraqEstimation(models.Model):
    _inherit = "petroraq.estimation"

    order_inquiry_id = fields.Many2one("order.inq", string="Inquiry", readonly=True)

    def action_create_sale_order(self):
        res = super().action_create_sale_order()
        for estimation in self:
            if estimation.order_inquiry_id:
                estimation.order_inquiry_id.state = "quotation_created"
        return res