from datetime import timedelta

from odoo import api, fields, models
from odoo.tools import date_utils


class HrLeaveDashboardPdf(models.AbstractModel):
    _name = 'report.de_hr_workspace_leave_management.hr_leave_report'
    _description = 'Workspace Leave Dashboard Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        today = fields.Date.today()
        duration = data.get('duration', 'today')
        if duration == 'this_month':
            start_date = date_utils.start_of(today, 'month')
            end_date = date_utils.end_of(today, 'month') - timedelta(days=1)
        elif duration == 'this_year':
            start_date = date_utils.start_of(today, 'year')
            end_date = date_utils.end_of(today, 'year') - timedelta(days=1)
        elif duration == 'this_week':
            start_date = date_utils.start_of(today, 'week')
            end_date = date_utils.end_of(today, 'week')
        else:
            start_date = today
            end_date = today

        leave_types = self.env['hr.leave.type'].sudo().search([])
        employees = self.env['hr.employee'].sudo().search([('active', '=', True)])
        filtered_list = []
        for emp in employees:
            for leave_type in leave_types:
                allocations = self.env['hr.leave.allocation'].sudo().search([
                    ('employee_id', '=', emp.id),
                    ('holiday_status_id', '=', leave_type.id),
                    ('state', '=', 'validate'),
                ])
                allocated_days = sum(allocations.mapped('number_of_days'))
                leaves = self.env['hr.leave'].sudo().search([
                    ('employee_id', '=', emp.id),
                    ('holiday_status_id', '=', leave_type.id),
                    ('state', '=', 'validate'),
                    ('request_date_from', '>=', start_date),
                    ('request_date_to', '<=', end_date),
                ])
                taken_days = sum(leaves.mapped('number_of_days'))
                if allocated_days or taken_days:
                    filtered_list.append({
                        'emp_id': emp.id,
                        'emp_name': emp.name,
                        'leave_type': leave_type.name,
                        'allocated_days': allocated_days,
                        'taken_days': taken_days,
                        'balance_days': allocated_days - taken_days,
                    })

        return {'duration': duration, 'filtered_list': filtered_list}
