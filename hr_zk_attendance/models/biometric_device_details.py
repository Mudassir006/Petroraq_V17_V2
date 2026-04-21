# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Ammu Raj (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
import datetime
import logging
import pytz
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)
try:
    from zk import ZK, const
except ImportError:
    _logger.error("Please Install pyzk library.")


class BiometricDeviceDetails(models.Model):
    """Model for configuring and connect the biometric device with odoo"""
    _name = 'biometric.device.details'
    _description = 'Biometric Device Details'

    name = fields.Char(string='Name', required=True, help='Record Name')
    device_ip = fields.Char(string='Device IP', required=True,
                            help='The IP address of the Device')
    port_number = fields.Integer(string='Port Number', required=True,
                                 help="The Port Number of the Device")
    address_id = fields.Many2one('res.partner', string='Working Address',
                                 help='Working address of the partner')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda
                                     self: self.env.user.company_id.id,
                                 help='Current Company')

    def device_connect(self, zk):
        """Function for connecting the device with Odoo"""
        try:
            conn = zk.connect()
            return conn
        except Exception:
            return False

    def action_test_connection(self):
        """Checking the connection status"""
        zk = ZK(self.device_ip, port=self.port_number, timeout=30,
                password=False, ommit_ping=False)
        try:
            if zk.connect():
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': 'Successfully Connected',
                        'type': 'success',
                        'sticky': False
                    }
                }
        except Exception as error:
            raise ValidationError(f'{error}')

    def action_set_timezone(self):
        """Function to set user's timezone to device"""
        for info in self:
            machine_ip = info.device_ip
            zk_port = info.port_number
            try:
                # Connecting with the device with the ip and port provided
                zk = ZK(machine_ip, port=zk_port, timeout=15,
                        password=0,
                        force_udp=False, ommit_ping=False)
            except NameError:
                raise UserError(
                    _("Pyzk module not Found. Please install it"
                      "with 'pip3 install pyzk'."))
            conn = self.device_connect(zk)
            if conn:
                user_tz = self.env.context.get(
                    'tz') or self.env.user.tz or 'UTC'
                user_timezone_time = pytz.utc.localize(fields.Datetime.now())
                user_timezone_time = user_timezone_time.astimezone(
                    pytz.timezone(user_tz))
                conn.set_time(user_timezone_time)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': 'Successfully Set the Time',
                        'type': 'success',
                        'sticky': False
                    }
                }
            else:
                raise UserError(_(
                    "Please Check the Connection"))

    def action_clear_attendance(self):
        """Methode to clear record from the zk.machine.attendance model and
        from the device"""
        for info in self:
            try:
                machine_ip = info.device_ip
                zk_port = info.port_number
                try:
                    # Connecting with the device
                    zk = ZK(machine_ip, port=zk_port, timeout=30,
                            password=0, force_udp=False, ommit_ping=False)
                except NameError:
                    raise UserError(_(
                        "Please install it with 'pip3 install pyzk'."))
                conn = self.device_connect(zk)
                if conn:
                    conn.enable_device()
                    clear_data = zk.get_attendance()
                    if clear_data:
                        # Clearing data in the device
                        conn.clear_attendance()
                        # Clearing data from attendance log
                        self._cr.execute(
                            """delete from zk_machine_attendance""")
                        conn.disconnect()
                    else:
                        raise UserError(
                            _('Unable to clear Attendance log.Are you sure '
                              'attendance log is not empty.'))
                else:
                    raise UserError(
                        _('Unable to connect to Attendance Device. Please use '
                          'Test Connection button to verify.'))
            except Exception as error:
                raise ValidationError(f'{error}')

    @api.model
    def cron_download(self):
        machines = self.env['biometric.device.details'].search([])
        for machine in machines:
            machine.action_download_attendance()

    def action_download_attendance(self):
        """Function to download attendance records from the device"""
        _logger.info("++++++++++++Cron Executed++++++++++++++++++++++")
        zk_attendance = self.env['zk.machine.attendance']
        hr_attendance = self.env['hr.attendance']
        for info in self:
            machine_ip = info.device_ip
            zk_port = info.port_number
            try:
                # Connecting with the device with the ip and port provided
                zk = ZK(machine_ip, port=zk_port, timeout=15,
                        password=0,
                        force_udp=False, ommit_ping=False)
            except NameError:
                raise UserError(
                    _("Pyzk module not Found. Please install it"
                      "with 'pip3 install pyzk'."))
            conn = self.device_connect(zk)
            self.action_set_timezone()
            if conn:
                conn.disable_device()  # Device Cannot be used during this time.
                user = conn.get_users()
                attendance = conn.get_attendance()
                if attendance:
                    for each in attendance:
                        atten_time = each.timestamp
                        local_tz = pytz.timezone(
                            self.env.user.partner_id.tz or 'GMT')
                        local_dt = local_tz.localize(atten_time, is_dst=None)
                        utc_dt = local_dt.astimezone(pytz.utc)
                        utc_dt = utc_dt.strftime("%Y-%m-%d %H:%M:%S")
                        atten_time = datetime.datetime.strptime(
                            utc_dt, "%Y-%m-%d %H:%M:%S")
                        atten_time = fields.Datetime.to_string(atten_time)
                        for uid in user:
                            if uid.user_id == each.user_id:
                                get_user_id = self.env['hr.employee'].search(
                                    # [('device_id_num', '=', each.user_id)])
                                    [('code', '=', each.user_id)])
                                if get_user_id:
                                    duplicate_atten_ids = zk_attendance.search(
                                        [('device_id_num', '=', each.user_id),
                                         ('punching_time', '=', atten_time)])
                                    if not duplicate_atten_ids:
                                        zk_attendance.create({
                                            'employee_id': get_user_id.id,
                                            'device_id_num': each.user_id,
                                            'attendance_type': str(each.status),
                                            'punch_type': str(each.punch),
                                            'punching_time': atten_time,
                                            'address_id': info.address_id.id
                                        })
                                        att_var = hr_attendance.search([(
                                            'employee_id', '=', get_user_id.id),
                                            ('check_out', '=', False)])
                                        # if each.punch == 0:  # check-in
                                            # if not att_var:
                                            #     hr_attendance.create({
                                            #         'employee_id':
                                            #             get_user_id.id,
                                            #         'check_in': atten_time
                                            #     })
                                        # if each.punch == 1:  # check-out
                                        #     if len(att_var) == 1:
                                        #         att_var.write({
                                        #             'check_out': atten_time
                                        #         })
                                        #     else:
                                        #         att_var1 = hr_attendance.search(
                                        #             [('employee_id', '=',
                                        #               get_user_id.id)])
                                        #         if att_var1:
                                        #             att_var1[-1].write({
                                        #                 'check_out': atten_time
                                        #             })
                                # else:
                                #     raise ValidationError(f"This Employee With Code {each.user_id} Not Exist")
                                #     employee = self.env['hr.employee'].create({
                                #         'device_id_num': each.user_id,
                                #         'name': uid.name
                                #     })
                                #     zk_attendance.create({
                                #         'employee_id': employee.id,
                                #         'device_id_num': each.user_id,
                                #         'attendance_type': str(each.status),
                                #         'punch_type': str(each.punch),
                                #         'punching_time': atten_time,
                                #         'address_id': info.address_id.id
                                #     })
                                    # hr_attendance.create({
                                    #     'employee_id': employee.id,
                                    #     'check_in': atten_time
                                    # })
                    conn.disconnect
                    return True
                else:
                    raise UserError(_('Unable to get the attendance log, please'
                                      'try again later.'))
            else:
                raise UserError(_('Unable to connect, please check the'
                                  'parameters and network connections.'))

    def action_restart_device(self):
        """For restarting the device"""
        zk = ZK(self.device_ip, port=self.port_number, timeout=15,
                password=0,
                force_udp=False, ommit_ping=False)
        self.device_connect(zk).restart()

    def action_create_attendance(self):
        for rec in self:
            machine_attendance_ids = self.env["daily.attendance"].sudo().search([("employee_id", "!=", False)])
            if machine_attendance_ids:
                employee_data = {}

                for machine_attendance in machine_attendance_ids:
                    emp_id = machine_attendance.employee_id.id
                    punch_datetime = machine_attendance.punching_time
                    punch_date = punch_datetime.date()
                    punch_date_str = punch_datetime.date().isoformat()

                    if emp_id not in employee_data:
                        employee_data[emp_id] = {}

                    if punch_date_str not in employee_data[emp_id]:
                        employee_data[emp_id][punch_date_str] = {
                            'min': punch_datetime,
                            'max': punch_datetime
                        }
                    else:
                        current = employee_data[emp_id][punch_date_str]
                        if punch_datetime < current['min']:
                            current['min'] = punch_datetime
                        if punch_datetime > current['max']:
                            current['max'] = punch_datetime

                # Now `employee_data` is in the desired format
                for k_employee_id, attendance_values in employee_data.items():
                    employee_id = self.env["hr.employee"].browse(k_employee_id)
                    for k_date, att_vals in attendance_values.items():
                        check_in = att_vals.get("min")
                        check_out = att_vals.get("max")
                        attendance_id = self.env["hr.attendance"].search([("employee_id", "=", k_employee_id), ("day_date", "=", check_in.date())], limit=1)
                        if attendance_id:
                            if not attendance_id.check_out:
                                attendance_id.sudo().write({"check_out": check_out})
                            elif attendance_id.check_out:
                                if check_out > attendance_id.check_out:
                                    attendance_id.sudo().write({"check_out": check_out})
                        else:
                            # if check_in != check_out:
                            new_attendance = self.env["hr.attendance"].create({
                                "employee_id": employee_id.id,
                                "check_in": check_in,
                                "check_out": check_out,
                            })
                # return employee_data
