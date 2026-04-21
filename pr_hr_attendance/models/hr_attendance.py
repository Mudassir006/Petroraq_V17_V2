from odoo import api, fields, models


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    attachment_ids = fields.Many2many(
        "ir.attachment",
        "hr_attendance_attachment_rel",
        "attendance_id",
        "attachment_id",
        string="Attachments",
        help="Optional supporting attachments for this attendance/overtime entry.",
    )

    @api.depends("worked_hours", "check_in", "check_out", "employee_id")
    def _compute_overtime_for_approval(self):
        """
        Compute overtime eligibility directly from worked hours and the
        employee's configured calendar hours per day.
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
            worked_hours = rec.worked_hours or 0.0
            rec.overtime_for_approval = max(worked_hours - hours_per_day, 0.0)