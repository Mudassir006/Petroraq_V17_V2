from odoo import api, fields, models, _


class ResPartnerBank(models.Model):
    # region [Initial]
    _inherit = 'res.partner.bank'
    # endregion [Initial]

    # region [Fields]
    employee_id = fields.Many2one('hr.employee', string='Employee')
    # endregion [Fields]

    @api.model
    def _get_supported_account_types(self):
        """ Add new account type 'Employee' """
        res = super()._get_supported_account_types()
        res.append(('employee', _('Employee')))
        return res