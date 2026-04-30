from odoo import fields, models


class Applicant(models.Model):
    _inherit = 'hr.applicant'

    partner_location = fields.Char(string='Location')
    will_relocate = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='Willing to Relocate')
    notice_period = fields.Char(string='Notice Period')
    legally_required = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='Authorized to Work in Saudi Arabia')


