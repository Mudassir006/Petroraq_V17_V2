from odoo import api, fields, models, _


class AccountMoveLine(models.Model):
    # region [Initial]
    _inherit = 'account.move.line'
    # endregion [Initial]

    # region [Fields]

    asset_id = fields.Many2one("account.analytic.account", string="Asset",
                               domain="[('analytic_plan_type', '=', 'asset')]", tracking=True)

    # endregion [Fields]