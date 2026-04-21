from odoo import models, fields, api, _
from odoo.tools import date_utils
from odoo.osv import expression
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
import re
import json
import math
from random import randint
import logging
from datetime import datetime, timedelta
import pandas as pd
import pytz

_logger = logging.getLogger(__name__)


class HrAttendanceSheet(models.Model):
    """
    """
    # region [Initial]
    _inherit = 'attendance.sheet'
    # endregion [Initial]

    # region [Fields]

    att_notification_id = fields.Many2one(comodel_name='pr.hr.attendance.notification',
                                          string='Attendance Notification')
    employee_code = fields.Char(related='employee_id.code', string='Employee ID', store=True, readonly=True)
    tot_late_in_minutes = fields.Float(compute="_compute_sheet_total",
                                       string="Total Late In Minutes",
                                       readonly=True, store=True)
    tot_early_checkout = fields.Float(compute="_compute_sheet_total",
                                      string="Total Early Check Out",
                                      readonly=True, store=True)
    no_early_checkout = fields.Integer(compute="_compute_sheet_total",
                                       string="No of Early Check Out",
                                       readonly=True, store=True)
    tot_early_checkout_amount = fields.Float(compute="_compute_sheet_total",
                                             string="Total Early Check Out Amount",
                                             readonly=True, store=True)
    early_check_out_minutes = fields.Float(compute="_compute_sheet_total",
                                           string="Total Early Checkout Minutes",
                                           readonly=True, store=True)

    # endregion [Fields]

    # region [Compute Methods]

    @api.depends('line_ids.status',
                 'line_ids.day_amount',
                 'line_ids.overtime',
                 'line_ids.worked_hours',
                 'line_ids.overtime_amount',
                 'line_ids.diff_time',
                 'line_ids.diff_amount',
                 'line_ids.late_in',
                 'line_ids.late_in_amount',
                 'line_ids.late_in_minutes',
                 'line_ids.absence_amount',
                 'line_ids.early_check_out',
                 'line_ids.early_check_out_minutes',
                 'line_ids.early_check_out_amount',
                 'employee_id',
                 'employee_id.add_overtime',
                 'employee_id.resource_calendar_id',
                 'employee_id.contract_id',
                 'employee_id.contract_id.wage')
    def _compute_sheet_total(self):
        """
        """
        res = super()._compute_sheet_total()
        for sheet in self:
            # Keep sheet overtime totals aligned with the overtime values already
            # computed per day on line level.
            overtime_lines = sheet.line_ids.filtered(lambda l: l.overtime > 0)
            approved_overtime_lines = overtime_lines.filtered(lambda l: l.overtime_approval_state == 'approved')
            if sheet.employee_id.add_overtime:
                sheet.tot_overtime = sum(approved_overtime_lines.mapped("approved_overtime_hours"))
                sheet.tot_overtime_amount = sum(approved_overtime_lines.mapped("approved_overtime_amount"))
            else:
                sheet.tot_overtime = 0.0
                sheet.tot_overtime_amount = 0.0
            sheet.no_overtime = len(approved_overtime_lines)

            # Compute Late In Minutes
            late_lines = sheet.line_ids.filtered(lambda l: l.late_in > 0)
            sheet.tot_late_in_minutes = sum(late_lines.mapped("late_in_minutes")) if late_lines else 0
            # Compute Total Early Check Out
            early_lines = sheet.line_ids.filtered(lambda l: l.early_check_out > 0)
            sheet.tot_early_checkout = sum([l.early_check_out for l in early_lines])
            sheet.tot_early_checkout_amount = sum([l.early_check_out_amount for l in early_lines])
            sheet.no_early_checkout = len(early_lines)
            sheet.early_check_out_minutes = sum(early_lines.mapped("early_check_out_minutes")) if early_lines else 0
        return res

    def get_attendances(self):
        res = super().get_attendances()
        for att_sheet in self:
            for line in att_sheet.line_ids:
                has_actual_attendance = (
                    line.ac_sign_in is not False
                    and line.ac_sign_out is not False
                    and line.ac_sign_out > line.ac_sign_in
                )
                if has_actual_attendance:
                    if line.pl_sign_in != 0:
                        if line.pl_sign_in + 1 >= line.ac_sign_in >= line.pl_sign_in - 1:
                            line.late_in = 0
                            line.late_in_minutes = 0
                            # pl_sign_out_custom = line.ac_sign_in + 9
                            pl_sign_out_custom = line.ac_sign_in + (line.pl_sign_out - line.pl_sign_in)
                            if line.ac_sign_out < pl_sign_out_custom:
                                early_check_out = pl_sign_out_custom - line.ac_sign_out
                                line.early_check_out = early_check_out
                                line.early_check_out_minutes = early_check_out * 60
                            # Compute Overtime
                            elif line.ac_sign_out > pl_sign_out_custom and line.employee_id.add_overtime:
                                line.act_overtime = line.ac_sign_out - pl_sign_out_custom
                                line.overtime = line.ac_sign_out - pl_sign_out_custom

                        # # Ramadan
                        # if line.pl_sign_in >= line.ac_sign_in:
                        #     line.late_in = 0
                        #     line.late_in_minutes = 0
                        #     if line.ac_sign_out < line.pl_sign_out:
                        #         early_check_out = line.pl_sign_out - line.ac_sign_out
                        #         line.early_check_out = early_check_out
                        #         line.early_check_out_minutes = early_check_out * 60
                        #     # Compute Overtime
                        #     elif line.ac_sign_out > line.pl_sign_out and line.employee_id.add_overtime:
                        #         line.act_overtime = line.ac_sign_out - line.pl_sign_out - 2
                        #         line.overtime = line.ac_sign_out - line.pl_sign_out - 2
                        # elif line.ac_sign_in > (line.pl_sign_in + 1):
                        elif line.ac_sign_in > line.pl_sign_in + 1:
                            line.late_in = line.ac_sign_in - (line.pl_sign_in + 1)
                            line.late_in_minutes = (line.ac_sign_in - (line.pl_sign_in + 1)) * 60

                            # Early Checkout
                            pl_sign_out_custom = line.pl_sign_out + 1
                            if line.ac_sign_out < pl_sign_out_custom:
                                early_check_out = pl_sign_out_custom - line.ac_sign_out
                                line.early_check_out = early_check_out
                                line.early_check_out_minutes = early_check_out * 60
                            # Compute Overtime
                            elif line.ac_sign_out > pl_sign_out_custom and line.employee_id.add_overtime:
                                line.act_overtime = line.ac_sign_out - pl_sign_out_custom
                                line.overtime = line.ac_sign_out - pl_sign_out_custom


                        #############
                        elif line.ac_sign_in < line.pl_sign_in - 1:
                            line.late_in = 0
                            line.late_in_minutes = 0
                            # pl_sign_out_custom = line.ac_sign_in + 9
                            pl_sign_out_custom = line.pl_sign_out - 1
                            if line.ac_sign_out < pl_sign_out_custom:
                                early_check_out = pl_sign_out_custom - line.ac_sign_out
                                line.early_check_out = early_check_out
                                line.early_check_out_minutes = early_check_out * 60
                            # Compute Overtime
                            elif line.ac_sign_out > pl_sign_out_custom and line.employee_id.add_overtime:
                                line.act_overtime = line.ac_sign_out - pl_sign_out_custom
                                line.overtime = line.ac_sign_out - pl_sign_out_custom

                    # Compute Overtime If Employee Work In Weekend Or In Public Holiday
                    if line.pl_sign_in == 0:
                        line.act_overtime = line.ac_sign_out - line.ac_sign_in if (
                                                                                          line.ac_sign_out - line.ac_sign_in) > 0 else 0
                        line.overtime = line.ac_sign_out - line.ac_sign_in if (
                                                                                      line.ac_sign_out - line.ac_sign_in) > 0 else 0

                # Check Absence Before Weekend
                # if line.status == "weekend":
                #     line_before_id = att_sheet.line_ids.filtered(lambda l: (l.date == line.date - relativedelta(days=1)) and l.status == "ab")
                #     line_after_id = att_sheet.line_ids.filtered(lambda l: (l.date == line.date + relativedelta(days=1)) and l.status == "ab")
                #     if not line_after_id:
                #         line_after_id = att_sheet.line_ids.filtered(
                #             lambda l: (l.date == line.date + relativedelta(days=2)) and l.status == "ab")
                #     if line_before_id and line_after_id:
                #         line.status = "ab"
            # Check Leave Day Although Weekend
            leave_ids = self.env["hr.leave"].search([
                ("employee_id", "=", att_sheet.employee_id.id),
                ("state", "=", "validate"),
                ("request_date_from", "<=", att_sheet.date_to),
                ("request_date_to", ">=", att_sheet.date_from),
            ])
            for leave in leave_ids:
                # Convert the string dates to pandas datetime objects
                # start_date = pd.to_datetime(leave.request_date_from, format="%d/%m/%Y")
                start_date = pd.to_datetime(leave.request_date_from, dayfirst=True)
                # end_date = pd.to_datetime(leave.request_date_to, format="%d/%m/%Y")
                end_date = pd.to_datetime(leave.request_date_to, dayfirst=True)
                dates_between = pd.date_range(start=start_date, end=end_date)

                for date in dates_between:
                    date_line = date.date()
                    # if att_sheet.employee_id.id == 116:
                    #     print(222)
                    if date_line.weekday() not in [4, 5]:
                        filtered_line = att_sheet.line_ids.filtered(lambda l: l.date == date_line)
                        if filtered_line:
                            filtered_line.status = "leave"
            att_sheet._sync_line_overtime_approval_from_attendance()
            att_sheet._mark_late_checkins_as_absent()
        return res

    def _sync_line_overtime_approval_from_attendance(self):
        for sheet in self:
            timezone_name = sheet.employee_id.tz or self.env.user.tz or "UTC"
            tz = pytz.timezone(timezone_name)
            allows_overtime = sheet._employee_allows_overtime() if hasattr(sheet, "_employee_allows_overtime") else bool(sheet.employee_id.add_overtime)
            for line in sheet.line_ids:
                if not allows_overtime or line.overtime <= 0:
                    line.overtime_approval_state = "not_required"
                    continue
                if line.date and sheet._is_overtime_approved_for_day(sheet.employee_id, line.date, tz):
                    line.overtime_approval_state = "approved"
                elif line.overtime_approval_state == "not_required":
                    line.overtime_approval_state = "pending"

    def _mark_late_checkins_as_absent(self):
        """Mark attendance sheet lines as absent when check-in is after 09:01."""
        cutoff = 9 + (1 / 60)
        for sheet in self:
            for line in sheet.line_ids:
                if line.status in ("leave", "weekend"):
                    continue
                if line.ac_sign_in and line.ac_sign_in > cutoff:
                    line.status = "ab"
                    line.late_in = 0
                    line.late_in_minutes = 0
                    line.early_check_out = 0
                    line.early_check_out_minutes = 0
                    line.overtime = 0
                    line.act_overtime = 0

    # endregion [Compute Methods]

    def _get_workday_lines(self):
        self.ensure_one()

        work_entry_obj = self.env['hr.work.entry.type']
        overtime_work_entry = work_entry_obj.search([('code', '=', 'ATTSHOT')])
        latin_work_entry = work_entry_obj.search([('code', '=', 'ATTSHLI')])
        early_work_entry = work_entry_obj.search([('code', '=', 'ATTSHECO')])
        absence_work_entry = work_entry_obj.search([('code', '=', 'ATTSHAB')])
        difftime_work_entry = work_entry_obj.search([('code', '=', 'ATTSHDT')])
        if not overtime_work_entry:
            raise ValidationError(_(
                'Please Add Work Entry Type For Attendance Sheet Overtime With Code ATTSHOT'))
        if not latin_work_entry:
            raise ValidationError(_(
                'Please Add Work Entry Type For Attendance Sheet Late In With Code ATTSHLI'))
        if not early_work_entry:
            raise ValidationError(_(
                'Please Add Work Entry Type For Attendance Sheet Early Check Out With Code ATTSHECO'))
        if not absence_work_entry:
            raise ValidationError(_(
                'Please Add Work Entry Type For Attendance Sheet Absence With Code ATTSHAB'))
        if not difftime_work_entry:
            raise ValidationError(_(
                'Please Add Work Entry Type For Attendance Sheet Diff Time With Code ATTSHDT'))

        approved_hours = self.approved_overtime_hours or 0.0
        approved_amount = self.approved_overtime_amount or 0.0
        overtime = []
        if approved_hours > 0:
            overtime = [{
                'name': "Overtime",
                'code': 'OVT',
                'work_entry_type_id': overtime_work_entry[0].id,
                'sequence': 30,
                'number_of_days': approved_hours / (self.employee_id.contract_id.resource_calendar_id.hours_per_day or 8.0),
                'number_of_hours': approved_hours,
                'amount': approved_amount,
            }]

        absence = [{
            'name': "Absence",
            'code': 'ABS',
            'work_entry_type_id': absence_work_entry[0].id,
            'sequence': 35,
            'number_of_days': self.no_absence,
            'number_of_hours': self.tot_absence,
        }]
        late = [{
            'name': "Late In",
            'code': 'LATE',
            'work_entry_type_id': latin_work_entry[0].id,
            'sequence': 40,
            'number_of_days': self.no_late,
            'number_of_hours': self.tot_late,
        }]
        early_co = [{
            'name': "Early Check Out",
            'code': 'ECO',
            'work_entry_type_id': early_work_entry[0].id,
            'sequence': 40,
            'number_of_days': self.no_early_checkout,
            'number_of_hours': self.tot_early_checkout,
        }]
        difftime = [{
            'name': "Difference time",
            'code': 'DIFFT',
            'work_entry_type_id': difftime_work_entry[0].id,
            'sequence': 45,
            'number_of_days': self.no_difftime,
            'number_of_hours': self.tot_difftime,
        }]
        worked_days_lines = overtime + late + early_co + absence + difftime
        return worked_days_lines

    def _send_notification(self):
        for sheet in self:
            employee_id = sheet.employee_id
            if not employee_id.attendance_email_enabled:
                _logger.info("Skipping attendance email for %s because attendance_email_enabled is disabled.", employee_id.name)
                sheet.write({'state': 'done'})
                continue
            employee_email = employee_id.work_email
            minutes = sheet.tot_late_in_minutes + sheet.early_check_out_minutes
            total_hours = minutes // 60
            total_minutes = minutes % 60
            no_absence = sheet.no_absence
            if not employee_email:
                _logger.warning("Skipping attendance email for %s because work email is not configured.", employee_id.name)
                sheet.write({'state': 'done'})
                continue
            if minutes > 0 or no_absence > 0:
                # mail_server = self.env["ir.mail_server"]
                mail = self.env["mail.mail"]
                try:
                    issue_messages = []
                    if minutes > 0:
                        issue_messages.append(
                            f"shortage of <strong>{int(round(total_hours, 2))} hours</strong> and "
                            f"<strong>{int(round(total_minutes, 2))} minutes</strong>"
                        )
                    if no_absence > 0:
                        issue_messages.append(f"absence of <strong>{int(round(no_absence, 2))} day(s)</strong>")

                    issues_html = " and ".join(issue_messages)
                    body_message = f"""
                        Dear Mr/Mrs. {employee_id.name},<br/><br/>

                        We wish to inform you that a discrepancy in your recorded work hours has been identified for
                        <strong>{sheet.date_from}</strong>. On this date, your attendance reflects a {issues_html}.<br/><br/>

                        Thank you for your attention to this matter.<br/><br/>
                        Best regards,<br/>
                        <strong>HR Department</strong><br/>
                        Petroraq Engineering
                    """
                    receivers_emails = [employee_email]
                    for receiver in receivers_emails:
                        message = {
                            "email_from": "hr@petroraq.com",
                            "subject": f"{employee_id.code} - Shortage Notifications Of {sheet.date_from} Attendance",
                            "body_html": body_message,
                            "email_to": receiver,
                        }

                        mail_id = mail.sudo().create(message)
                        if mail_id:
                            mail_id.sudo().send()
                except Exception as e:
                    _logger.error("Attendance email was not sent for %s: %s", employee_id.name, e)
            sheet.write({'state': 'done'})


