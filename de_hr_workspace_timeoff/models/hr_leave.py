from odoo import models, fields, api
from datetime import date

class HrLeave(models.Model):
    _inherit = 'hr.leave'

    @api.model
    def get_dashboard_data(self):
        today = fields.Date.today()
        current_user = self.env.user
        current_employee_id = self.env["hr.employee"].sudo().search([("user_id", "=", current_user.id), ("active", "=", True)], limit=1)
        summary = []
        if current_employee_id:
            leave_type_ids = self.env["hr.leave.type"].sudo().search(["|", ("company_id", "=", self.env.company.id), ("company_id", "=", False)])
            if leave_type_ids:
                for leave_type in leave_type_ids:
                    # region [Allocations]
                    if leave_type.requires_allocation == "yes":
                        allocation_ids = self.env["hr.leave.allocation"].sudo().search([("employee_id", "=", current_employee_id.id),
                                                                                        ("holiday_status_id", "=", leave_type.id), ("state", "=", "validate")])
                        if allocation_ids:
                            allocation_days = sum(allocation_ids.mapped("number_of_days"))
                        else:
                            allocation_days = 0
                    else:
                        if leave_type.leave_type == "sick_leave":
                            allocation_days = 90
                        else:
                            allocation_days = 0
                    # endregion [Allocations]

                    # region [Leaves]
                    leave_ids = self.env["hr.leave"].sudo().search([("employee_id", "=", current_employee_id.id),
                                                                                        ("holiday_status_id", "=", leave_type.id), ("state", "=", "validate")])
                    if leave_ids:
                        leave_days = sum(leave_ids.mapped("number_of_days"))
                    else:
                        leave_days = 0
                    # endregion [Leaves]
                    summary.append({
                        "leave_name": leave_type.name,
                        "allocation_days": allocation_days,
                        "leave_days": leave_days,
                        "requires_allocation": leave_type.requires_allocation if leave_type.leave_type !="sick_leave" else "yes",
                    })

                    # summary = {
                    #     'annual': self.search_count([('holiday_status_id.name', '=', 'Annual Leave')]),
                    #     'sick': self.search_count([('holiday_status_id.name', '=', 'Sick Leave')]),
                    #     'other': self.search_count([('holiday_status_id.name', '=', 'Other Leave')]),
                    #     'pending': self.search_count([('state', '=', 'confirm')]),
                    # }

            upcoming_leaves = self.env["hr.leave"].sudo().search([
                ('state', '=', 'validate'),
                ('request_date_from', '>=', today),
                ('employee_id', '=', current_employee_id.id)
            ], limit=5, order='request_date_from asc')

            upcoming = [{
                'employee': l.employee_id.name,
                'leave_type': l.holiday_status_id.name,
                'from': l.request_date_from.strftime('%d/%m/%Y'),
                'to': l.request_date_to.strftime('%d/%m/%Y'),
                'days': l.number_of_days_display,
            } for l in upcoming_leaves]

            pending = [{
                'employee': l.employee_id.name,
                'leave_type': l.holiday_status_id.name,
                'from': l.request_date_from.strftime('%d/%m/%Y'),
                'to': l.request_date_to.strftime('%d/%m/%Y'),
                'days': l.number_of_days_display,
                'status': l.state,
            } for l in self.search([('state', '=', 'confirm')], limit=5)]

            chart_data = {
                'labels': ['7 Dec', '8 Dec', '9 Dec', '10 Dec', '11 Dec', '12 Dec', '13 Dec'],
                'datasets': [
                    {
                        'label': 'Emergency Leave',
                        'data': [4, 3, 2, 1, 5, 2, 3],
                        'backgroundColor': 'rgba(255, 99, 132, 0.6)',
                    },
                    {
                        'label': 'Annual Leave',
                        'data': [6, 5, 4, 3, 7, 5, 4],
                        'backgroundColor': 'rgba(54, 162, 235, 0.6)',
                    },
                ]
            }

            return {
                'summary': summary,
                'upcoming': upcoming,
                'pending': pending,
                'chart': chart_data,
            }
        return None

    @api.model
    def get_taken_leaves(self):
        current_user = self.env.user
        current_employee_id = self.env["hr.employee"].sudo().search(
            [("user_id", "=", current_user.id), ("active", "=", True)], limit=1)
        taken_leaves = {}
        if current_employee_id:
            leave_type_ids = self.env["hr.leave.type"].sudo().search(
                ["|", ("company_id", "=", self.env.company.id), ("company_id", "=", False)])
            if leave_type_ids:
                for leave_type in leave_type_ids:
                    leave_ids = self.env["hr.leave"].sudo().search([("employee_id", "=", current_employee_id.id),
                                                                    ("holiday_status_id", "=", leave_type.id),
                                                                    ("state", "=", "validate")])
                    if leave_ids:
                        for leave in leave_ids:
                            if leave.holiday_status_id.name not in taken_leaves:
                                taken_leaves[leave.holiday_status_id.name] = leave.number_of_days
                            else:
                                taken_leaves[leave.holiday_status_id.name] += leave.number_of_days
                    else:
                        taken_leaves[leave_type.name] = 0
        return taken_leaves

    @api.model
    def get_our_base_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return base_url

