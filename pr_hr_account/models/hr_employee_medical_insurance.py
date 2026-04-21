from odoo import api, fields, models, _


class HREmployeeMedicalInsuranceLine(models.Model):
    # region [Initial]
    _inherit = 'hr.employee.medical.insurance.line'
    # endregion [Initial]

    bank_payment_id = fields.Many2one('pr.account.bank.payment', readonle=True)
    paid_move_id = fields.Many2one('account.move', related="bank_payment_id.journal_entry_id", store=True)

