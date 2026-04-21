from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    received_bank_account_id = fields.Many2one(
        "res.partner.bank",
        string="Received In Bank Account",
        domain="[('company_id', '=', company_id)]",
        help="Company bank account where the payment was received.",
    )

    @api.onchange("journal_id")
    def _onchange_journal_id_default_received_bank(self):
        for wiz in self:
            if wiz.journal_id and wiz.journal_id.type == "bank":
                wiz.received_bank_account_id = wiz.journal_id.bank_account_id
            else:
                wiz.received_bank_account_id = False

    # def _create_payment_vals_from_wizard(self, batch_result, **kwargs):
    #     vals = super()._create_payment_vals_from_wizard(batch_result, **kwargs)
    #
    #     # only set when bank journal (optional rule)
    #     if self.journal_id.type == "bank":
    #         vals["received_bank_account_id"] = self.received_bank_account_id.id or False
    #     else:
    #         vals["received_bank_account_id"] = False
    #
    #     return vals

    # def action_create_payments(self):
    #     for wiz in self:
    #         if wiz.journal_id.type == "bank" and not wiz.received_bank_account_id:
    #             raise ValidationError(_("Please select the bank account where payment was received."))
    #     return super().action_create_payments()
