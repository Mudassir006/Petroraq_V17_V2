# -*- coding: utf-8 -*-

##############################################################################
#
#
#    Copyright (C) 2020-TODAY .
#    Author: Eng.Ramadan Khalil (<rkhalil1990@gmail.com>)
#
#    It is forbidden to publish, distribute, sublicense, or sell copies
#    of the Software or modified copies of the Software.
#
##############################################################################
import datetime
import pytz
from datetime import datetime, date, timedelta, time
from dateutil.relativedelta import relativedelta
from odoo import models, fields, tools, api, exceptions, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import format_date

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
TIME_FORMAT = "%H:%M:%S"
from odoo.tools import date_utils


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    @api.onchange('check_in', 'employee_id')
    def _onchange_check_in_gs(self):
        for rec in self:
            if rec.employee_id and rec.check_in:
                leave_ids = self.env['hr.leave'].search(
                    [('employee_id', '=', rec.employee_id.id), ('state', '=', 'validate'), ])
                for leave_id in leave_ids:
                    if leave_id.holiday_status_id.work_entry_type_id.id == self.env.ref(
                            'hr_work_entry_contract.work_entry_type_unpaid_leave').id:
                        if leave_id.request_date_from <= rec.check_in.date() <= leave_id.request_date_to:
                            raise ValidationError(_('There Is No Attendance For Employee %s' % rec.employee_id.name))

                    if leave_id.holiday_status_id.work_entry_type_id.id == self.env.ref(
                            'hr_work_entry_contract.work_entry_type_legal_leave').id:
                        if leave_id.request_date_from <= rec.check_in.date() <= leave_id.request_date_to:
                            raise ValidationError(_('There Is No Attendance For Employee %s' % rec.employee_id.name))

    day_name = fields.Selection(string='Day',
                                selection=[
                                    ('Saturday', 'Saturday'),
                                    ('Sunday', 'Sunday'),
                                    ('Monday', 'Monday'),
                                    ('Tuesday', 'Tuesday'),
                                    ('Wednesday', 'Wednesday'),
                                    ('Thursday', 'Thursday'),
                                    ('Friday', 'Friday'),
                                ])

    run_compute = fields.Boolean(compute='_compute_day_name')
    overtime_approval_state = fields.Selection([
        ('not_required', 'Not Required'),
        ('pending', 'Pending HR Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Overtime Approval', default='not_required', copy=False, tracking=True)
    overtime_for_approval = fields.Float(
        string='Overtime For Approval',
        compute='_compute_overtime_for_approval',
        store=True,
    )
    overtime_reject_reason = fields.Text(string='Overtime Rejection Reason', copy=False)

    @api.depends('worked_hours', 'check_in', 'check_out', 'employee_id')
    def _compute_overtime_for_approval(self):
        for rec in self:
            if not rec.employee_id or not rec.check_out:
                rec.overtime_for_approval = 0.0
                continue
            allows_overtime = (
                ('allow_overtime' in rec.employee_id._fields and rec.employee_id.allow_overtime)
                or ('add_overtime' in rec.employee_id._fields and rec.employee_id.add_overtime)
            )
            if not allows_overtime:
                rec.overtime_for_approval = 0.0
                continue
            hours_per_day = rec.employee_id.resource_calendar_id.hours_per_day or 8.0
            rec.overtime_for_approval = max((rec.worked_hours or 0.0) - hours_per_day, 0.0)

    def _sync_overtime_approval_state(self):
        for rec in self:
            if rec.overtime_for_approval > 0:
                if rec.overtime_approval_state == 'not_required':
                    rec.overtime_approval_state = 'pending'
            else:
                rec.overtime_approval_state = 'not_required'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_overtime_approval_state()
        return records

    def write(self, vals):
        result = super().write(vals)
        tracked_fields = {'check_in', 'check_out', 'employee_id', 'worked_hours'}
        if tracked_fields.intersection(vals.keys()):
            self._sync_overtime_approval_state()
        return result

    def action_approve_overtime(self):
        for rec in self:
            if rec.overtime_for_approval <= 0:
                raise ValidationError(_('No overtime to approve for this attendance record.'))
            rec.overtime_approval_state = 'approved'
            rec.overtime_reject_reason = False

    def action_open_reject_overtime_wizard(self):
        self.ensure_one()
        if self.overtime_for_approval <= 0:
            raise ValidationError(_('No overtime to reject for this attendance record.'))
        return {
            'name': _('Reject Overtime'),
            'type': 'ir.actions.act_window',
            'res_model': 'attendance.overtime.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_attendance_id': self.id},
        }

    def action_reject_overtime(self, reason=False):
        for rec in self:
            if rec.overtime_for_approval <= 0:
                raise ValidationError(_('No overtime to reject for this attendance record.'))
            rec.overtime_approval_state = 'rejected'
            rec.overtime_reject_reason = reason or _('Rejected by HR Manager')

    def _compute_day_name(self):
        for rec in self:
            rec.run_compute = True
            if rec.check_in:
                day = rec.check_in.strftime("%A")
                rec.day_name = day


class hrPayslip(models.Model):
    _inherit = 'hr.payslip'

    attendance_sheet_id = fields.Many2one('attendance.sheet', string='Attendance Sheet', )
    is_bool = fields.Boolean()
    absence_num = fields.Integer()
    total_absence = fields.Float()

    def compute_sheet(self):
        res = super(hrPayslip, self).compute_sheet()
        for rec in self:
            rec._get_workday_lines()
            # rec._get_total_absence()
            rec._check_net_salary()
        return res

    def _check_net_salary(self):
        return
        for rec in self:
            for line in rec.line_ids:
                if line.code == 'NET':
                    if line.total < 0:
                        raise ValidationError(
                            _('Total Salary Less Than Zero For Employee :  %s' % rec.employee_id.name))

    # def _get_total_absence(self):
    #     for rec in self:
    #         wd_diff = fields.Datetime.from_string(rec.date_to) - fields.Datetime.from_string(rec.date_from)
    #         days = wd_diff.days + 1
    #
    #         rec.total_absence = 0
    #         if rec.absence_num:
    #             # amount_day = (rec.contract_id.wage + rec.contract_id.trans_allowance_val) / days
    #             amount_day = (rec.contract_id.net_amount) / days
    #             rec.total_absence = rec.absence_num * amount_day

    def _get_workday_lines(self):
        for rec in self:
            if not rec.is_bool:
                self.ensure_one()
                rec.worked_days_line_ids = [(5, 0, 0)]
                work_entry_obj = self.env['hr.work.entry.type']
                overtime_work_entry = work_entry_obj.search([('code', '=', 'ATTSHOT')])
                latin_work_entry = work_entry_obj.search([('code', '=', 'ATTSHLI')])
                absence_work_entry = work_entry_obj.search([('code', '=', 'ATTSHAB')])
                difftime_work_entry = work_entry_obj.search([('code', '=', 'ATTSHDT')])
                # total_unpaid_leave_hours = rec.attendance_sheet_id.unpaid_leave * rec.contract_id.resource_calendar_id.hours_per_day
                total_unpaid_leave_hours = rec.attendance_sheet_id.unpaid_leave * (
                        rec.contract_id.resource_calendar_id.hours_per_day + 1)
                # total_paid_leave_hours = rec.attendance_sheet_id.paid_leave * rec.contract_id.resource_calendar_id.hours_per_day
                total_paid_leave_hours = rec.attendance_sheet_id.paid_leave * (
                        rec.contract_id.resource_calendar_id.hours_per_day + 1)
                # total_num_att_hours = rec.attendance_sheet_id.num_att * rec.contract_id.resource_calendar_id.hours_per_day
                total_num_att_hours = rec.attendance_sheet_id.num_att * (
                        rec.contract_id.resource_calendar_id.hours_per_day + 1)
                attendances = self.env['hr.attendance'].search(
                    [('employee_id', '=', rec.employee_id.id), ('check_in', '>=', rec.date_from),
                     ('check_out', '<=', rec.date_to)])
                leave_ids = self.env['hr.leave'].search(
                    [('employee_id', '=', rec.employee_id.id), ('request_date_from', '>=', rec.date_from),
                     ('request_date_to', '<=', rec.date_to)])

                att = [{
                    'name': "Attendance",
                    'work_entry_type_id': self.env.ref('hr_work_entry.work_entry_type_attendance').id,
                    'sequence': 1,
                    'number_of_days': rec.attendance_sheet_id.num_att,
                    'number_of_hours': total_num_att_hours,
                }]
                unpaid = [{
                    'name': "Unpaid",
                    'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_unpaid_leave').id,
                    'sequence': 2,
                    'number_of_days': rec.attendance_sheet_id.unpaid_leave,
                    'number_of_hours': total_unpaid_leave_hours,
                }]
                paid = [{
                    'name': "Paid Time Off",
                    'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_legal_leave').id,
                    'sequence': 0,
                    'number_of_days': rec.attendance_sheet_id.paid_leave,
                    'number_of_hours': total_paid_leave_hours,
                }]
                overtime = [{
                    'name': "Overtime",
                    'code': 'OVT',
                    'work_entry_type_id': overtime_work_entry[0].id,
                    'sequence': 30,
                    # 'number_of_days': 0,
                    'number_of_days': rec.attendance_sheet_id.approved_overtime_hours / rec.employee_id.contract_id.resource_calendar_id.hours_per_day,
                    'number_of_hours': rec.attendance_sheet_id.approved_overtime_hours,
                    'amount': (
                                rec.attendance_sheet_id.approved_overtime_amount + rec.attendance_sheet_id.carry_forward_overtime_amount) if rec.employee_id.add_overtime else 0.0,
                }]
                if not attendances and not leave_ids:
                    num_weekend = 0
                    weekend_amount = 0
                    for lin in rec.attendance_sheet_id.line_ids:
                        if lin.status == 'weekend':
                            num_weekend += 1
                            weekend_amount += lin.day_amount
                    absence = [{
                        'name': "Absence",
                        'code': 'ABS',
                        'work_entry_type_id': absence_work_entry[0].id,
                        'sequence': 35,
                        'number_of_days': rec.attendance_sheet_id.no_absence + num_weekend,
                        'number_of_hours': rec.attendance_sheet_id.tot_absence + (num_weekend * 8),
                        'amount': rec.attendance_sheet_id.tot_absence_amount + weekend_amount + rec.attendance_sheet_id.carry_forward_absence_amount
                    }]
                    rec.absence_num = rec.attendance_sheet_id.no_absence + num_weekend
                    rec.total_absence = rec.attendance_sheet_id.tot_absence_amount + weekend_amount + rec.attendance_sheet_id.carry_forward_absence_amount
                else:
                    absence = [{
                        'name': "Absence",
                        'code': 'ABS',
                        'work_entry_type_id': absence_work_entry[0].id,
                        'sequence': 35,
                        'number_of_days': rec.attendance_sheet_id.no_absence,
                        'number_of_hours': rec.attendance_sheet_id.tot_absence,
                        'amount': rec.attendance_sheet_id.tot_absence_amount + rec.attendance_sheet_id.carry_forward_absence_amount,
                    }]
                    rec.absence_num = rec.attendance_sheet_id.no_absence
                    rec.total_absence = rec.attendance_sheet_id.tot_absence_amount + rec.attendance_sheet_id.carry_forward_absence_amount

                late = [{
                    'name': "Late In",
                    'code': 'LATE',
                    'work_entry_type_id': latin_work_entry[0].id,
                    'sequence': 40,
                    'number_of_days': rec.attendance_sheet_id.no_late,
                    'number_of_hours': rec.attendance_sheet_id.tot_late,
                    'amount': rec.attendance_sheet_id.tot_late_amount,
                }]
                difftime = [{
                    'name': "Difference time",
                    'code': 'DIFFT',
                    'work_entry_type_id': difftime_work_entry[0].id,
                    'sequence': 45,
                    'number_of_days': rec.attendance_sheet_id.no_difftime,
                    'number_of_hours': rec.attendance_sheet_id.tot_difftime,
                    'amount': rec.attendance_sheet_id.tot_difftime_amount,
                }]
                # worked_days_lines = att + paid + unpaid + overtime + late + absence + difftime
                worked_days_lines = att + paid + unpaid + overtime + late + absence
                rec.worked_days_line_ids = [(0, 0, x) for x in
                                            worked_days_lines]
                rec.is_bool = True
                rec.compute_sheet()


