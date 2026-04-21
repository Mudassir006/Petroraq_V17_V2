from odoo import api, fields, models, _


class ResGroups(models.Model):
    """

    """
    # region [Initial]
    _inherit = 'res.groups'
    # endregion [Initial]

    # region [Fields]

    # endregion

    @api.constrains("users")
    def _check_users_to_check_approvals(self):
        res = super()._check_users_to_check_approvals()
        for group in self:
            # hr_supervisor_group_id = self.env.ref('hr_holidays.group_hr_holidays_user')
            hr_supervisor_group_id = self.env.ref('pr_hr_holidays.custom_group_hr_holidays_supervisor')
            hr_manager_group_id = self.env.ref('hr_holidays.group_hr_holidays_manager')
            if group.id == hr_supervisor_group_id.id:
                user_ids = hr_supervisor_group_id.users
                if user_ids:
                    leave_request_ids = self.env["pr.hr.leave.request"].sudo().search([("state", "in", ["draft", "manager_approve"])])
                    if leave_request_ids:
                        for leave_request in leave_request_ids:
                            leave_request.sudo().write({"hr_supervisor_ids": [(6, 0, user_ids.ids)]})
            if group.id == hr_manager_group_id.id:
                user_ids = hr_manager_group_id.users
                if user_ids:
                    leave_request_ids = self.env["pr.hr.leave.request"].sudo().search([("state", "in", ["draft", "manager_approve", "hr_supervisor"])])
                    if leave_request_ids:
                        for leave_request in leave_request_ids:
                            leave_request.sudo().write({"hr_manager_ids": [(6, 0, user_ids.ids)]})
        return res
