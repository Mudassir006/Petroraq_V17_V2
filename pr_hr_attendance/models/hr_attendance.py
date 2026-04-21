from odoo import api, models


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    @api.depends("worked_hours", "check_in", "check_out", "employee_id")
    def _compute_overtime_for_approval(self):
        """
        Keep overtime approval aligned with payroll overtime logic by deducting
        one break hour from worked hours before comparing against expected
        calendar hours per day.
        """
        for rec in self:
            if not rec.employee_id or not rec.check_out:
                rec.overtime_for_approval = 0.0
                continue

            allows_overtime = (
                ("allow_overtime" in rec.employee_id._fields and rec.employee_id.allow_overtime)
                or ("add_overtime" in rec.employee_id._fields and rec.employee_id.add_overtime)
            )
            if not allows_overtime:
                rec.overtime_for_approval = 0.0
                continue

            hours_per_day = rec.employee_id.resource_calendar_id.hours_per_day or 8.0
            net_worked_hours = max((rec.worked_hours or 0.0) - 1.0, 0.0)
            rec.overtime_for_approval = max(net_worked_hours - hours_per_day, 0.0)