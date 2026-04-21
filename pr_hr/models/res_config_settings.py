# -*- coding: utf-8 -*-

import threading
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    # region [Initial]
    _inherit = 'res.config.settings'
    # endregion

    # region [Fields]

    lc_employee_percentage = fields.Float(string='LC',
                                          related='company_id.lc_employee_percentage',
                                          readonly=False,
                                          help='Saudi Employee LC Percentage')

    # Compatibility field: some inherited settings views reference `favicon`.
    # Keep it on res.config.settings to avoid view validation crashes when
    # modules adding company-level favicon support are not loaded.
    favicon = fields.Binary(string='Favicon')

    # endregion
