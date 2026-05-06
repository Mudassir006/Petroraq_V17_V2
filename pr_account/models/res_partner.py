# -*- coding: utf-8 -*-

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    pr_ledger_account_id = fields.Many2one(
        "account.account",
        string="Customer/Vendor Ledger Account",
        domain="[('deprecated', '=', False)]",
        help=(
            "Map this customer/vendor to the legacy account used by the custom "
            "Account Ledger report. When that account is selected, posted "
            "invoice, bill, payment, and journal lines for this partner are "
            "included in the ledger as well."
        ),
    )
