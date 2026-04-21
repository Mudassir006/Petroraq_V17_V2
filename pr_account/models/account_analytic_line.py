from odoo import api, fields, models, _


class AccountAnalyticLine(models.Model):
    # region [Initial]
    _inherit = 'account.analytic.line'
    # endregion [Initial]

    # region [Fields]

    debit_payment_receipt_id = fields.Many2one('pr.payment.receipt', string='Debit Payment Receipt')
    credit_payment_receipt_id = fields.Many2one('pr.payment.receipt', string='Credit Payment Receipt')
    debit_transaction_payment_id = fields.Many2one('pr.transaction.payment', string='Debit Transaction Payment')
    credit_transaction_payment_id = fields.Many2one('pr.transaction.payment', string='Credit Transaction Payment')
    cash_receipt_id = fields.Many2one('pr.account.cash.receipt', string='Cash Receipt')
    cash_receipt_line_id = fields.Many2one('pr.account.cash.receipt.line', string='Cash Receipt Line')
    cash_payment_id = fields.Many2one('pr.account.cash.payment', string='Cash Payment')
    cash_payment_line_id = fields.Many2one('pr.account.cash.payment.line', string='Cash Payment Line')
    bank_receipt_id = fields.Many2one('pr.account.bank.receipt', string='Bank Receipt')
    bank_receipt_line_id = fields.Many2one('pr.account.bank.receipt.line', string='Bank Receipt Line')
    bank_payment_id = fields.Many2one('pr.account.bank.payment', string='Bank Payment')
    bank_payment_line_id = fields.Many2one('pr.account.bank.payment.line', string='Bank Payment Line')

    # endregion [Fields]

