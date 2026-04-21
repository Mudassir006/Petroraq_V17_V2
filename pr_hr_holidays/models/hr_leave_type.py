from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import random


class HolidaysType(models.Model):
    # region [Initial]
    _inherit = "hr.leave.type"
    # endregion [Initial]

    # region [Fields]

    is_paid = fields.Boolean(string="Is Paid ?")
    leave_type = fields.Selection([
        ("annual_leave", "Annual Leave"),
        ("sick_leave", "Sick Leave"),
        ("business_leave", "Business Trip"),
    ], string="Type", required=True)

    # endregion [Fields]
