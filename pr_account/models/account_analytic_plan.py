from odoo import api, fields, models, _


class AccountAnalyticAccount(models.Model):
    # region [Initial]
    _inherit = 'account.analytic.plan'
    # endregion [Initial]


    analytic_plan_type = fields.Selection([
        ("department", "Department"),
        ("section", "Section"),
        ("project", "Project"),
        ("employee", "Employee"),
        ("asset", "Asset"),
    ], string="Plan Type", required=True)
