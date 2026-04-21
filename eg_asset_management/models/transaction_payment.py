from odoo import api, fields, models, _


class TransactionPayment(models.Model):
    # region [Initial]
    _inherit = 'pr.transaction.payment'
    # endregion [Initial]

    # region [Fields]

    debit_asset_id = fields.Many2one('asset.detail', string='Debit Asset', tracking=True)
    credit_asset_id = fields.Many2one('asset.detail', string='Credit Asset', tracking=True)

    # endregion [Fields]

    def _prepare_debit_move_line_vals(self):
        line_vals = super()._prepare_debit_move_line_vals()
        if self.debit_asset_id:
            line_vals.update({"asset_id": self.debit_asset_id.id})
        return line_vals

    def _prepare_debit_tax_move_line_vals(self):
        line_vals = super()._prepare_debit_tax_move_line_vals()
        if self.debit_asset_id:
            line_vals.update({"asset_id": self.debit_asset_id.id})
        return line_vals

    def _prepare_credit_move_line_vals(self):
        line_vals = super()._prepare_credit_move_line_vals()
        if self.credit_asset_id:
            line_vals.update({"asset_id": self.credit_asset_id.id})
        return line_vals