class AttendanceSheetLine(models.Model):
    # region [Initial]
    _inherit = 'attendance.sheet.line'
    # endregion [Initial]

    # region [Fields]

    late_in_minutes = fields.Float("Late In Minutes", readonly=True)
    early_check_out_minutes = fields.Float("Early Checkout Minutes", readonly=True)
    early_check_out = fields.Float("Early Checkout", readonly=True)
    early_check_out_amount = fields.Float("Early Checkout Amount", readonly=True,
                                          compute="_compute_early_check_out_amount", store=True)

    # endregion [Fields]

    def _get_transportation_allowance_amount(self, contract):
        if not contract:
            return 0.0
        transport_rules = contract.contract_salary_rule_ids.filtered(
            lambda r: r.pay_in_payslip and (r.salary_rule_id.code or "").upper() == "TRANSPORTATION"
        )
        return sum(transport_rules.mapped("amount")) if transport_rules else 0.0

    def _get_deduction_salary_base(self, contract):
        gross_amount = contract.gross_amount if contract else 0.0
        if not self.employee_id:
            return gross_amount

        exclude_transport_from_deduction = (
            "exclude_transportation_from_attendance_gross" in self.employee_id._fields
            and self.employee_id.exclude_transportation_from_attendance_gross
        )
        if not exclude_transport_from_deduction:
            return gross_amount

        transport_amount = self._get_transportation_allowance_amount(contract)
        return max(gross_amount - transport_amount, 0.0)

    @api.depends("employee_id",
                 "date",
                 "pl_sign_in",
                 "pl_sign_out",
                 "employee_id.contract_id",
                 "employee_id.contract_id.gross_amount",
                 "employee_id.contract_id.contract_salary_rule_ids",
                 "employee_id.contract_id.contract_salary_rule_ids.amount",
                 "employee_id.contract_id.contract_salary_rule_ids.pay_in_payslip",
                 "employee_id.contract_id.contract_salary_rule_ids.salary_rule_id",
                 "employee_id.contract_id.contract_salary_rule_ids.salary_rule_id.name",
                 "employee_id.contract_id.contract_salary_rule_ids.salary_rule_id.code")
    def _compute_day_amount(self):
        for line in self:
            if line.employee_id and line.employee_id.contract_id and line.date:
                month_days = line._get_month_days_divisor(line.date)
                salary_base = line._get_deduction_salary_base(line.employee_id.contract_id)
                line.day_amount = salary_base / month_days if month_days else 0.0
            else:
                line.day_amount = 0.0

    @api.depends("employee_id",
                 "late_in",
                 "date",
                 "pl_sign_in",
                 "pl_sign_out",
                 "employee_id.contract_id",
                 "employee_id.contract_id.gross_amount",
                 "employee_id.contract_id.contract_salary_rule_ids",
                 "employee_id.contract_id.contract_salary_rule_ids.amount",
                 "employee_id.contract_id.contract_salary_rule_ids.pay_in_payslip",
                 "employee_id.contract_id.contract_salary_rule_ids.salary_rule_id",
                 "employee_id.contract_id.contract_salary_rule_ids.salary_rule_id.name",
                 "employee_id.contract_id.contract_salary_rule_ids.salary_rule_id.code")
    def _compute_late_in_amount(self):
        for line in self:
            if line.employee_id and line.date and line.late_in > 0:
                month_days = line._get_month_days_divisor(line.date)
                salary_base = line._get_deduction_salary_base(line.employee_id.contract_id)
                day_amount = salary_base / month_days if month_days else 0.0
                hours_per_day = line.employee_id.contract_id.resource_calendar_id.hours_per_day
                line.late_in_amount = (line.late_in * day_amount) / hours_per_day if hours_per_day > 0 else 0.0
            else:
                line.late_in_amount = 0.0

    @api.depends("employee_id",
                 "status",
                 "date",
                 "employee_id.contract_id",
                 "employee_id.contract_id.gross_amount",
                 "employee_id.contract_id.contract_salary_rule_ids",
                 "employee_id.contract_id.contract_salary_rule_ids.amount",
                 "employee_id.contract_id.contract_salary_rule_ids.pay_in_payslip",
                 "employee_id.contract_id.contract_salary_rule_ids.salary_rule_id",
                 "employee_id.contract_id.contract_salary_rule_ids.salary_rule_id.name",
                 "employee_id.contract_id.contract_salary_rule_ids.salary_rule_id.code")
    def _compute_absence_amount(self):
        for line in self:
            if not line.employee_id or not line.employee_id.contract_id or not line.date:
                line.absence_amount = 0.0
                continue
            month_days = line._get_month_days_divisor(line.date)
            salary_base = line._get_deduction_salary_base(line.employee_id.contract_id)
            day_amount = salary_base / month_days if month_days else 0.0
            line.absence_amount = day_amount if line.status == "ab" else 0.0

    @api.depends("overtime",
                 "worked_hours",
                 "employee_id",
                 "employee_id.add_overtime",
                 "employee_id.contract_id",
                 "employee_id.contract_id.wage",
                 "employee_id.contract_id.resource_calendar_id",
                 "employee_id.contract_id.resource_calendar_id.hours_per_day")
    def _compute_overtime_amount(self):
        for line in self:
            if not line.employee_id or not line.employee_id.contract_id or not line.employee_id.add_overtime:
                line.overtime_amount = 0.0
                continue
            if line.overtime <= 0:
                line.overtime_amount = 0.0
                continue

            wage = line.employee_id.contract_id.wage or 0.0
            calendar_hours_per_day = line.employee_id.contract_id.resource_calendar_id.hours_per_day or 8.0

            if line.employee_id.resource_calendar_id.id == 6:
                hourly_rate = (wage / 30.0 / 8.0) * 1.5
            else:
                hourly_rate = (wage / 30.0 / calendar_hours_per_day) * 1.5

            line.overtime_amount = line.overtime * hourly_rate

    @api.depends("employee_id",
                 "early_check_out",
                 "date",
                 "pl_sign_in",
                 "pl_sign_out",
                 "employee_id.contract_id",
                 "employee_id.contract_id.gross_amount",
                 "employee_id.contract_id.contract_salary_rule_ids",
                 "employee_id.contract_id.contract_salary_rule_ids.amount",
                 "employee_id.contract_id.contract_salary_rule_ids.pay_in_payslip",
                 "employee_id.contract_id.contract_salary_rule_ids.salary_rule_id",
                 "employee_id.contract_id.contract_salary_rule_ids.salary_rule_id.name",
                 "employee_id.contract_id.contract_salary_rule_ids.salary_rule_id.code",
                 "att_sheet_id",
                 "att_sheet_id.att_policy_id",
                 "att_sheet_id.att_policy_id.early_rule_id",
                 )
    def _compute_early_check_out_amount(self):
        for line in self:
            if line.employee_id and line.date and line.early_check_out > 0:
                month_days = line._get_month_days_divisor(line.date)
                salary_base = line._get_deduction_salary_base(line.employee_id.contract_id)
                day_amount = salary_base / month_days if month_days else 0.0
                # hours_per_day = line.pl_sign_out - line.pl_sign_in
                hours_per_day = line.employee_id.contract_id.resource_calendar_id.hours_per_day
                line.early_check_out_amount = (line.early_check_out * day_amount) / hours_per_day
            else:
                line.early_check_out_amount = 0

                # early_check_out_policy = line.att_sheet_id.att_policy_id.early_rule_id if (line.att_sheet_id.att_policy_id and line.att_sheet_id.att_policy_id.early_rule_id) else False
                # if early_check_out_policy:
                #     early_check_out_line = early_check_out_policy.line_ids[0]
                #     minutes = early_check_out_line.time
                #     l_type = early_check_out_line.type
                #     rate = early_check_out_line.rate
                #     amount = early_check_out_line.amount
                #     if l_type == "fix":
                #         line.early_check_out_amount = (line.early_check_out * 60 * amount) / minutes
                #     elif l_type == "rate":
                #         line.early_check_out_amount = (line.early_check_out * day_amount) / hours_per_day
                #     else:
                #         line.early_check_out_amount = 0
                # else:
                #     line.early_check_out_amount = 0