class AttendanceSheet(models.Model):
    _name = 'attendance.sheet'
    _inherit = ['mail.thread.cc', 'mail.activity.mixin']
    _description = 'Hr Attendance Sheet'

    name = fields.Char("name")
    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee',
                                  required=True)

    batch_id = fields.Many2one(comodel_name='attendance.sheet.batch',
                               string='Attendance Sheet Batch')
    department_id = fields.Many2one(related='employee_id.department_id',
                                    string='Department', store=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True,
                                 copy=False, required=True,
                                 default=lambda self: self.env.company,
                                 states={'draft': [('readonly', False)]})
    date_from = fields.Date(string='Date From', readonly=True, required=True,
                            default=lambda self: fields.Date.to_string(
                                date.today().replace(day=1)), )
    date_to = fields.Date(string='Date To', readonly=True, required=True,
                          default=lambda self: fields.Date.to_string(
                              (datetime.now() + relativedelta(months=+1, day=1,
                                                              days=-1)).date()))
    line_ids = fields.One2many(comodel_name='attendance.sheet.line',
                               string='Attendances', readonly=True,
                               inverse_name='att_sheet_id')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('done', 'Approved')], default='draft', track_visibility='onchange',
        string='Status', required=True, readonly=True, index=True,
        help=' * The \'Draft\' status is used when a HR user is creating a new  attendance sheet. '
             '\n* The \'Confirmed\' status is used when  attendance sheet is confirmed by HR user.'
             '\n* The \'Approved\' status is used when  attendance sheet is accepted by the HR Manager.')
    overtime_approval_state = fields.Selection([
        ('not_required', 'Not Required'),
        ('pending', 'Pending HR Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Overtime Approval', compute='_compute_overtime_approval_state', store=True, tracking=True, copy=False)
    has_overtime = fields.Boolean(
        string='Has Overtime',
        compute='_compute_has_overtime',
        store=True,
    )
    approved_overtime_hours = fields.Float(
        string="Approved Overtime Hours",
        compute='_compute_approved_overtime',
        store=True,
    )
    approved_overtime_amount = fields.Float(
        string="Approved Overtime Amount",
        compute='_compute_approved_overtime',
        store=True,
    )
    no_overtime = fields.Integer(compute="_compute_sheet_total",
                                 string="No of overtimes", readonly=True,
                                 store=True)
    tot_overtime = fields.Float(compute="_compute_sheet_total",
                                string="Total Over Time", readonly=True,
                                store=True)
    tot_overtime_amount = fields.Float(compute="_compute_sheet_total",
                                       string="Total Overtime Amount", readonly=True, store=True)
    tot_difftime = fields.Float(compute="_compute_sheet_total",
                                string="Total Diff time Hours", readonly=True,
                                store=True)
    no_difftime = fields.Integer(compute="_compute_sheet_total",
                                 string="No of Diff Times", readonly=True,
                                 store=True)
    tot_difftime_amount = fields.Float(compute="_compute_sheet_total",
                                       string="Total Diff Amount", readonly=True, store=True)
    tot_late = fields.Float(compute="_compute_sheet_total",
                            string="Total Late In", readonly=True, store=True)
    tot_late_amount = fields.Float(compute="_compute_sheet_total",
                                   string="Total Late In Amount", readonly=True, store=True)
    no_late = fields.Integer(compute="_compute_sheet_total",
                             string="No of Lates",
                             readonly=True, store=True)
    no_absence = fields.Integer(compute="_compute_sheet_total",
                                string="No of Absence Days", readonly=True,
                                store=True)
    tot_absence = fields.Float(compute="_compute_sheet_total",
                               string="Total absence Hours", readonly=True,
                               store=True)
    tot_absence_amount = fields.Float(compute="_compute_sheet_total",
                                      string="Total Absence Amount", readonly=True, store=True)
    tot_worked_hour = fields.Float(compute="_compute_sheet_total",
                                   string="Total Late In", readonly=True,
                                   store=True)
    att_policy_id = fields.Many2one(comodel_name='hr.attendance.policy',
                                    string="Attendance Policy ", required=True)
    payslip_id = fields.Many2one(comodel_name='hr.payslip', string='PaySlip')
    predictive_mode = fields.Boolean(
        string='Predictive Payroll',
        default=True,
        help='When enabled, days after the predictive cutoff are assumed as present without deductions.',
    )
    predictive_cutoff_date = fields.Date(
        string='Predictive Cutoff Date',
        default=fields.Date.context_today,
        help='Days after this date are projected as present when payroll is run before month end.',
    )
    carry_forward_deduction = fields.Float(
        string='Carry Forward Deduction',
        readonly=True,
        copy=False,
        help='Deductions captured from previously projected payroll periods and applied in this payroll.',
    )
    carry_forward_absence_amount = fields.Float(
        string='Carry Forward Absence',
        readonly=True,
        copy=False,
        help='Absence-only amount carried from prior projected periods.',
    )
    carry_forward_late_amount = fields.Float(
        string='Carry Forward Late',
        readonly=True,
        copy=False,
        help='Late-only amount carried from prior projected periods.',
    )
    carry_forward_diff_amount = fields.Float(
        string='Carry Forward Diff',
        readonly=True,
        copy=False,
        help='Difference-time amount carried from prior projected periods.',
    )
    carry_forward_overtime_amount = fields.Float(
        string='Carry Forward Overtime',
        readonly=True,
        copy=False,
        help='Overtime amount carried from prior projected periods.',
    )
    carry_forward_early_checkout_amount = fields.Float(
        string='Carry Forward Early Checkout',
        readonly=True,
        copy=False,
        help='Early checkout amount carried from prior projected periods.',
    )
    opening_carry_absence_amount = fields.Float(
        string='Opening Carry Absence',
        help='Manual one-time carry amount from legacy payroll periods before predictive mode was enabled.',
    )
    opening_carry_late_amount = fields.Float(
        string='Opening Carry Late',
        help='Manual one-time late carry amount from legacy payroll periods.',
    )
    opening_carry_diff_amount = fields.Float(
        string='Opening Carry Diff',
        help='Manual one-time diff-time carry amount from legacy payroll periods.',
    )
    opening_carry_early_checkout_amount = fields.Float(
        string='Opening Carry Early Checkout',
        help='Manual one-time early checkout carry amount from legacy payroll periods.',
    )
    opening_carry_overtime_amount = fields.Float(
        string='Opening Carry Overtime',
        help='Manual one-time overtime carry amount from legacy payroll periods.',
    )
    carry_forward_processed = fields.Boolean(
        string='Carry Forward Processed',
        default=False,
        copy=False,
        help='Technical flag to avoid deducting the same projected period more than once.',
    )
    carry_forward_run_date = fields.Date(
        string='Carry Forward Processed Date',
        readonly=True,
        copy=False,
    )
    carry_forward_amount = fields.Float(
        string='Carry Forward Amount (Source)',
        readonly=True,
        copy=False,
        help='Computed deduction amount for this source sheet that will be carried to a later payroll.',
    )
    carry_forward_settled_sheet_id = fields.Many2one(
        comodel_name='attendance.sheet',
        string='Carry Forward Settled In',
        readonly=True,
        copy=False,
        help='Attendance sheet where this source sheet carry-forward was finally deducted.',
    )

    contract_id = fields.Many2one('hr.contract', string='Contract',
                                  readonly=True,
                                  states={'draft': [('readonly', False)]})
    unpaid_leave = fields.Integer()
    paid_leave = fields.Integer()
    sick_leave = fields.Integer()
    business_trip_leave = fields.Integer()
    num_att = fields.Integer()
    attendance_amount = fields.Float(compute="_compute_sheet_total",
                                     string="Total Attendance Amount", readonly=True, store=True)

    total_unpaid_leave = fields.Float(compute='_compute_total_unpaid_leave')
    total_paid_leave = fields.Float(compute='_compute_total_unpaid_leave')
    total_sick_leave = fields.Float(compute='_compute_total_unpaid_leave')
    total_business_trip_leave = fields.Float(compute='_compute_total_unpaid_leave')

    def _employee_allows_overtime(self):
        self.ensure_one()
        return bool(
            self.employee_id and (
                ('allow_overtime' in self.employee_id._fields and self.employee_id.allow_overtime)
                or ('add_overtime' in self.employee_id._fields and self.employee_id.add_overtime)
            )
        )

    @api.depends('line_ids.overtime')
    def _compute_has_overtime(self):
        for rec in self:
            rec.has_overtime = any(line.overtime > 0 for line in rec.line_ids)

    @api.depends('line_ids.overtime_approval_state', 'line_ids.approved_overtime_hours', 'line_ids.approved_overtime_amount')
    def _compute_approved_overtime(self):
        for rec in self:
            approved_lines = rec.line_ids.filtered(lambda l: l.overtime_approval_state == 'approved')
            rec.approved_overtime_hours = sum(approved_lines.mapped('approved_overtime_hours'))
            rec.approved_overtime_amount = sum(approved_lines.mapped('approved_overtime_amount'))

    @api.depends('line_ids.overtime', 'line_ids.overtime_approval_state')
    def _compute_overtime_approval_state(self):
        for rec in self:
            overtime_lines = rec.line_ids.filtered(lambda l: l.overtime > 0)
            if not rec._employee_allows_overtime() or not overtime_lines:
                rec.overtime_approval_state = 'not_required'
                continue
            pending_count = len(overtime_lines.filtered(lambda l: l.overtime_approval_state == 'pending'))
            approved_count = len(overtime_lines.filtered(lambda l: l.overtime_approval_state == 'approved'))
            if pending_count:
                rec.overtime_approval_state = 'pending'
            elif approved_count and approved_count == len(overtime_lines):
                rec.overtime_approval_state = 'approved'
            else:
                rec.overtime_approval_state = 'rejected'

    def _refresh_line_overtime_approvals(self):
        for sheet in self:
            allows_overtime = sheet._employee_allows_overtime()
            for line in sheet.line_ids:
                if not allows_overtime or line.overtime <= 0:
                    line.overtime_approval_state = 'not_required'
                elif line.overtime_approval_state == 'not_required':
                    line.overtime_approval_state = 'pending'

    @api.depends("line_ids.status", "line_ids.date", "employee_id", "paid_leave", "unpaid_leave", "sick_leave",
                 "business_trip_leave")
    def _compute_total_unpaid_leave(self):
        for rec in self:
            # Compute Paid Leave
            unpaid_amount = 0
            paid_amount = 0
            sick_amount = 0
            business_trip_amount = 0
            if rec.paid_leave > 0 or rec.unpaid_leave > 0 or rec.sick_leave or rec.business_trip_leave > 0:
                for line in rec.line_ids:
                    if line.status == "leave":
                        leave_id = self.env['hr.leave'].search([('employee_id', '=', rec.employee_id.id),
                                                                ('request_date_from', '<=', line.date),
                                                                ('request_date_to', '>=', line.date),
                                                                ('state', '=', "validate"),
                                                                ])
                        if leave_id and leave_id.holiday_status_id:
                            if leave_id.holiday_status_id.is_paid:
                                if leave_id.holiday_status_id.leave_type == "sick_leave":
                                    sick_amount += line.day_amount
                                elif leave_id.holiday_status_id.leave_type == "business_leave":
                                    business_trip_amount += line.day_amount
                                else:
                                    paid_amount += line.day_amount
                            elif not leave_id.holiday_status_id.is_paid:
                                unpaid_amount += line.day_amount
            rec.total_unpaid_leave = unpaid_amount
            rec.total_paid_leave = paid_amount
            rec.total_sick_leave = sick_amount
            rec.total_business_trip_leave = business_trip_amount

    # def _compute_total_unpaid_leave(self):
    #     for rec in self:
    #         wd_diff = fields.Datetime.from_string(rec.date_to) - fields.Datetime.from_string(rec.date_from)
    #         days = wd_diff.days + 1
    #
    #         rec.total_unpaid_leave = 0
    #         if rec.unpaid_leave:
    #             # amount_day = rec.contract_id.total_package_val / days
    #             amount_day = rec.contract_id.gross_amount / days
    #             rec.total_unpaid_leave = rec.unpaid_leave * amount_day
    #
    #         rec.total_paid_leave = 0
    #         if rec.paid_leave:
    #             # amount_day = rec.contract_id.total_package_val / days
    #             amount_day = rec.contract_id.gross_amount / days
    #             rec.total_paid_leave = rec.paid_leave * amount_day

    def unlink(self):
        if any(self.filtered(
                lambda att: att.state not in ('draft', 'confirm'))):
            # TODO:un comment validation in case on non testing
            pass
            # raise UserError(_(
            #     'You cannot delete an attendance sheet which is '
            #     'not draft or confirmed!'))
        return super(AttendanceSheet, self).unlink()

    # @api.constrains('date_from', 'date_to')
    # def check_date(self):
    #     for sheet in self:
    #         emp_sheets = self.env['attendance.sheet'].search(
    #             [('employee_id', '=', sheet.employee_id.id),
    #              ('id', '!=', sheet.id)])
    #         for emp_sheet in emp_sheets:
    #             if max(sheet.date_from, emp_sheet.date_from) < min(
    #                     sheet.date_to, emp_sheet.date_to):
    #                 raise UserError(_(
    #                     'You Have Already Attendance Sheet For That '
    #                     'Period  Please pick another date !'))

    def action_confirm(self):
        # if self.line_ids:
        for sheet in self:
            sheet._refresh_line_overtime_approvals()
            sheet.write({'state': 'confirm'})

    def action_approve(self):
        payslips = self.action_create_payslip()
        self.write({'state': 'done'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_submit_overtime_approval(self):
        for sheet in self:
            if not sheet._employee_allows_overtime():
                raise UserError(_("This employee is not eligible for overtime approval."))
            overtime_lines = sheet.line_ids.filtered(lambda l: l.overtime > 0)
            if not overtime_lines:
                raise UserError(_("There is no overtime to submit for approval."))
            overtime_lines.filtered(lambda l: l.overtime_approval_state == 'rejected').write({
                'overtime_approval_state': 'pending'
            })

    def action_approve_overtime(self):
        for sheet in self:
            overtime_lines = sheet.line_ids.filtered(lambda l: l.overtime > 0 and l.overtime_approval_state == 'pending')
            if not overtime_lines or not sheet._employee_allows_overtime():
                raise UserError(_("This attendance sheet has no eligible overtime to approve."))
            overtime_lines.write({'overtime_approval_state': 'approved'})

    def action_reject_overtime(self):
        for sheet in self:
            overtime_lines = sheet.line_ids.filtered(lambda l: l.overtime > 0 and l.overtime_approval_state == 'pending')
            if not overtime_lines or not sheet._employee_allows_overtime():
                raise UserError(_("This attendance sheet has no eligible overtime to reject."))
            overtime_lines.write({'overtime_approval_state': 'rejected'})

    @api.onchange('employee_id', 'date_from', 'date_to')
    def onchange_employee(self):
        if (not self.employee_id) or (not self.date_from) or (not self.date_to):
            return
        employee = self.employee_id
        date_from = self.date_from
        date_to = self.date_to
        self.name = 'Attendance Sheet - %s - %s' % (self.employee_id.name or '',
                                                    format_date(self.env,
                                                                self.date_to,
                                                                date_format="MMMM y"))
        self.company_id = employee.company_id
        contracts = employee._get_contracts(date_from, date_to)
        # if not contracts:
        #     raise ValidationError(
        #         _('There Is No Valid Contract For Employee %s' % employee.name))

        if not employee.contract_id or (employee.contract_id.state != "open"):
            raise ValidationError(
                _('There Is No Valid Contract For Employee %s' % employee.name))
        self.contract_id = contracts[0] if contracts else employee.contract_id
        if not self.contract_id.att_policy_id:
            raise ValidationError(_(
                "Employee %s does not have attendance policy" % employee.name))
        self.att_policy_id = self.contract_id.att_policy_id

    @api.depends('line_ids.status',
                 'line_ids.day_amount',
                 'line_ids.overtime',
                 'line_ids.overtime_amount',
                 'line_ids.diff_time',
                 'line_ids.diff_amount',
                 'line_ids.late_in',
                 'line_ids.late_in_amount',
                 'line_ids.absence_amount')
    def _compute_sheet_total(self):
        """
        Compute Total overtime,late ,absence,diff time and worked hours
        :return:
        """
        for sheet in self:
            # Compute Attendance
            attendance_lines = sheet.line_ids.filtered(lambda l: l.status in ["weekend", "ph"] or not l.status)
            sheet.num_att = len(attendance_lines)
            sheet.attendance_amount = sum(attendance_lines.mapped("day_amount")) if attendance_lines else 0

            calendar_hours_per_day = sheet.employee_id.resource_calendar_id.hours_per_day or 8.0
            overtime_min_worked_hours = calendar_hours_per_day
            overtime_lines = sheet.line_ids.filtered(lambda l: l.worked_hours > overtime_min_worked_hours)

            # sheet.tot_overtime = sum([l.overtime for l in overtime_lines])
            # if sheet.employee_id.id == 133:
            if sheet.employee_id.resource_calendar_id.id == 6:
                tot_overtime_hours_from_calc_def = 0
                site_overtime_min_worked_hours = 11 if calendar_hours_per_day >= 9 else calendar_hours_per_day
                # sheet.tot_overtime = sum([l.overtime for l in overtime_lines]) if sheet.employee_id.add_overtime else 0
                overtime_lines = sheet.line_ids.filtered(
                    lambda l: l.worked_hours > site_overtime_min_worked_hours or (l.pl_sign_in == 0 and l.ac_sign_in > 0
                                                                                  ))
                # sheet.tot_overtime = sum([(l.worked_hours -1) - sheet.employee_id.resource_calendar_id.hours_per_day for l in overtime_lines]) if sheet.employee_id.add_overtime else 0
                for overtime_line in overtime_lines:
                    tot_overtime_hours_from_calc_def += self.calculate_overtime_from_method(
                        overtime_line,
                        sheet.employee_id.resource_calendar_id.hours_per_day,
                        sheet.employee_id.add_overtime
                    )
                sheet.tot_overtime = tot_overtime_hours_from_calc_def
                if sheet.employee_id.add_overtime:
                    basic_salary = sheet.employee_id.contract_id.wage or 0
                    hourly_rate = (basic_salary / 30 / 8) * 1.5
                    sheet.tot_overtime_amount = sheet.tot_overtime * hourly_rate
                else:
                    sheet.tot_overtime_amount = 0
            else:
                overtime_lines = sheet.line_ids.filtered(
                    lambda l: l.worked_hours > overtime_min_worked_hours or (l.pl_sign_in == 0 and l.ac_sign_in > 0))

                # Calculate overtime per-day (sum daily extra hours),
                # instead of applying a monthly threshold.
                tot_overtime_hours_from_calc_def = 0
                for overtime_line in overtime_lines:
                    tot_overtime_hours_from_calc_def += self.calculate_overtime_from_method(
                        overtime_line,
                        sheet.employee_id.resource_calendar_id.hours_per_day,
                        sheet.employee_id.add_overtime
                    )

                sheet.tot_overtime = tot_overtime_hours_from_calc_def if sheet.employee_id.add_overtime else 0.0

                if sheet.employee_id.add_overtime and sheet.tot_overtime:
                    wage = sheet.employee_id.contract_id.wage or 0.0
                    hours_per_day = sheet.employee_id.contract_id.resource_calendar_id.hours_per_day or 8.0
                    hourly_rate = (wage / 30.0) / hours_per_day
                    sheet.tot_overtime_amount = sheet.tot_overtime * hourly_rate * 1.5
                else:
                    sheet.tot_overtime_amount = 0.0

            # sheet.tot_overtime_amount = (((tot_overtime_custom * 1.5) * sheet.employee_id.contract_id.wage) / 208) if sheet.employee_id.add_overtime else 0
            sheet.no_overtime = len(overtime_lines)
            # Compute Total Late In
            late_lines = sheet.line_ids.filtered(lambda l: l.late_in > 0)
            sheet.tot_late = sum([l.late_in for l in late_lines])
            sheet.tot_late_amount = sum([l.late_in_amount for l in late_lines])
            sheet.no_late = len(late_lines)
            # Compute Absence
            absence_lines = sheet.line_ids.filtered(
                lambda l: l.status == "ab")
            # lambda l: l.diff_time > 0 and l.status == "ab")
            sheet.tot_absence = sum([l.diff_time for l in absence_lines])
            sheet.tot_absence_amount = sum([l.absence_amount for l in absence_lines])
            sheet.no_absence = len(absence_lines)
            # Compute Diff Amount
            diff_lines = sheet.line_ids.filtered(
                lambda l: l.diff_time > 0 and l.diff_amount > 0)
            sheet.tot_difftime_amount = sum([l.diff_amount for l in diff_lines])
            diff_lines = sheet.line_ids.filtered(
                lambda l: l.diff_time > 0 and l.status != "ab")
            sheet.tot_difftime = sum([l.diff_time for l in diff_lines])
            sheet.no_difftime = len(diff_lines)

    def calculate_overtime_from_method(self, l, resource_calendar_hours_per_day, add_overtime):
        if add_overtime:
            if l.pl_sign_in > 0 and l.ac_sign_in > 0:
                return max(l.worked_hours - resource_calendar_hours_per_day, 0)
            elif l.pl_sign_in == 0 and l.ac_sign_in > 0:
                return l.worked_hours
        return 0

    def _get_float_from_time(self, time):
        str_time = datetime.strftime(time, "%H:%M")
        split_time = [int(n) for n in str_time.split(":")]
        float_time = split_time[0] + split_time[1] / 60.0
        return float_time

    def get_attendance_intervals(self, employee, day_start, day_end, tz):
        """

        :param employee:
        :param day_start:datetime the start of the day in datetime format
        :param day_end: datetime the end of the day in datetime format
        :return:
        """
        day_start_native = day_start.replace(tzinfo=tz).astimezone(
            pytz.utc).replace(tzinfo=None)
        day_end_native = day_end.replace(tzinfo=tz).astimezone(
            pytz.utc).replace(tzinfo=None)
        res = []
        attendances = self.env['hr.attendance'].sudo().search(
            [('employee_id.id', '=', employee.id),
             ('check_in', '>=', day_start_native),
             ('check_in', '<=', day_end_native)],
            order="check_in")
        for att in attendances:
            check_in = att.check_in
            check_out = att.check_out
            if not check_out:
                continue
            res.append((check_in, check_out))
        return res

    def _get_emp_leave_intervals(self, emp, start_datetime=None,
                                 end_datetime=None):
        leaves = []
        leave_obj = self.env['hr.leave']
        leave_ids = leave_obj.search([
            ('employee_id', '=', emp.id),
            ('state', '=', 'validate')])

        for leave in leave_ids:
            date_from = leave.date_from
            if end_datetime and date_from > end_datetime:
                continue
            date_to = leave.date_to
            if start_datetime and date_to < start_datetime:
                continue
            leaves.append((date_from, date_to))
        return leaves

    def get_public_holiday(self, date, emp):
        public_holiday = []
        public_holidays = self.env['hr.public.holiday'].sudo().search(
            [('date_from', '<=', date), ('date_to', '>=', date),
             ('state', '=', 'active')])
        for ph in public_holidays:
            print('ph is', ph.name, [e.name for e in ph.emp_ids])
            if not ph.emp_ids:
                return public_holidays
            if emp.id in ph.emp_ids.ids:
                public_holiday.append(ph.id)
        return public_holiday

    def _is_overtime_approved_for_day(self, employee, day_date, tz):
        attendance_obj = self.env['hr.attendance']
        day_start_local = tz.localize(datetime.combine(day_date, time.min))
        day_end_local = tz.localize(datetime.combine(day_date, time.max))
        day_start_utc = day_start_local.astimezone(pytz.utc).replace(tzinfo=None)
        day_end_utc = day_end_local.astimezone(pytz.utc).replace(tzinfo=None)
        domain = [
            ('employee_id', '=', employee.id),
            ('check_in', '<=', day_end_utc),
            ('check_out', '>=', day_start_utc),
            ('overtime_approval_state', '=', 'approved'),
            ('overtime_for_approval', '>', 0),
        ]
        return bool(attendance_obj.search_count(domain))

    def get_attendances(self):
        for att_sheet in self:
            att_sheet.line_ids.unlink()
            att_line = self.env["attendance.sheet.line"]
            from_date = att_sheet.date_from
            to_date = att_sheet.date_to
            emp = att_sheet.employee_id
            tz = pytz.timezone(emp.tz)
            if not tz:
                raise exceptions.Warning(
                    "Please add time zone for employee : %s" % emp.name)
            calendar_id = emp.contract_id.resource_calendar_id
            if not calendar_id:
                raise ValidationError(_(
                    'Please add working hours to the %s `s contract ' % emp.name))
            policy_id = att_sheet.att_policy_id
            if not policy_id:
                raise ValidationError(_(
                    'Please add Attendance Policy to the %s `s contract ' % emp.name))

            emp_contract = att_sheet.employee_id.contract_id
            emp_contract_end_date = emp_contract.expected_end_date if emp_contract and emp_contract.expected_end_date else False

            all_dates = [(from_date + timedelta(days=x)) for x in
                         range((to_date - from_date).days + 1)]
            abs_cnt = 0
            unpaid_leave = 0
            paid_leave = 0
            sick_leave = 0
            business_trip_leave = 0
            late_cnt = []
            predictive_cutoff = att_sheet.predictive_cutoff_date or fields.Date.context_today(self)
            for day in all_dates:
                # Add Custom Calendar Day For 26, 27/03/2025
                # Add Custom Calendar Day For 26, 27/03/2025
                day_date_day = day.day
                day_date_month = day.month
                # if (day == custom_date or day == custom_date_2) and calendar_id.id == 4:
                # if (day_date_day in [24, 25, 26, 27]  and day_date_month == 3) and emp.id != 133:
                #     calendar_id = self.env["resource.calendar"].sudo().browse(7)
                # elif (day_date_day in [24, 25, 26, 27]  and day_date_month == 3) and emp.id == 133:
                #     calendar_id = self.env["resource.calendar"].sudo().browse(8)
                # else:
                #     # calendar_id = self.env["resource.calendar"].sudo().browse(4)
                # calendar_id = emp.contract_id.resource_calendar_id
                day_start = datetime(day.year, day.month, day.day)
                day_end = day_start.replace(hour=23, minute=59,
                                            second=59)
                day_str = str(day.weekday())
                date = day.strftime('%Y-%m-%d')
                work_intervals = calendar_id.att_get_work_intervals_new(day_start,
                                                                        day_end, tz)
                attendance_intervals = self.get_attendance_intervals(emp,
                                                                     day_start,
                                                                     day_end,
                                                                     tz)
                leaves = self._get_emp_leave_intervals(emp, day_start, day_end)
                public_holiday = self.get_public_holiday(date, emp)
                reserved_intervals = []
                overtime_policy = policy_id.get_overtime()
                abs_flag = False
                if work_intervals:
                    if public_holiday:
                        if attendance_intervals:
                            for attendance_interval in attendance_intervals:
                                overtime = attendance_interval[1] - \
                                           attendance_interval[0]
                                float_overtime = overtime.total_seconds() / 3600
                                if float_overtime <= overtime_policy[
                                    'ph_after']:
                                    act_float_overtime = float_overtime = 0
                                else:
                                    act_float_overtime = (float_overtime -
                                                          overtime_policy[
                                                              'ph_after'])
                                    float_overtime = (float_overtime -
                                                      overtime_policy[
                                                          'ph_after']) * \
                                                     overtime_policy['ph_rate']
                                if not self._is_overtime_approved_for_day(emp, day, tz):
                                    float_overtime = 0
                                    act_float_overtime = 0
                                ac_sign_in = pytz.utc.localize(
                                    attendance_interval[0]).astimezone(tz)
                                float_ac_sign_in = self._get_float_from_time(
                                    ac_sign_in)
                                ac_sign_out = pytz.utc.localize(
                                    attendance_interval[1]).astimezone(tz)
                                worked_hours = attendance_interval[1] - \
                                               attendance_interval[0]
                                float_worked_hours = worked_hours.total_seconds() / 3600
                                float_ac_sign_out = float_ac_sign_in + float_worked_hours
                                values = {
                                    'date': date,
                                    'day': day_str,
                                    'ac_sign_in': float_ac_sign_in,
                                    'ac_sign_out': float_ac_sign_out,
                                    'worked_hours': float_worked_hours,
                                    # 'worked_hours': (float_worked_hours - 1) if float_worked_hours else 0,
                                    'overtime': float_overtime,
                                    'act_overtime': act_float_overtime,
                                    'att_sheet_id': self.id,
                                    'status': 'ph',
                                    'note': _("working on Public Holiday")
                                }
                                if att_sheet.employee_id.compute_attendance:
                                    att_line.create(values)
                        else:
                            values = {
                                'date': date,
                                'day': day_str,
                                'att_sheet_id': self.id,
                                'status': 'ph',
                            }
                            if att_sheet.employee_id.compute_attendance:
                                att_line.create(values)
                    else:
                        for i, work_interval in enumerate(work_intervals):
                            float_worked_hours = 0
                            att_work_intervals = []
                            diff_intervals = []
                            late_in_interval = []
                            diff_time = timedelta(hours=00, minutes=00,
                                                  seconds=00)
                            late_in = timedelta(hours=00, minutes=00,
                                                seconds=00)
                            overtime = timedelta(hours=00, minutes=00,
                                                 seconds=00)
                            for j, att_interval in enumerate(
                                    attendance_intervals):
                                if max(work_interval[0], att_interval[0]) < min(
                                        work_interval[1], att_interval[1]):
                                    current_att_interval = att_interval
                                    if i + 1 < len(work_intervals):
                                        next_work_interval = work_intervals[
                                            i + 1]
                                        if max(next_work_interval[0],
                                               current_att_interval[0]) < min(
                                            next_work_interval[1],
                                            current_att_interval[1]):
                                            split_att_interval = (
                                                next_work_interval[0],
                                                current_att_interval[1])
                                            current_att_interval = (
                                                current_att_interval[0],
                                                next_work_interval[0])
                                            attendance_intervals[
                                                j] = current_att_interval
                                            attendance_intervals.insert(j + 1,
                                                                        split_att_interval)
                                    att_work_intervals.append(
                                        current_att_interval)
                            reserved_intervals += att_work_intervals
                            pl_sign_in = self._get_float_from_time(
                                pytz.utc.localize(work_interval[0]).astimezone(
                                    tz))
                            pl_sign_out = self._get_float_from_time(
                                pytz.utc.localize(work_interval[1]).astimezone(
                                    tz))
                            pl_sign_in_time = pytz.utc.localize(
                                work_interval[0]).astimezone(tz)
                            pl_sign_out_time = pytz.utc.localize(
                                work_interval[1]).astimezone(tz)
                            ac_sign_in = 0
                            ac_sign_out = 0
                            status = ""
                            note = ""
                            if att_work_intervals:
                                if len(att_work_intervals) > 1:
                                    # print("there is more than one interval for that work interval")
                                    late_in_interval = (
                                        work_interval[0],
                                        att_work_intervals[0][0])
                                    overtime_interval = (
                                        work_interval[1],
                                        att_work_intervals[-1][1])
                                    if overtime_interval[1] < overtime_interval[
                                        0]:
                                        overtime = timedelta(hours=0, minutes=0,
                                                             seconds=0)
                                    else:
                                        overtime = overtime_interval[1] - \
                                                   overtime_interval[0]
                                    remain_interval = (
                                        att_work_intervals[0][1],
                                        work_interval[1])
                                    # print'first remain intervals is',remain_interval
                                    for att_work_interval in att_work_intervals:
                                        float_worked_hours += (
                                                                      att_work_interval[
                                                                          1] -
                                                                      att_work_interval[
                                                                          0]).total_seconds() / 3600
                                        # print'float worked hors is', float_worked_hours
                                        if att_work_interval[1] <= \
                                                remain_interval[0]:
                                            continue
                                        if att_work_interval[0] >= \
                                                remain_interval[1]:
                                            break
                                        if remain_interval[0] < \
                                                att_work_interval[0] < \
                                                remain_interval[1]:
                                            diff_intervals.append((
                                                remain_interval[
                                                    0],
                                                att_work_interval[
                                                    0]))
                                            remain_interval = (
                                                att_work_interval[1],
                                                remain_interval[1])
                                    if remain_interval and remain_interval[0] <= \
                                            work_interval[1]:
                                        diff_intervals.append((remain_interval[
                                                                   0],
                                                               work_interval[
                                                                   1]))
                                    ac_sign_in = self._get_float_from_time(
                                        pytz.utc.localize(att_work_intervals[0][
                                                              0]).astimezone(
                                            tz))
                                    ac_sign_out = self._get_float_from_time(
                                        pytz.utc.localize(
                                            att_work_intervals[-1][
                                                1]).astimezone(tz))
                                    ac_sign_out = ac_sign_in + ((
                                                                        att_work_intervals[
                                                                            -1][
                                                                            1] -
                                                                        att_work_intervals[
                                                                            0][
                                                                            0]).total_seconds() / 3600)
                                else:
                                    late_in_interval = (
                                        work_interval[0],
                                        att_work_intervals[0][0])

                                    overtime_interval = (
                                        work_interval[1],
                                        att_work_intervals[-1][1])
                                    if overtime_interval[1] < overtime_interval[
                                        0]:
                                        overtime = timedelta(hours=0, minutes=0,
                                                             seconds=0)
                                        diff_intervals.append((
                                            overtime_interval[
                                                1],
                                            overtime_interval[
                                                0]))
                                    else:
                                        overtime = overtime_interval[1] - \
                                                   overtime_interval[0]
                                    ac_sign_in = self._get_float_from_time(
                                        pytz.utc.localize(att_work_intervals[0][
                                                              0]).astimezone(
                                            tz))
                                    ac_sign_out = self._get_float_from_time(
                                        pytz.utc.localize(att_work_intervals[0][
                                                              1]).astimezone(
                                            tz))
                                    worked_hours = att_work_intervals[0][1] - \
                                                   att_work_intervals[0][0]
                                    float_worked_hours = worked_hours.total_seconds() / 3600
                                    ac_sign_out = ac_sign_in + float_worked_hours
                            else:
                                late_in_interval = []
                                is_predictive_day = bool(
                                    att_sheet.predictive_mode
                                    and predictive_cutoff
                                    and not self.env.context.get('force_actual_attendance')
                                    and day > predictive_cutoff
                                )
                                if is_predictive_day:
                                    planned_interval = work_interval[1] - work_interval[0]
                                    float_worked_hours = planned_interval.total_seconds() / 3600
                                    ac_sign_in = pl_sign_in
                                    ac_sign_out = pl_sign_out
                                    status = ""
                                    note = _("Projected as present for predictive payroll run.")
                                else:
                                    diff_intervals.append(
                                        (work_interval[0], work_interval[1]))
                                    status = "ab"
                            if diff_intervals:
                                for diff_in in diff_intervals:
                                    if leaves:
                                        status = "leave"
                                        diff_clean_intervals = calendar_id.att_interval_without_leaves(
                                            diff_in, leaves)
                                        for diff_clean in diff_clean_intervals:
                                            diff_time += diff_clean[1] - \
                                                         diff_clean[0]
                                    else:
                                        diff_time += diff_in[1] - diff_in[0]
                            if late_in_interval:
                                if late_in_interval[1] < late_in_interval[0]:
                                    late_in = timedelta(hours=0, minutes=0,
                                                        seconds=0)
                                else:
                                    if leaves:
                                        late_clean_intervals = calendar_id.att_interval_without_leaves(
                                            late_in_interval, leaves)
                                        for late_clean in late_clean_intervals:
                                            late_in += late_clean[1] - \
                                                       late_clean[0]
                                    else:
                                        late_in = late_in_interval[1] - \
                                                  late_in_interval[0]
                            float_overtime = overtime.total_seconds() / 3600
                            if float_overtime <= overtime_policy['wd_after']:
                                act_float_overtime = float_overtime = 0
                            else:
                                act_float_overtime = float_overtime
                                float_overtime = float_overtime * \
                                                 overtime_policy[
                                                     'wd_rate']
                            if not self._is_overtime_approved_for_day(emp, day, tz):
                                float_overtime = 0
                                act_float_overtime = 0
                            float_late = late_in.total_seconds() / 3600
                            act_float_late = late_in.total_seconds() / 3600
                            policy_late, late_cnt = policy_id.get_late(
                                float_late,
                                late_cnt)
                            float_diff = diff_time.total_seconds() / 3600
                            if status == 'ab':
                                if not abs_flag:
                                    abs_cnt += 1
                                abs_flag = True

                                act_float_diff = float_diff
                                float_diff = policy_id.get_absence(float_diff,
                                                                   abs_cnt)
                            else:
                                act_float_diff = float_diff
                                float_diff = policy_id.get_diff(float_diff)
                            values = {
                                'date': date,
                                'day': day_str,
                                'pl_sign_in': pl_sign_in,
                                'pl_sign_out': pl_sign_out,
                                'ac_sign_in': ac_sign_in,
                                'ac_sign_out': ac_sign_out,
                                'late_in': policy_late,
                                'act_late_in': act_float_late,
                                'worked_hours': float_worked_hours,
                                # 'worked_hours': (float_worked_hours - 1) if float_worked_hours else 0,
                                'overtime': float_overtime,
                                'act_overtime': act_float_overtime,
                                'diff_time': float_diff,
                                # 'diff_time': float_diff - 1 if float_diff > 0 else 0,
                                'act_diff_time': act_float_diff,
                                # 'act_diff_time': act_float_diff - 1 if act_float_diff > 0 else 0,
                                'status': status,
                                'att_sheet_id': self.id
                            }
                            if att_sheet.employee_id.compute_attendance or status == "leave":
                                att_line.create(values)
                        out_work_intervals = [x for x in attendance_intervals if
                                              x not in reserved_intervals]
                        if out_work_intervals:
                            for att_out in out_work_intervals:
                                overtime = att_out[1] - att_out[0]
                                ac_sign_in = self._get_float_from_time(
                                    pytz.utc.localize(att_out[0]).astimezone(
                                        tz))
                                ac_sign_out = self._get_float_from_time(
                                    pytz.utc.localize(att_out[1]).astimezone(
                                        tz))
                                float_worked_hours = overtime.total_seconds() / 3600
                                ac_sign_out = ac_sign_in + float_worked_hours
                                float_overtime = overtime.total_seconds() / 3600
                                if float_overtime <= overtime_policy[
                                    'wd_after']:
                                    float_overtime = act_float_overtime = 0
                                else:
                                    act_float_overtime = float_overtime
                                    float_overtime = act_float_overtime * \
                                                     overtime_policy['wd_rate']
                                if not self._is_overtime_approved_for_day(emp, day, tz):
                                    float_overtime = 0
                                    act_float_overtime = 0
                                values = {
                                    'date': date,
                                    'day': day_str,
                                    'pl_sign_in': 0,
                                    'pl_sign_out': 0,
                                    'ac_sign_in': ac_sign_in,
                                    'ac_sign_out': ac_sign_out,
                                    'overtime': float_overtime,
                                    'worked_hours': float_worked_hours,
                                    # 'worked_hours': (float_worked_hours - 1) if float_worked_hours else 0,
                                    'act_overtime': act_float_overtime,
                                    'note': _("overtime out of work intervals"),
                                    'att_sheet_id': self.id
                                }
                                if att_sheet.employee_id.compute_attendance:
                                    att_line.create(values)
                else:
                    if attendance_intervals:
                        # print "thats weekend be over time "
                        for attendance_interval in attendance_intervals:
                            overtime = attendance_interval[1] - \
                                       attendance_interval[0]
                            ac_sign_in = pytz.utc.localize(
                                attendance_interval[0]).astimezone(tz)
                            ac_sign_out = pytz.utc.localize(
                                attendance_interval[1]).astimezone(tz)
                            float_overtime = overtime.total_seconds() / 3600
                            if float_overtime <= overtime_policy['we_after']:
                                float_overtime = 0
                                act_float_overtime = 0
                            else:
                                act_float_overtime = float_overtime
                                float_overtime = act_float_overtime * \
                                                 overtime_policy['we_rate']
                            if not self._is_overtime_approved_for_day(emp, day, tz):
                                float_overtime = 0
                                act_float_overtime = 0
                            ac_sign_in = pytz.utc.localize(
                                attendance_interval[0]).astimezone(tz)
                            ac_sign_out = pytz.utc.localize(
                                attendance_interval[1]).astimezone(tz)
                            worked_hours = attendance_interval[1] - \
                                           attendance_interval[0]
                            float_worked_hours = worked_hours.total_seconds() / 3600
                            values = {
                                'date': date,
                                'day': day_str,
                                'ac_sign_in': self._get_float_from_time(
                                    ac_sign_in),
                                'ac_sign_out': self._get_float_from_time(
                                    ac_sign_out),
                                'overtime': float_overtime,
                                'act_overtime': act_float_overtime,
                                'worked_hours': float_worked_hours,
                                # 'worked_hours': (float_worked_hours - 1) if float_worked_hours else 0,
                                'att_sheet_id': self.id,
                                'status': 'weekend',
                                'note': _("working in weekend")
                            }
                            if att_sheet.employee_id.compute_attendance:
                                att_line.create(values)
                    else:
                        values = {
                            'date': date,
                            'day': day_str,
                            'att_sheet_id': self.id,
                            'status': 'weekend',
                            'note': ""
                        }
                        if att_sheet.employee_id.compute_attendance:
                            att_line.create(values)

            # leave_ids = self.env['hr.leave'].search([('employee_id', '=', att_sheet.employee_id.id),
            #                                          ('request_date_from', '>=',att_sheet.date_from),
            #                                          ('request_date_to', '<=', att_sheet.date_to)])

            leave_ids = self.env['hr.leave'].search([('employee_id', '=', att_sheet.employee_id.id),
                                                     ('request_date_from', '<=', att_sheet.date_to),
                                                     ('request_date_to', '>=', att_sheet.date_from),
                                                     ('state', '=', "validate"),
                                                     ])

            for leave in leave_ids:
                # if leave.holiday_status_id.work_entry_type_id.id == self.env.ref('hr_work_entry_contract.work_entry_type_unpaid_leave').id:
                if leave.holiday_status_id.work_entry_type_id.id == self.env.ref(
                        'hr_work_entry_contract.work_entry_type_unpaid_leave').id or not leave.holiday_status_id.is_paid:
                    unpaid_leave += leave.number_of_days_display
                # if leave.holiday_status_id.work_entry_type_id.id == self.env.ref('hr_work_entry_contract.work_entry_type_legal_leave').id:
                if leave.holiday_status_id.is_paid:
                    if leave.holiday_status_id.leave_type == "sick_leave":
                        sick_leave += leave.number_of_days_display
                    elif leave.holiday_status_id.leave_type == "business_leave":
                        business_trip_leave += leave.number_of_days_display
                    else:
                        paid_leave += leave.number_of_days_display

            num_att = 0
            # for line in att_sheet.line_ids:
            #     if not line.status:
            #         num_att += 1
            #     # Custom Condition Of Weekend
            #     if line.status == "weekend":
            #         num_att += 1
            #     # Custom Condition Of Public Holiday
            #     if line.status == "ph":
            #         if att_sheet.employee_id.state != "out_service":
            #             num_att += 1
            att_sheet.num_att = num_att
            att_sheet.unpaid_leave = unpaid_leave
            att_sheet.paid_leave = paid_leave
            att_sheet.sick_leave = sick_leave
            att_sheet.business_trip_leave = business_trip_leave
            att_sheet._refresh_line_overtime_approvals()

    def _collect_carry_forward_deduction(self):
        self.ensure_one()
        if not self.employee_id.compute_attendance:
            self.carry_forward_deduction = 0.0
            self.carry_forward_absence_amount = 0.0
            self.carry_forward_late_amount = 0.0
            self.carry_forward_diff_amount = 0.0
            self.carry_forward_overtime_amount = 0.0
            self.carry_forward_early_checkout_amount = 0.0
            return 0.0

        carry_absence_amount = 0.0
        carry_late_amount = 0.0
        carry_diff_amount = 0.0
        carry_overtime_amount = 0.0
        carry_early_checkout_amount = 0.0
        carry_amount = 0.0
        previous_sheets = self.search([
            ('employee_id', '=', self.employee_id.id),
            ('state', '=', 'done'),
            ('id', '!=', self.id),
            ('predictive_mode', '=', True),
            ('predictive_cutoff_date', '!=', False),
            ('date_to', '<', self.date_from),
            ('carry_forward_settled_sheet_id', '=', False),
        ], order='date_to asc')

        for prev_sheet in previous_sheets:
            if not prev_sheet.predictive_cutoff_date or prev_sheet.predictive_cutoff_date >= prev_sheet.date_to:
                prev_sheet.write({
                    'carry_forward_processed': True,
                    'carry_forward_run_date': fields.Date.context_today(self),
                    'carry_forward_amount': 0.0,
                    'carry_forward_settled_sheet_id': self.id,
                })
                continue

            # Rebuild prior period with actual attendance (no projection) to get true late/absence deductions.
            prev_sheet.with_context(force_actual_attendance=True).get_attendances()
            pending_lines = prev_sheet.line_ids.filtered(
                lambda l: l.date and l.date > prev_sheet.predictive_cutoff_date
            )
            source_absence_amount = sum(pending_lines.mapped('absence_amount'))
            source_late_amount = sum(pending_lines.mapped('late_in_amount'))
            source_diff_amount = sum(pending_lines.mapped('diff_amount'))
            source_early_checkout_amount = sum(pending_lines.mapped(
                'early_check_out_amount')) if 'early_check_out_amount' in pending_lines._fields else 0.0
            if prev_sheet.employee_id.add_overtime:
                source_overtime_amount = sum([v for v in pending_lines.mapped('overtime_amount') if v > 0])
            else:
                source_overtime_amount = 0.0
            source_amount = source_absence_amount + source_late_amount + source_diff_amount + source_early_checkout_amount - source_overtime_amount

            carry_absence_amount += source_absence_amount
            carry_late_amount += source_late_amount
            carry_diff_amount += source_diff_amount
            carry_early_checkout_amount += source_early_checkout_amount
            carry_overtime_amount += source_overtime_amount
            carry_amount += source_amount

            prev_sheet.write({
                'carry_forward_processed': True,
                'carry_forward_run_date': fields.Date.context_today(self),
                'carry_forward_amount': source_amount,
                'carry_forward_settled_sheet_id': self.id,
            })

        carry_absence_amount += (self.opening_carry_absence_amount or 0.0)
        carry_late_amount += (self.opening_carry_late_amount or 0.0)
        carry_diff_amount += (self.opening_carry_diff_amount or 0.0)
        carry_early_checkout_amount += (self.opening_carry_early_checkout_amount or 0.0)
        carry_overtime_amount += (self.opening_carry_overtime_amount or 0.0)
        carry_amount += (self.opening_carry_absence_amount or 0.0)
        carry_amount += (self.opening_carry_late_amount or 0.0)
        carry_amount += (self.opening_carry_diff_amount or 0.0)
        carry_amount += (self.opening_carry_early_checkout_amount or 0.0)
        carry_amount -= (self.opening_carry_overtime_amount or 0.0)

        self.carry_forward_absence_amount = carry_absence_amount
        self.carry_forward_late_amount = carry_late_amount
        self.carry_forward_diff_amount = carry_diff_amount
        self.carry_forward_overtime_amount = carry_overtime_amount
        self.carry_forward_early_checkout_amount = carry_early_checkout_amount
        self.carry_forward_deduction = carry_amount
        return carry_amount

    def action_payslip(self):
        self.ensure_one()
        payslip_id = self.payslip_id
        if not payslip_id:
            payslip_id = self.action_create_payslip()[0]
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': payslip_id.id,
            'views': [(False, 'form')],
        }

    def action_create_payslip(self):
        payslip_obj = self.env['hr.payslip']
        payslips = payslip_obj
        for sheet in self:
            sheet._collect_carry_forward_deduction()
            contracts = sheet.employee_id._get_contracts(sheet.date_from,
                                                         sheet.date_to)
            if not contracts:
                if not sheet.employee_id.contract_id:
                    raise ValidationError(_('There is no active contract for current employee'))
            if sheet.payslip_id:
                raise ValidationError(_('Payslip Has Been Created Before'))
            contract = sheet.employee_id.contract_id
            if not contract:
                contract = self.env['hr.contract'].search(
                    [('employee_id', '=', sheet.employee_id.id), ('state', '=', 'open')], limit=1)
            struct_id = self.env.ref("gs_hr_attendance_sheet.structure_attendance_sheet")
            new_payslip = payslip_obj.new({
                'name': sheet.employee_id.name + 'Payslip',
                'employee_id': sheet.employee_id.id,
                'date_from': sheet.date_from,
                'date_to': sheet.date_to,
                'contract_id': contract.id,
                # 'struct_id': contract.struct_id.id,
                'struct_id': struct_id.id,
                'attendance_sheet_id': sheet.id,
            })
            # new_payslip._onchange_employee()
            payslip_dict = new_payslip._convert_to_write({
                name: new_payslip[name] for name in new_payslip._cache})

            payslip_id = payslip_obj.create(payslip_dict)
            worked_day_lines = self._get_workday_lines()
            payslip_id.worked_days_line_ids = [(0, 0, x) for x in
                                               worked_day_lines]
            payslip_id.compute_sheet()
            payslip_id.is_bool = False
            # payslip_id.gs_onchange_employee()
            # payslip_id.onchange_employee_ref()
            sheet.payslip_id = payslip_id
            payslips += payslip_id
        return payslips

    def _get_workday_lines(self):
        self.ensure_one()

        work_entry_obj = self.env['hr.work.entry.type']
        overtime_work_entry = work_entry_obj.search([('code', '=', 'ATTSHOT')])
        latin_work_entry = work_entry_obj.search([('code', '=', 'ATTSHLI')])
        absence_work_entry = work_entry_obj.search([('code', '=', 'ATTSHAB')])
        difftime_work_entry = work_entry_obj.search([('code', '=', 'ATTSHDT')])
        if not overtime_work_entry:
            raise ValidationError(_(
                'Please Add Work Entry Type For Attendance Sheet Overtime With Code ATTSHOT'))
        if not latin_work_entry:
            raise ValidationError(_(
                'Please Add Work Entry Type For Attendance Sheet Late In With Code ATTSHLI'))
        if not absence_work_entry:
            raise ValidationError(_(
                'Please Add Work Entry Type For Attendance Sheet Absence With Code ATTSHAB'))
        if not difftime_work_entry:
            raise ValidationError(_(
                'Please Add Work Entry Type For Attendance Sheet Diff Time With Code ATTSHDT'))

        overtime = [{
            'name': "Overtime",
            'code': 'OVT',
            'work_entry_type_id': overtime_work_entry[0].id,
            'sequence': 30,
            'number_of_days': self.no_overtime,
            'number_of_hours': self.tot_overtime,
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
        difftime = [{
            'name': "Difference time",
            'code': 'DIFFT',
            'work_entry_type_id': difftime_work_entry[0].id,
            'sequence': 45,
            'number_of_days': self.no_difftime,
            'number_of_hours': self.tot_difftime,
        }]
        worked_days_lines = overtime + late + absence + difftime
        return worked_days_lines

    def create_payslip(self):
        payslips = self.env['hr.payslip']
        for att_sheet in self:
            if att_sheet.payslip_id:
                continue
            from_date = att_sheet.date_from
            to_date = att_sheet.date_to
            employee = att_sheet.employee_id
            slip_data = self.env['hr.payslip'].onchange_employee_id(from_date,
                                                                    to_date,
                                                                    employee.id,
                                                                    contract_id=False)
            contract_id = slip_data['value'].get('contract_id')
            if not contract_id:
                raise exceptions.Warning(
                    'There is No Contracts for %s That covers the period of the Attendance sheet' % employee.name)
            worked_days_line_ids = slip_data['value'].get(
                'worked_days_line_ids')

            overtime = [{
                'name': "Overtime",
                'code': 'OVT',
                'contract_id': contract_id,
                'sequence': 30,
                'number_of_days': att_sheet.no_overtime,
                'number_of_hours': att_sheet.tot_overtime,
            }]
            absence = [{
                'name': "Absence",
                'code': 'ABS',
                'contract_id': contract_id,
                'sequence': 35,
                'number_of_days': att_sheet.no_absence,
                'number_of_hours': att_sheet.tot_absence,
            }]
            late = [{
                'name': "Late In",
                'code': 'LATE',
                'contract_id': contract_id,
                'sequence': 40,
                'number_of_days': att_sheet.no_late,
                'number_of_hours': att_sheet.tot_late,
            }]
            difftime = [{
                'name': "Difference time",
                'code': 'DIFFT',
                'contract_id': contract_id,
                'sequence': 45,
                'number_of_days': att_sheet.no_difftime,
                'number_of_hours': att_sheet.tot_difftime,
            }]
            worked_days_line_ids += overtime + late + absence + difftime

            res = {
                'employee_id': employee.id,
                'name': slip_data['value'].get('name'),
                'struct_id': slip_data['value'].get('struct_id'),
                'contract_id': contract_id,
                'input_line_ids': [(0, 0, x) for x in
                                   slip_data['value'].get('input_line_ids')],
                'worked_days_line_ids': [(0, 0, x) for x in
                                         worked_days_line_ids],
                'date_from': from_date,
                'date_to': to_date,
            }
            new_payslip = self.env['hr.payslip'].create(res)
            att_sheet.payslip_id = new_payslip
            payslips += new_payslip
        return payslips


class AttendanceSheetLine(models.Model):
    _name = 'attendance.sheet.line'

    state = fields.Selection([
        ('draft', 'Draft'),
        ('sum', 'Summary'),
        ('confirm', 'Confirmed'),
        ('done', 'Approved')], related='att_sheet_id.state', store=True, )

    date = fields.Date("Date")
    day = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday')
    ], 'Day of Week', required=True, index=True, )
    att_sheet_id = fields.Many2one(comodel_name='attendance.sheet',
                                   ondelete="cascade",
                                   string='Attendance Sheet', readonly=True)
    employee_id = fields.Many2one(related='att_sheet_id.employee_id',
                                  string='Employee')
    pl_sign_in = fields.Float("Planned sign in", readonly=True)
    pl_sign_out = fields.Float("Planned sign out", readonly=True)
    worked_hours = fields.Float("Worked Hours", readonly=True)
    ac_sign_in = fields.Float("Actual sign in", readonly=True)
    ac_sign_out = fields.Float("Actual sign out", readonly=True)
    day_amount = fields.Float("Day Amount", compute="_compute_day_amount", store=True)
    overtime = fields.Float("Overtime", readonly=True)
    act_overtime = fields.Float("Actual Overtime", readonly=True)
    overtime_amount = fields.Float("Overtime Amount", compute="_compute_overtime_amount", store=True)
    overtime_approval_state = fields.Selection([
        ('not_required', 'Not Required'),
        ('pending', 'Pending HR Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string="Overtime Approval", default='not_required', copy=False)
    approved_overtime_hours = fields.Float(
        string="Approved Overtime Hours",
        compute="_compute_approved_overtime",
        store=True,
    )
    approved_overtime_amount = fields.Float(
        string="Approved Overtime Amount",
        compute="_compute_approved_overtime",
        store=True,
    )
    late_in = fields.Float("Late In", readonly=True)
    late_in_amount = fields.Float("Late In Amount", compute="_compute_late_in_amount", store=True)
    absence_amount = fields.Float("Absence Amount", compute="_compute_absence_amount", store=True)
    diff_time = fields.Float("Diff Time",
                             help="Diffrence between the working time and attendance time(s) ",
                             readonly=True)
    diff_amount = fields.Float("Diff Amount", compute="_compute_diff_amount", store=True)
    act_late_in = fields.Float("Actual Late In", readonly=True)
    act_diff_time = fields.Float("Actual Diff Time",
                                 help="Diffrence between the working time and attendance time(s) ",
                                 readonly=True)
    status = fields.Selection(string="Status",
                              selection=[('ab', 'Absence'),
                                         ('weekend', 'Week End'),
                                         ('ph', 'Public Holiday'),
                                         ('leave', 'Leave'), ],
                              required=False, readonly=True)
    note = fields.Text("Note", readonly=True)

    @api.depends('overtime', 'overtime_amount', 'overtime_approval_state')
    def _compute_approved_overtime(self):
        for line in self:
            if line.overtime_approval_state == 'approved' and line.overtime > 0:
                line.approved_overtime_hours = line.overtime
                line.approved_overtime_amount = line.overtime_amount
            else:
                line.approved_overtime_hours = 0.0
                line.approved_overtime_amount = 0.0

    def action_approve_overtime_line(self):
        for line in self:
            if line.overtime <= 0:
                raise UserError(_("No overtime found on this day."))
            line.overtime_approval_state = 'approved'

    def action_reject_overtime_line(self):
        for line in self:
            if line.overtime <= 0:
                raise UserError(_("No overtime found on this day."))
            line.overtime_approval_state = 'rejected'

    def _get_month_days_divisor(self, the_date):
        return 30

    @api.depends("employee_id",
                 "date",
                 "pl_sign_in",
                 "pl_sign_out",
                 "employee_id.contract_id",
                 "employee_id.contract_id.gross_amount",
                 )
    def _compute_day_amount(self):
        for line in self:
            if line.employee_id and line.employee_id.contract_id and line.date:
                start_of_month = date_utils.start_of(line.date, 'month')
                end_of_month = date_utils.end_of(line.date, 'month')
                month_days = self._get_month_days_divisor(line.date)
                net_salary_amount = line.employee_id.contract_id.gross_amount
                day_amount = net_salary_amount / month_days
                line.day_amount = day_amount
            else:
                line.day_amount = 0

    @api.depends("employee_id",
                 "late_in",
                 "date",
                 "pl_sign_in",
                 "pl_sign_out",
                 "employee_id.contract_id",
                 "employee_id.contract_id.gross_amount",
                 "att_sheet_id",
                 "att_sheet_id.att_policy_id",
                 "att_sheet_id.att_policy_id.late_rule_id",
                 )
    def _compute_late_in_amount(self):
        for line in self:
            if line.employee_id and line.date and line.late_in > 0:
                start_of_month = date_utils.start_of(line.date, 'month')
                end_of_month = date_utils.end_of(line.date, 'month')
                month_days = self._get_month_days_divisor(line.date)
                net_salary_amount = line.employee_id.contract_id.gross_amount
                day_amount = net_salary_amount / month_days
                # hours_per_day = line.pl_sign_out - line.pl_sign_in
                hours_per_day = line.employee_id.contract_id.resource_calendar_id.hours_per_day
                line.late_in_amount = (line.late_in * day_amount) / hours_per_day if hours_per_day > 0 else 0
            else:
                line.late_in_amount = 0

                # late_in_policy = line.att_sheet_id.att_policy_id.late_rule_id if (line.att_sheet_id.att_policy_id and line.att_sheet_id.att_policy_id.late_rule_id) else False
                # if late_in_policy:
                #     late_in_line = late_in_policy.line_ids[0]
                #     minutes = late_in_line.time
                #     l_type = late_in_line.type
                #     rate = late_in_line.rate
                #     amount = late_in_line.amount
                #     if l_type == "fix":
                #         line.late_in_amount = (line.late_in * 60 * amount) / minutes
                #     elif l_type == "rate":
                #         line.late_in_amount = (line.late_in * day_amount) / hours_per_day if hours_per_day > 0 else 0
                #     else:
                #         line.late_in_amount = 0
                # else:
                #     line.late_in_amount = 0

    @api.depends("employee_id",
                 "status",
                 "date",
                 "pl_sign_in",
                 "pl_sign_out",
                 "employee_id.contract_id",
                 "employee_id.contract_id.gross_amount",
                 "att_sheet_id",
                 )
    def _compute_absence_amount(self):
        for line in self:
            start_of_month = date_utils.start_of(line.date, 'month')
            end_of_month = date_utils.end_of(line.date, 'month')
            month_days = self._get_month_days_divisor(line.date)
            net_salary_amount = line.employee_id.contract_id.gross_amount
            day_amount = net_salary_amount / month_days
            if line.status == "ab":
                line.absence_amount = day_amount
            else:
                line.absence_amount = 0

    @api.depends("overtime",
                 "employee_id",
                 "status",
                 "date",
                 "pl_sign_in",
                 "pl_sign_out",
                 "worked_hours",
                 "employee_id.contract_id",
                 "employee_id.contract_id.gross_amount",
                 )
    def _compute_overtime_amount(self):
        for line in self:
            # if line.overtime > 0:
            if line.worked_hours > 0:
                start_of_month = date_utils.start_of(line.date, 'month')
                end_of_month = date_utils.end_of(line.date, 'month')
                month_days = self._get_month_days_divisor(line.date)
                # net_salary_amount = line.employee_id.contract_id.gross_amount
                net_salary_amount = line.employee_id.contract_id.wage
                day_amount = net_salary_amount / month_days
                # hours_per_day = line.pl_sign_out - line.pl_sign_in
                hours_per_day = line.employee_id.contract_id.resource_calendar_id.hours_per_day

                if line.pl_sign_in > 0 and line.ac_sign_in > 0:
                    line.overtime_amount = (((
                                                     line.worked_hours - 1) - line.employee_id.resource_calendar_id.hours_per_day) * 1.5 * day_amount) / hours_per_day
                elif line.pl_sign_in == 0 and line.ac_sign_in > 0:
                    line.overtime_amount = ((line.worked_hours - 1) * 1.5 * day_amount) / hours_per_day

                # line.overtime_amount = (line.overtime * 1.5 * day_amount) / hours_per_day
            else:
                line.overtime_amount = 0

    @api.depends("act_diff_time",
                 "day_amount",
                 "employee_id",
                 "status",
                 "date",
                 "pl_sign_in",
                 "pl_sign_out",
                 )
    def _compute_diff_amount(self):
        for line in self:
            if line.act_diff_time > 0:
                day_amount = line.day_amount
                # hours_per_day = line.pl_sign_out - line.pl_sign_in
                hours_per_day = line.employee_id.contract_id.resource_calendar_id.hours_per_day
                line.diff_amount = (line.act_diff_time * day_amount) / hours_per_day
            else:
                line.diff_amount = 0