from odoo import api, fields, models, _


class AccountAnalyticAccount(models.Model):
    # region [Initial]
    _inherit = 'account.analytic.account'
    # endregion [Initial]


    employee_id = fields.Many2one("account.analytic.account", string="Employee", domain="[('analytic_plan_type', '=', 'employee')]")