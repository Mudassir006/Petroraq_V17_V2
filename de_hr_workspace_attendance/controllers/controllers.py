# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from datetime import datetime
from dateutil.relativedelta import relativedelta
import base64
import logging
logger = logging.getLogger(__name__)


class ShortageRequestTemplate(http.Controller):

    @http.route('/shortage_request', auth='user', type='http')
    def display_shortage_request_form(self, **kw):
        current_user = request.env.user
        current_employee_id = request.env["hr.employee"].sudo().search([("user_id", "=", current_user.id)], limit=1)
        email = current_employee_id.work_email
        shortage_text = ""
        check_in = kw.get("check_in")
        check_out = kw.get("check_out")
        shortage_text = kw.get("shortage_text")
        if shortage_text:
            shortage_text = shortage_text
        else:
            shortage_text = ""
        shortage_date = datetime.strptime(check_in , "%Y-%m-%d %H:%M:%S").date()
        return http.request.render('de_hr_workspace_attendance.shortage_request_template', {
            "current_employee_id": current_employee_id,
            "employee_email": email,
            "check_in": (datetime.strptime(check_in , "%Y-%m-%d %H:%M:%S")) + relativedelta(hours=3) if check_in else False,
            "check_out": (datetime.strptime(check_out , "%Y-%m-%d %H:%M:%S")) + relativedelta(hours=3) if check_out else False,
            "shortage_text": shortage_text,
            "shortage_date": shortage_date,
        })

    @http.route('/shortage_request/create', type='http', auth="user")
    def contact_created(self, **kw):
        # logger.warning(
        #     f"{kw.get('employee_id')} -> employee shortage request"
        # )
        # print(kw.get('employee_id'), "employee shortage request")
        employee_id = int(kw.get('employee_id'))
        str_date = kw.get('date')
        str_check_in = kw.get('checkin')
        if len(str_check_in) == 16:  # If no seconds part is present
            str_check_in += ':00'
        str_check_out = kw.get('checkout')
        if len(str_check_out) == 16:  # If no seconds part is present
            str_check_out += ':00'
        shortage_time = kw.get('shortage')
        date = datetime.strptime(str_date, "%Y-%m-%d").date()
        check_in = datetime.strptime(str_check_in, "%Y-%m-%dT%H:%M:%S")
        # check_in = datetime.strptime(str_check_in, "%Y-%m-%dT%H:%M")
        check_out = datetime.strptime(str_check_out, "%Y-%m-%dT%H:%M:%S")
        # check_out = datetime.strptime(str_check_out, "%Y-%m-%dT%H:%M")
        employee_obj = request.env['hr.employee'].sudo().browse(employee_id)
        reason = kw.get('message') if kw.get('message') else False
        employee_manager_id = employee_obj.parent_id
        # hr_supervisor_group_ids = [request.env.ref('hr_attendance.group_hr_attendance_officer').id]
        hr_supervisor_group_ids = [request.env.ref('pr_hr_attendance.custom_group_hr_attendance_supervisor').id]
        hr_manager_group_ids = [request.env.ref('hr_attendance.group_hr_attendance_manager').id]
        hr_supervisor_ids = request.env['res.users'].sudo().search([('groups_id', 'in', hr_supervisor_group_ids)])
        hr_manager_ids = request.env['res.users'].sudo().search([('groups_id', 'in', hr_manager_group_ids)])
        shortage_request_id = request.env['pr.hr.shortage.request'].sudo().create({
            'date': date,
            'employee_id': employee_id,
            'check_in': check_in - relativedelta(hours=3),
            'check_out': check_out - relativedelta(hours=3),
            'shortage_time': shortage_time,
            'company_id': employee_obj.company_id.id if employee_obj.company_id else request.env.company.id,
            'employee_reason': reason,
            'employee_manager_id': employee_manager_id.id if employee_manager_id else False,
            'hr_supervisor_ids': hr_supervisor_ids.ids if hr_supervisor_ids else False,
            'hr_manager_ids': hr_manager_ids.ids if hr_manager_ids else False,
        })
        if shortage_request_id:
            # Create Attachments And Add Them To Leave Request
            attachment_ids = []
            attachment_list = request.httprequest.files.getlist('attachment_ids')
            for att in attachment_list:
                if kw.get('attachment_ids'):
                    attachments = {
                        'res_name': att.filename,
                        'res_model': 'pr.hr.shortage.request',
                        'res_id': shortage_request_id.sudo().id,
                        'datas': base64.encodebytes(att.read()),
                        'type': 'binary',
                        'name': att.filename,
                    }
                    attachment_obj = http.request.env['ir.attachment']
                    att_record = attachment_obj.sudo().create(attachments)
                    attachment_ids.append(att_record.id)
            shortage_request_id.sudo()._send_manager_email()
            return http.request.render('de_hr_workspace_attendance.thanks_template')
        else:
            print(kw, 'False')
            return False

