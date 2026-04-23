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


import pytz
from datetime import datetime, date, timedelta, time
from dateutil.relativedelta import relativedelta
from odoo import models, fields, tools, api, exceptions, _
from odoo.exceptions import UserError, ValidationError
import babel
import inspect
from operator import itemgetter
import logging
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
TIME_FORMAT = "%H:%M:%S"


class AttendanceSheetBatch(models.Model):
    _name = 'attendance.sheet.batch'
    name = fields.Char("name")
    department_id = fields.Many2one('hr.department', 'Department Name',
                                    required=False, check_company=True)
    date_from = fields.Date(string='Date From', readonly=True, required=True,
                            default=lambda self: fields.Date.to_string(
                                date.today().replace(day=1)), )
    date_to = fields.Date(string='Date To', readonly=True, required=True,
                          default=lambda self: fields.Date.to_string(
                              (datetime.now() + relativedelta(months=+1, day=1,
                                                              days=-1)).date()))
    att_sheet_ids = fields.One2many(comodel_name='attendance.sheet',
                                    string='Attendance Sheets',
                                    inverse_name='batch_id')
    payslip_batch_id = fields.Many2one(comodel_name='hr.payslip.run',
                                       string='Payslip Batch')
    predictive_mode = fields.Boolean(
        string='Predictive Payroll',
        default=True,
        help='If enabled, future days after cutoff are projected as present while generating attendance sheets.',
    )
    predictive_cutoff_date = fields.Date(
        string='Predictive Cutoff Date',
        default=fields.Date.context_today,
        help='All working days after this date are projected as present with no late/absence deduction.',
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('att_gen', 'Attendance Sheets Generated'),
        ('att_sub', 'Attendance Sheets Submitted'),
        ('done', 'Close')], default='draft', track_visibility='onchange',
        string='Status', required=True, readonly=True, index=True, )

    type = fields.Selection([
        ('department', 'By Department'),
        ('company', 'By Company')], default='department', track_visibility='onchange',
        string='BY', required=True)

    company_id = fields.Many2one('res.company', string='Company', tracking=True, default=lambda self: self.env.company, required=True)

    @api.onchange('type', 'department_id','company_id', 'date_from', 'date_to')
    def onchange_employee(self):
        if self.type == 'department':
            if (not self.department_id) or (not self.date_from) or (
                    not self.date_to):
                return
            department = self.department_id
            date_from = self.date_from
            # ttyme = datetime.combine(fields.Date.from_string(date_from), time.min)
            ttyme = datetime.combine(fields.Date.from_string(self.date_to), time.min)
            locale = self.env.context.get('lang', 'en_US')
            self.name = _('Attendance Batch of %s  Department for %s') % (
                department.name,
                tools.ustr(
                    babel.dates.format_date(date=ttyme,
                                            format='MMMM-y',
                                            locale=locale)))

        if self.type == 'company':
            if (not self.company_id) or (not self.date_from) or (
                    not self.date_to):
                return
            company = self.company_id
            date_from = self.date_from
            # ttyme = datetime.combine(fields.Date.from_string(date_from), time.min)
            ttyme = datetime.combine(fields.Date.from_string(self.date_to), time.min)
            locale = self.env.context.get('lang', 'en_US')
            self.name = _('Attendance Batch of %s  Company for %s') % (
                company.name,
                tools.ustr(
                    babel.dates.format_date(date=ttyme,
                                            format='MMMM-y',
                                            locale=locale)))

    def action_done(self):
        for batch in self:
            payslip_batch_name = batch.name.replace("Attendance", "Payslip")
            payslip_batch_id = self.env["hr.payslip.run"].sudo().create({
                "name": payslip_batch_name or batch.name,
                "date_start": batch.date_from,
                "date_end": batch.date_to,
            })
            if batch.state != "att_sub":
                continue
            for sheet in batch.att_sheet_ids:
                if sheet.state == 'confirm':
                    sheet.action_approve()
                    payslip_id = self.env["hr.payslip"].search([("attendance_sheet_id", "=", sheet.id)], limit=1)
                    if payslip_id and payslip_batch_id:
                        payslip_id.payslip_run_id = payslip_batch_id.id
            batch_info = dir(payslip_batch_id)
            if "_generate_batch_payslip_data_summary" in batch_info:
                payslip_batch_id._generate_batch_payslip_data_summary()
            batch.payslip_batch_id = payslip_batch_id.id
            batch.write({'state': 'done'})

    def action_att_gen(self):
        return self.write({'state': 'att_gen'})

    def gen_att_sheet(self):

        att_sheets = self.env['attendance.sheet']
        att_sheet_obj = self.env['attendance.sheet']
        for batch in self:
            from_date = batch.date_from
            to_date = batch.date_to
            if self.type == 'department':
                employee_ids = self.env['hr.employee'].search(
                    [('department_id', '=', batch.department_id.id)])

                if not employee_ids:
                    raise UserError(_("There is no  Employees In This Department"))
                for employee in employee_ids:

                    contract_ids = employee._get_contracts(from_date, to_date)

                    # if not contract_ids:
                    #     raise UserError(_(
                    #         "There is no  Running contracts for :%s " % employee.name))

                    # Add Custom Condition
                    if not employee.contract_id or (employee.contract_id.state != "open"):
                        raise UserError(_(
                            "There is no  Running contracts for :%s " % employee.name))
                    else:
                        new_sheet = att_sheet_obj.new({
                            'employee_id': employee.id,
                            'date_from': from_date,
                            'date_to': to_date,
                            'batch_id':batch.id,
                            'predictive_mode': batch.predictive_mode,
                            'predictive_cutoff_date': batch.predictive_cutoff_date,
                        })
                        new_sheet.onchange_employee()
                        values = att_sheet_obj._convert_to_write(new_sheet._cache)
                        att_sheet_id = att_sheet_obj.create(values)


                        att_sheet_id.get_attendances()
                        att_sheets += att_sheet_id
            if self.type == 'company':
                employee_ids = self.env['hr.employee'].search(
                    [('company_id', '=', batch.company_id.id)])

                if not employee_ids:
                    raise UserError(_("There is no  Employees In This Company"))
                for employee in employee_ids:

                    contract_ids = employee._get_contracts(from_date, to_date)

                    # if not contract_ids:
                    #     raise UserError(_(
                    #         "There is no  Running contracts for :%s " % employee.name))

                    # Add Custom Condition
                    if not employee.contract_id or (employee.contract_id.state != "open"):
                        raise UserError(_(
                            "There is no  Running contracts for :%s " % employee.name))
                    else:

                        new_sheet = att_sheet_obj.new({
                            'employee_id': employee.id,
                            'date_from': from_date,
                            'date_to': to_date,
                            'batch_id':batch.id,
                            'predictive_mode': batch.predictive_mode,
                            'predictive_cutoff_date': batch.predictive_cutoff_date,
                        })
                        new_sheet.onchange_employee()
                        values = att_sheet_obj._convert_to_write(new_sheet._cache)
                        att_sheet_id = att_sheet_obj.create(values)


                        att_sheet_id.get_attendances()
                        att_sheets += att_sheet_id
            batch.action_att_gen()

    def submit_att_sheet(self):
        for batch in self:
            if batch.state != "att_gen":
                continue
            for sheet in batch.att_sheet_ids:
                if sheet.state == 'draft':
                    sheet.action_confirm()

            batch.write({'state': 'att_sub'})

    def unlink(self):
        for batch in self:
            if batch.att_sheet_ids:
                batch.att_sheet_ids.unlink()
        return super().unlink()
