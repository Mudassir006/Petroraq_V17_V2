from odoo import api, fields, models, _


class ResGroups(models.Model):
    """

    """
    # region [Initial]
    _inherit = 'res.groups'
    # endregion [Initial]

    # region [Fields]

    # endregion

    @api.constrains("users")
    def _check_users_to_check_approvals(self):
        for group in self:
            return True
