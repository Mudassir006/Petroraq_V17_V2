from odoo import fields, models


class Applicant(models.Model):
    _inherit = 'hr.applicant'

    partner_location = fields.Char(string='Location')
    will_relocate = fields.Char(string='Will you able to relocate for this position?')
    notice_period = fields.Char(string='Notice Period')
    legally_required = fields.Char(string='Are you legally required Authorized to work in Saudi Arabia?')



