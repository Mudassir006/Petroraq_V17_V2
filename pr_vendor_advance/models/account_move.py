
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    prepayment_bill = fields.Boolean(
        help="This Flag is set to True while creating a Down Payment on a Purchase Order.",
    )
