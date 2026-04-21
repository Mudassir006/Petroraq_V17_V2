# -*- coding: utf-8 -*-

from odoo import http, fields
from odoo.http import request
from odoo.exceptions import ValidationError, UserError
from datetime import datetime
import base64


class LeaveRequestTemplate(http.Controller):

    @http.route('/leave_request', auth='user', type='http')
    def display_leave_request_form(self, **kw):
        current_user = request.env.user
        current_employee_id = request.env["hr.employee"].sudo().search([("user_id", "=", current_user.id)], limit=1)
        email = current_employee_id.work_email
        return http.request.render('de_hr_workspace_timeoff.leave_request_template', {
            "current_employee_id": current_employee_id,
            "employee_email": email,
            "company_name": current_employee_id.company_id.name,
            "form_values": {},
            "error_message": False,
        })

    @http.route('/leave_request/create', type='http', auth="user")
    def leave_created(self, **kw):
        employee_id = int(kw.get('employee_id'))
        leave_type_id = int(kw.get('leave_type_id'))
        str_date_from = kw.get('date_from')
        str_date_to = kw.get('date_to')
        date_from = datetime.strptime(str_date_from, "%Y-%m-%d").date()
        date_to = datetime.strptime(str_date_to, "%Y-%m-%d").date()
        employee_obj = request.env['hr.employee'].sudo().browse(employee_id)
        leave_type_obj = request.env['hr.leave.type'].sudo().browse(leave_type_id)
        employee_manager_id = employee_obj.parent_id
        # hr_supervisor_group_ids = [request.env.ref('hr_holidays.group_hr_holidays_user').id]
        hr_supervisor_group_ids = [request.env.ref('pr_hr_holidays.custom_group_hr_holidays_supervisor').id]
        hr_manager_group_ids = [request.env.ref('hr_holidays.group_hr_holidays_manager').id]
        hr_supervisor_ids = request.env['res.users'].sudo().search([('groups_id', 'in', hr_supervisor_group_ids)])
        hr_manager_ids = request.env['res.users'].sudo().search([('groups_id', 'in', hr_manager_group_ids)])
        notes = kw.get('message') if kw.get('message') else False
        try:
            leave_request_id = request.env['pr.hr.leave.request'].sudo().create({
                'employee_id': employee_id,
                'leave_type_id': leave_type_id,
                'date_from': date_from,
                'date_to': date_to,
                'note': notes if notes else False,
                'company_id': employee_obj.company_id.id if employee_obj.company_id else request.env.company.id,
                'employee_manager_id': employee_manager_id.id if employee_manager_id else False,
                'hr_supervisor_ids': hr_supervisor_ids.ids if hr_supervisor_ids else False,
                'hr_manager_ids': hr_manager_ids.ids if hr_manager_ids else False,
            })
        except (ValidationError, UserError) as ex:
            current_user = request.env.user
            current_employee_id = request.env["hr.employee"].sudo().search([("user_id", "=", current_user.id)], limit=1)
            return http.request.render('de_hr_workspace_timeoff.leave_request_template', {
                "current_employee_id": current_employee_id,
                "employee_email": current_employee_id.work_email,
                "company_name": current_employee_id.company_id.name,
                "form_values": kw,
                "error_message": str(ex),
            })
        if leave_request_id:
            # Create Attachments And Add Them To Leave Request
            attachment_ids = []
            attachment_list = request.httprequest.files.getlist('attachment_ids')
            for att in attachment_list:
                if kw.get('attachment_ids'):
                    attachments = {
                        'res_name': att.filename,
                        'res_model': 'pr.hr.leave.request',
                        'res_id': leave_request_id.sudo().id,
                        'datas': base64.encodebytes(att.read()),
                        'type': 'binary',
                        'name': att.filename,
                    }
                    attachment_obj = http.request.env['ir.attachment']
                    att_record = attachment_obj.sudo().create(attachments)
                    attachment_ids.append(att_record.id)
            # if attachment_ids:
            #     leave_request_id.update({'attachment_ids': [(6, 0, attachment_ids)]})
            leave_request_id.sudo()._send_manager_email()
            return http.request.render('de_hr_workspace_timeoff.thanks_template')
        else:
            print(kw, 'False')
            return False

    @http.route(['/get_dashboard_data'], type='json', auth="user")
    def get_dashboard_data(self):
        today = fields.Date.today()
        current_user = request.env.user
        current_employee_id = request.env["hr.employee"].sudo().search(
            [("user_id", "=", current_user.id), ("active", "=", True)], limit=1)
        summary = []
        if current_employee_id:
            leave_type_ids = request.env["hr.leave.type"].sudo().search(
                ["|", ("company_id", "=", request.env.company.id), ("company_id", "=", False)])
            if leave_type_ids:
                for leave_type in leave_type_ids:
                    # region [Allocations]
                    if leave_type.requires_allocation == "yes":
                        allocation_ids = request.env["hr.leave.allocation"].sudo().search(
                            [("employee_id", "=", current_employee_id.id),
                             ("holiday_status_id", "=", leave_type.id), ("state", "=", "validate")])
                        if allocation_ids:
                            allocation_days = round(sum(allocation_ids.mapped("number_of_days")), 2)
                        else:
                            allocation_days = 0
                    else:
                        if leave_type.leave_type == "sick_leave":
                            allocation_days = 30
                        else:
                            allocation_days = 0
                    # endregion [Allocations]

                    # region [Leaves]
                    leave_ids = request.env["hr.leave"].sudo().search([("employee_id", "=", current_employee_id.id),
                                                                    ("holiday_status_id", "=", leave_type.id),
                                                                    ("state", "=", "validate")])
                    if leave_ids:
                        leave_days = round(sum(leave_ids.mapped("number_of_days")), 2)
                    else:
                        leave_days = 0
                    # endregion [Leaves]
                    # if allocation_days > 0 or leave_days > 0:
                    if allocation_days > 0 :
                        summary.append({
                            "leave_name": leave_type.name,
                            "allocation_days": allocation_days,
                            "leave_days": leave_days,
                            "requires_allocation": leave_type.requires_allocation if leave_type.leave_type != "sick_leave" else "yes",
                        })

                    # summary = {
                    #     'annual': self.search_count([('holiday_status_id.name', '=', 'Annual Leave')]),
                    #     'sick': self.search_count([('holiday_status_id.name', '=', 'Sick Leave')]),
                    #     'other': self.search_count([('holiday_status_id.name', '=', 'Other Leave')]),
                    #     'pending': self.search_count([('state', '=', 'confirm')]),
                    # }

            leaves_history = request.env["hr.leave"].sudo().search([
                ('employee_id', '=', current_employee_id.id)
            ], limit=5, order='request_date_from asc')

            all_leaves = [{
                'employee': l.employee_id.name,
                'leave_type': l.holiday_status_id.name,
                'from': l.request_date_from.strftime('%d/%m/%Y'),
                'to': l.request_date_to.strftime('%d/%m/%Y'),
                'days': l.number_of_days_display,
            } for l in leaves_history]

            pending = [{
                'employee': current_employee_id.name,
                'leave_type': l.leave_type_id.name,
                'from': l.date_from.strftime('%d/%m/%Y'),
                'to': l.date_to.strftime('%d/%m/%Y'),
                'days': (l.date_to - l.date_from).days + 1,
                'status': l.state,
            } for l in request.env["pr.hr.leave.request"].sudo().search([("employee_id", "=", current_employee_id.id), ('state', 'in', ['draft', 'manager_approve', 'hr_supervisor'])], limit=5)]
            # } for l in request.env["hr.leave"].sudo().search([('state', 'in', ['draft', 'confirm', 'validate1'])], limit=5)]

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
                'all_leaves': all_leaves,
                'pending': pending,
                'chart': chart_data,
            }
        return None