import logging
from datetime import datetime, time, timedelta
import random

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo import tools

_logger = logging.getLogger(__name__)


class UserAttendance(models.Model):
    _name = 'user.attendance'
    _description = 'User Attendance'
    _order = 'timestamp DESC, user_id, status, attendance_state_id, device_id'

    device_id = fields.Many2one('attendance.device', string='Attendance Machine', required=True, ondelete='restrict',
                                index=True)
    user_id = fields.Many2one('attendance.device.user', string='Machine User', required=True, ondelete='cascade',
                              index=True)
    timestamp = fields.Datetime(string='Timestamp', required=True, index=True,
                                help="The date and time at which the employee took a check in/out action at the attendance machine")
    status = fields.Integer(string='Machine Attendance State', required=True,
                            help="The state which is the unique number stored in the machine to"
                                 " indicate type of attendance (e.g. 0: Checkin, 1: Checkout, etc)")
    attendance_state_id = fields.Many2one('attendance.state', string='Software Attendance State',
                                          help="This technical field is to map the attendance"
                                               " status stored in the machine and the attendance status in System",
                                          required=True, index=True)
    activity_id = fields.Many2one('attendance.activity', related='attendance_state_id.activity_id', store=True,
                                  index=True)
    hr_attendance_id = fields.Many2one('hr.attendance', string='HR Attendance', ondelete='set null',
                                       help="The technical field to link Machine Attendance Data with System Attendance Data",
                                       index=True)

    type = fields.Selection(string='Activity Type', related='attendance_state_id.type', store=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', related='user_id.employee_id', store=True,
                                  index=True)
    synced = fields.Boolean(string='Synced',
                            help="This field is to indicate whether the attendance data is synchronized to System or not")

    _sql_constraints = [
        ('unique_user_id_device_id_timestamp',
         'UNIQUE(user_id, device_id, timestamp)',
         "The Timestamp and User must be unique per machine"),
    ]

    @api.constrains('status', 'attendance_state_id')
    def constrains_status_attendance_state_id(self):
        for r in self:
            if r.status != r.attendance_state_id.code:
                raise ValidationError(
                    _("Attendance Status conflict! The status number from machine must match the attendance status defined in System."))

    def _prepare_last_hr_attendance_domain(self):
        self.ensure_one()
        return [
            ('employee_id', '=', self.employee_id.id),
            ('check_in', '<=', self.timestamp),
            ('activity_id', 'in', [False, self.activity_id.id]),
        ]

    def _get_last_hr_attendance(self, user_attendance, hr_attendances):
        last_hr_attendance = hr_attendances.filtered(
            lambda hr_att: hr_att.employee_id == user_attendance.employee_id
                           and hr_att.checkin_device_id
                           and hr_att.check_in <= user_attendance.timestamp
                           and (hr_att.activity_id == user_attendance.activity_id
                                or not hr_att.activity_id)).sorted('check_in')
        return last_hr_attendance and last_hr_attendance[-1:] or False

    def _prepare_hr_attendance_vals(self):
        return {
            'employee_id': self.employee_id.id,
            'check_in': self.timestamp,
            'checkin_device_id': self.device_id.id,
            'activity_id': self.activity_id.id,
        }

    def _create_hr_attendance(self):
        vals_list = []
        for r in self:
            vals_list.append(r._prepare_hr_attendance_vals())
        return self.env['hr.attendance'].with_context(sync_from_device=True).create(vals_list)

    def _sync_attendance(self):
        """
        This method synchronizes `user.attendance` data into `hr.attendance` data
        """
        error_msg = {}
        all_hr_attendances = self.env['hr.attendance'].search([('employee_id', 'in', self.employee_id.ids)])
        for attendance_activity in self.activity_id:
            for employee in self.filtered(lambda r: r.activity_id == attendance_activity).employee_id:
                unsync_user_attendances = self.filtered(
                    lambda uatt: uatt.employee_id == employee
                                 and uatt.activity_id == attendance_activity
                ).sorted('timestamp')
                hr_attendances = all_hr_attendances.filtered(
                    lambda hr_att: hr_att.employee_id == employee
                )
                for uatt in unsync_user_attendances:
                    # Do flush manually to avoid magical user error:
                    # https://github.com/Viindoo/tvtmaaddons/pull/4053
                    try:
                        with self.env.cr.savepoint(flush=False), tools.mute_logger('odoo.sql_db'):
                            last_hr_attendance = self._get_last_hr_attendance(uatt, hr_attendances)
                            uatt_update = False
                            if uatt.type == 'checkin':
                                if not last_hr_attendance or (
                                        last_hr_attendance.check_out and uatt.timestamp > last_hr_attendance.check_out):
                                    last_hr_attendance = uatt._create_hr_attendance()
                                    uatt_update = True
                            else:
                                if last_hr_attendance and not last_hr_attendance.check_out and uatt.timestamp >= last_hr_attendance.check_in:
                                    last_hr_attendance.with_context(not_manual_check_out_modification=True,
                                                                    sync_from_device=True).write({
                                        'check_out': uatt.timestamp,
                                        'checkout_device_id': uatt.device_id.id
                                    })
                                    uatt_update = True
                            uatt_vals_to_update = {'synced': True}
                            if uatt_update:
                                if last_hr_attendance not in hr_attendances:
                                    hr_attendances += last_hr_attendance
                                uatt_vals_to_update.update({'hr_attendance_id': last_hr_attendance.id})
                            uatt.write(uatt_vals_to_update)
                            self.flush_recordset()
                    except Exception as e:
                        all_hr_attendances = self.env['hr.attendance'].search(
                            [('employee_id', 'in', self.employee_id.ids)])
                        error_msg.setdefault(uatt.device_id, [])
                        msg = str(e)
                        if msg not in error_msg[uatt.device_id]:
                            error_msg[uatt.device_id].append(str(e))
        if bool(error_msg):
            for device, msg_list in error_msg.items():
                device.message_post(body="<ol>%s</ol>" % "".join(["<li>%s</li>" % msg for msg in msg_list]))

    def action_sync_attendance(self):
        self._sync_attendance()

    @api.model
    def _prepare_unsynch_data_domain(self):
        return [
            ('hr_attendance_id', '=', False),
            ('employee_id', '!=', False),
            ('synced', '=', False),
        ]

    @api.model
    def _cron_synch_hr_attendance(self):
        unsync_data = self.env['user.attendance'].search(self._prepare_unsynch_data_domain())
        unsync_data._sync_attendance()

    @api.model
    def _get_checkin_leverage_tz(self):
        return (
                self.env['ir.config_parameter'].sudo().get_param('pr_attendance_device.checkin_leverage_tz')
                or self.env.user.tz
                or self.env.company.partner_id.tz
                or 'Asia/Riyadh'
        )

    @api.model
    def _apply_checkin_leverage_for_date(self, target_date, tz_name):

        seconds = random.randint(0, 59)
        minutes = random.randint(57, 59)
        leverage_start_local = datetime.combine(target_date, time(9, 0, 0))
        leverage_end_local = datetime.combine(target_date, time(9, 4, 0))
        normalized_checkin_local = datetime.combine(target_date, time(8, minutes, seconds))

        leverage_start_utc = fields.Datetime.to_datetime(
            self.env['to.base'].convert_local_to_utc(leverage_start_local, force_local_tz_name=tz_name, naive=True)
        )
        leverage_end_utc = fields.Datetime.to_datetime(
            self.env['to.base'].convert_local_to_utc(leverage_end_local, force_local_tz_name=tz_name, naive=True)
        )
        normalized_checkin_utc = fields.Datetime.to_datetime(
            self.env['to.base'].convert_local_to_utc(normalized_checkin_local, force_local_tz_name=tz_name, naive=True)
        )

        hr_attendances = self.env['hr.attendance'].search([
            ('check_in', '>=', leverage_start_utc),
            ('check_in', '<', leverage_end_utc),
        ])
        if hr_attendances:
            hr_attendances.with_context(sync_from_device=True).write({'check_in': normalized_checkin_utc})

        user_attendances = self.search([
            ('timestamp', '>=', leverage_start_utc),
            ('timestamp', '<', leverage_end_utc),
            ('type', '=', 'checkin'),
        ])
        if user_attendances:
            user_attendances.write({'timestamp': normalized_checkin_utc})
        return len(hr_attendances), len(user_attendances)

    @api.model
    def _cron_apply_checkin_leverage(self):

        tz_name = self._get_checkin_leverage_tz()
        now_local = fields.Datetime.context_timestamp(self.with_context(tz=tz_name), fields.Datetime.now())
        today = now_local.date()
        yesterday = today - timedelta(days=1)

        hr_count_today, user_count_today = self._apply_checkin_leverage_for_date(today, tz_name)
        hr_count_yesterday, user_count_yesterday = self._apply_checkin_leverage_for_date(yesterday, tz_name)

        _logger.info(
            "Check-in leverage applied in TZ %s. Updated hr.attendance: today=%s, yesterday=%s | "
            "user.attendance: today=%s, yesterday=%s",
            tz_name, hr_count_today, hr_count_yesterday, user_count_today, user_count_yesterday
        )