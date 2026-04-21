

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """The class is to created for inherited the model Res Config Settings"""
    _inherit = 'res.config.settings'

    po_deposit_default_product_id = fields.Many2one(
        'product.product',
        'PO Deposit Product',
        domain="[('type', '=', 'service')]",
        config_parameter='pr_vendor_advance.po_deposit_default_product_id',
        help='Default product used for payment advances in purchase order')
