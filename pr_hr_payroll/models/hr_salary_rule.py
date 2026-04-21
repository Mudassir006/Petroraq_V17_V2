
from odoo import fields, models


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    account_id = fields.Many2one('account.account', string='Account Code', required=True,
                                 ondelete='restrict', tracking=True, index=True)
    account_name = fields.Char(string='Account Name', related="account_id.name", store=True,
                               tracking=True)

    attendance_based_eligibility = fields.Boolean(
        string='Apply Attendance Eligibility',
        help='When enabled, this rule amount is prorated by eligible attendance days in the payslip period.'
    )
    attendance_min_worked_hours = fields.Float(
        string='Min Worked Hours',
        default=0.0,
        help='Minimum worked hours per day required to be eligible for this rule amount.'
    )
    attendance_require_presence = fields.Boolean(
        string='Require Presence',
        default=True,
        help='If enabled, absent days are never eligible for this rule amount.'
    )