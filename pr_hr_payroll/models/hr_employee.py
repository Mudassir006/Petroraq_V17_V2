from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    exclude_transportation_from_attendance_gross = fields.Boolean(
        string="Exclude Transportation in Attendance Gross",
        help="If enabled, transportation allowance is excluded from attendance gross calculations.",
    )