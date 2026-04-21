from odoo import models, fields, tools, api, exceptions, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import date_utils


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _get_workday_lines(self):
        for rec in self:
            if not rec.is_bool:
                if rec.attendance_sheet_id:
                    rec.attendance_sheet_id._mark_late_checkins_as_absent()
                self.ensure_one()
                rec.worked_days_line_ids = [(5, 0, 0)]
                work_entry_obj = self.env['hr.work.entry.type']
                overtime_work_entry = work_entry_obj.search([('code', '=', 'ATTSHOT')])
                latin_work_entry = work_entry_obj.search([('code', '=', 'ATTSHLI')])
                early_co_work_entry = work_entry_obj.search([('code', '=', 'ATTSHECO')])
                absence_work_entry = work_entry_obj.search([('code', '=', 'ATTSHAB')])
                difftime_work_entry = work_entry_obj.search([('code', '=', 'ATTSHDT')])
                total_unpaid_leave_hours = rec.attendance_sheet_id.unpaid_leave * rec.contract_id.resource_calendar_id.hours_per_day
                total_paid_leave_hours = rec.attendance_sheet_id.paid_leave * rec.contract_id.resource_calendar_id.hours_per_day
                total_num_att_hours = rec.attendance_sheet_id.num_att * rec.contract_id.resource_calendar_id.hours_per_day
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
                approved_overtime_hours = rec.attendance_sheet_id.approved_overtime_hours or 0.0
                overtime = []
                if approved_overtime_hours > 0:
                    overtime = [{
                        'name': "Overtime",
                        'code': 'OVT',
                        'work_entry_type_id': overtime_work_entry[0].id,
                        'sequence': 30,
                        'number_of_days': approved_overtime_hours / rec.employee_id.contract_id.resource_calendar_id.hours_per_day,
                        'number_of_hours': approved_overtime_hours,
                        'amount': (rec.attendance_sheet_id.approved_overtime_amount + rec.attendance_sheet_id.carry_forward_overtime_amount) if rec.employee_id.add_overtime else 0.0,
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
                        'amount': rec.attendance_sheet_id.tot_absence_amount + weekend_amount + rec.attendance_sheet_id.carry_forward_absence_amount,
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

                early_check_out = [{
                    'name': "Early Check Out",
                    'code': 'ECO',
                    'work_entry_type_id': early_co_work_entry[0].id,
                    'sequence': 40,
                    'number_of_days': rec.attendance_sheet_id.no_early_checkout,
                    'number_of_hours': rec.attendance_sheet_id.tot_early_checkout,
                    'amount': rec.attendance_sheet_id.tot_early_checkout_amount + rec.attendance_sheet_id.carry_forward_early_checkout_amount,
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
                # worked_days_lines = att + paid + unpaid + overtime + late + early_check_out + absence + difftime
                worked_days_lines = att + paid + unpaid + overtime + late + early_check_out + absence
                rec.worked_days_line_ids = [(0, 0, x) for x in
                                            worked_days_lines]
                rec.is_bool = True
                rec.compute_sheet()