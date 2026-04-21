from odoo import models, fields, api, SUPERUSER_ID
from datetime import date

class HrShortageRequest(models.Model):
    _inherit = 'pr.hr.shortage.request'

    # region [System Methods]

    @api.model
    def search_fetch(self, domain, field_names, offset=0, limit=None, order=None):
        user = self.env.user
        view_action_id = self.env.ref("de_hr_workspace_attendance.action_my_shortage_request_approvals")
        approvals_of_shortage_request = self.env.context.get("approvals_of_shortage_request")
        params = self.env.context.get("params")
        if params:
            action_id = params.get("action")
        else:
            action_id = False
        domain = domain or []
        if user.has_group("de_hr_workspace.group_hr_employee_approvals") and ( approvals_of_shortage_request or (action_id and action_id == view_action_id.id)):
            domain = []
            role_domains = []
            # Employee Manager
            role_domains.append([
                ('employee_manager_id.user_id', '=', user.id),
                ('state', '=', 'draft')
            ])

            # HR Manager
            if user.has_group("hr_attendance.group_hr_attendance_manager"):
                role_domains.append([
                    ('state', '=', 'hr_supervisor'),
                    ('hr_manager_ids', 'in', user.id),
                ])
            # HR Supervisor
            # elif user.has_group("hr_attendance.group_hr_attendance_officer"):
            elif user.has_group("pr_hr_attendance.custom_group_hr_attendance_supervisor"):
                role_domains.append([
                    ('state', '=', 'manager_approve'),
                    ('hr_supervisor_ids', 'in', user.id),
                ])

            # Combine roles with OR
            if len(role_domains) == 1:
                domain += role_domains[0]
            else:
                combined = ['|'] * (len(role_domains) - 1)
                for rd in role_domains:
                    if len(rd) > 1:
                        combined += ['&'] * (len(rd) - 1) + rd
                    else:
                        combined += rd
                domain += combined
            return super().search_fetch(domain, field_names, offset, limit, order)
        else:
            return super().search_fetch(domain, field_names, offset, limit, order)

    # endregion [System Methods]

