from odoo import api, fields, models, _


class ResCountry(models.Model):
    # region [Initial]
    _inherit = 'res.country'
    # endregion [Initial]

    # region [Fields]

    is_homeland = fields.Boolean(default=False, string='Homeland',
                                 help='Homeland Is for the saudi nationality employees')
    # endregion [Fields]
