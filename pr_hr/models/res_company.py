# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Company(models.Model):
    # region [Initial]
    _inherit = 'res.company'
    # endregion

    # region [Fields]

    lc_employee_percentage = fields.Float(string='LC', help='Saudi Employee LC Percentage')

    # endregion
