from odoo import models, fields

class AccountPayment(models.Model):
    _inherit = "account.payment"

    received_bank_account_id = fields.Many2one(
        "res.partner.bank",
        string="Received In Bank Account",
        help="Company bank account where this payment was received.",
        index=True,
        copy=False,
    )
