from odoo import models, fields, api, _
from odoo.tools import date_utils
from odoo.osv import expression
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError
import re
import json
import math
from random import randint
import logging
from datetime import datetime, timedelta
import pandas as pd


_logger = logging.getLogger(__name__)


class HrAttendanceNotification(models.Model):
    """
    """
    # region [Initial]
    _name = 'pr.hr.attendance.notification'
    _description = 'Hr Attendance Notification'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "id"
    # endregion [Initial]

    # region [Fields]

    name = fields.Char(string="Name")
    date = fields.Date(string="Date", required=True, default=fields.Date.today)
    company_id = fields.Many2one('res.company', string='Company', tracking=True, default=lambda self: self.env.company, required=True)
    att_sheet_ids = fields.One2many(comodel_name='attendance.sheet',
                                    string='Attendance Sheets',
                                    inverse_name='att_notification_id')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('gen', 'Notifications Generated'),
        ('sub', 'Notifications Submitted'),
        ('done', 'Sent')], default='draft', track_visibility='onchange',
        string='Status', required=True, readonly=True, index=True, )
    att_sheet_ids_count = fields.Integer(compute="_compute_att_sheet_ids_count")
    # endregion [Fields]

    @api.depends("att_sheet_ids")
    def _compute_att_sheet_ids_count(self):
        for notification in self:
            notification.att_sheet_ids_count = len(notification.att_sheet_ids)

    def open_related_attendance_sheets(self):
        self.ensure_one()
        form_id = self.env.ref('gs_hr_attendance_sheet.attendance_sheet_form_view').id
        list_id = self.env.ref('gs_hr_attendance_sheet.attendance_sheet_tree_view').id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Attendance Sheets'),
            'res_model': 'attendance.sheet',
            'view_type': 'list',
            'view_mode': 'list',
            'views': [[list_id, 'list'], [form_id, 'form']],
            'domain': [('id', 'in', self.att_sheet_ids.ids)],
            'target': 'current'
        }


    @api.onchange("date")
    def _onchange_date(self):
        self.ensure_one()
        if self.date:
            self.name = f"Attendance Notifications For {self.date}"

    def action_att_gen(self):
        return self.write({'state': 'gen'})

    def gen_att_sheet(self):
        att_sheets = self.env['attendance.sheet']
        att_sheet_obj = self.env['attendance.sheet']
        for notification in self:
            date = notification.date
            employee_ids = self.env['hr.employee'].search(
                [
                    ('company_id', '=', notification.company_id.id),
                    ("active", "=", True),
                    ("compute_attendance", "=", True),
                    ("attendance_email_enabled", "=", True),
                ]
            )

            if not employee_ids:
                raise UserError(_("There is no  Employees In This Company"))
            for employee in employee_ids:
                # Add Custom Condition
                if not employee.contract_id or (employee.contract_id.state != "open"):
                    raise UserError(_(
                        "There is no  Running contracts for :%s " % employee.name))
                else:

                    new_sheet = att_sheet_obj.new({
                        'employee_id': employee.id,
                        'date_from': date,
                        'date_to': date,
                        'att_notification_id': notification.id
                    })
                    new_sheet.onchange_employee()
                    values = att_sheet_obj._convert_to_write(new_sheet._cache)
                    att_sheet_id = att_sheet_obj.create(values)

                    att_sheet_id.get_attendances()
                    att_sheets += att_sheet_id
            notification.action_att_gen()

    def submit_att_sheet(self):
        for notification in self:
            if notification.state != "gen":
                continue
            for sheet in notification.att_sheet_ids:
                if sheet.state == 'draft':
                    sheet.action_confirm()

            notification.write({'state': 'sub'})

    def action_done(self):
        for notification in self:
            if notification.state != "sub":
                continue
            for sheet in notification.att_sheet_ids:
                if sheet.state == 'confirm':
                    sheet._send_notification()
            notification.write({'state': 'done'})

    @api.model
    def _get_employee_expected_hours_for_date(self, employee, target_date):
        """Return planned working hours for the employee on the provided date."""
        calendar = employee.resource_calendar_id or employee.contract_id.resource_calendar_id
        if not calendar:
            return 0.0

        weekday = str(target_date.weekday())
        has_date_from = 'date_from' in calendar.attendance_ids._fields
        has_date_to = 'date_to' in calendar.attendance_ids._fields
        attendance_lines = calendar.attendance_ids.filtered(
            lambda a: a.dayofweek == weekday
            and (not has_date_from or not a.date_from or a.date_from <= target_date)
            and (not has_date_to or not a.date_to or a.date_to >= target_date)
        )
        return sum((line.hour_to - line.hour_from) for line in attendance_lines)

    @api.model
    def _send_daily_attendance_email(self, employee, target_date, expected_hours, worked_hours):
        """Send a daily attendance email for shortage/absence based on hr.attendance."""
        if not employee.attendance_email_enabled:
            return

        if not employee.work_email:
            _logger.warning("Skipping attendance email for %s because work email is not configured.", employee.name)
            return

        shortage_hours = max(expected_hours - worked_hours, 0.0)
        is_absent = worked_hours <= 0.0 and expected_hours > 0.0
        if shortage_hours <= 0.0 and not is_absent:
            return

        whole_hours = int(shortage_hours)
        remaining_minutes = int(round((shortage_hours - whole_hours) * 60))
        issue_parts = []
        if is_absent:
            issue_parts.append("absence")
        if shortage_hours > 0:
            issue_parts.append(
                f"shortage of <strong>{whole_hours} hour(s)</strong> and "
                f"<strong>{remaining_minutes} minute(s)</strong>"
            )
        issues_html = " and ".join(issue_parts)

        body_message = f"""
            Dear Mr/Mrs. {employee.name},<br/><br/>
            We wish to inform you that a discrepancy in your attendance has been identified for
            <strong>{target_date}</strong>. Your record reflects {issues_html}.<br/><br/>
            Thank you for your attention to this matter.<br/><br/>
            Best regards,<br/>
            <strong>HR Department</strong><br/>
            Petroraq Engineering
        """
        message = {
            "email_from": "hr@petroraq.com",
            "subject": f"{employee.code} - Attendance Notification Of {target_date}",
            "body_html": body_message,
            "email_to": employee.work_email,
        }
        mail_id = self.env["mail.mail"].sudo().create(message)
        if mail_id:
            mail_id.sudo().send()

    @api.model
    def cron_send_daily_attendance_notifications(self):
        """Send same-day attendance alerts directly from hr.attendance records."""
        today = fields.Date.context_today(self)
        companies = self.env['res.company'].search([])
        attendance_obj = self.env['hr.attendance']
        for company in companies:
            notification = self.search(
                [('date', '=', today), ('company_id', '=', company.id)],
                order='id desc',
                limit=1,
            )
            if not notification:
                notification = self.create({
                    'name': f"Attendance Notifications For {today}",
                    'date': today,
                    'company_id': company.id,
                })

            employees = self.env['hr.employee'].search([
                ('company_id', '=', company.id),
                ('active', '=', True),
                ('compute_attendance', '=', True),
                ('attendance_email_enabled', '=', True),
            ])
            start_dt = datetime.combine(today, datetime.min.time())
            end_dt = start_dt + timedelta(days=1)

            for employee in employees:
                expected_hours = self._get_employee_expected_hours_for_date(employee, today)
                if expected_hours <= 0:
                    continue
                attendances = attendance_obj.search([
                    ('employee_id', '=', employee.id),
                    ('check_in', '>=', fields.Datetime.to_string(start_dt)),
                    ('check_in', '<', fields.Datetime.to_string(end_dt)),
                ])
                worked_hours = sum(attendances.mapped('worked_hours')) if attendances else 0.0
                self._send_daily_attendance_email(
                    employee=employee,
                    target_date=today,
                    expected_hours=expected_hours,
                    worked_hours=worked_hours,
                )

            if notification.state == 'draft':
                notification.write({'state': 'gen'})
            notification.write({'state': 'done'})