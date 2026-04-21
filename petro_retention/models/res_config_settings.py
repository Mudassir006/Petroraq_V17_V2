from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    retention_product_id = fields.Many2one(
        "product.product",
        string="Retention Product",
        config_parameter="petro_retention.retention_product_id",
        help="Product used to create the negative retention deduction line on invoices.",
    )
