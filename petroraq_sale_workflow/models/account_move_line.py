from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    dp_source_sale_line_id = fields.Many2one(
        "sale.order.line",
        string="Down Payment Source SO Line",
        copy=False,
        index=True,
        help="Tracks the original SO down payment line when a deduction line is auto-created without sale_line_ids linkage.",
    )