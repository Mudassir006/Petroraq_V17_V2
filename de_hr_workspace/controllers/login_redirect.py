from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.home import Home


class HomeLoginRedirect(Home):
    _APPROVER_GROUPS = (
        "de_hr_workspace.group_hr_employee_approvals",
        "hr.group_hr_manager",
        "pr_account.custom_group_accounting_manager",
        "account.group_account_manager",
        "account.group_account_user",
        "pr_custom_purchase.project_manager",
        "pr_custom_purchase.managing_director",
        "petroraq_sale_workflow.group_sale_approval_manager",
        "petroraq_sale_workflow.group_sale_approval_md",
        "pr_work_order.custom_group_work_order_operations",
        "pr_work_order.custom_group_work_order_accounts",
        "pr_work_order.custom_group_work_order_management",
    )

    def _get_approval_dashboard_url(self):
        """Build a stable dashboard URL using XMLIDs instead of DB ids."""
        env = request.env
        action = env.ref("de_hr_workspace_attendance.action_hr_approval_dashboard", raise_if_not_found=False)
        menu = env.ref("de_hr_workspace_attendance.menu_hr_approval_dashboard", raise_if_not_found=False)

        if not action:
            return False

        fragments = [f"action={action.id}"]
        if menu:
            fragments.append(f"menu_id={menu.id}")

        allowed_company_ids = request.session.context.get("allowed_company_ids") if request.session.context else []
        if allowed_company_ids:
            fragments.append("cids=%s" % ",".join(str(company_id) for company_id in allowed_company_ids))

        return "/web#%s" % "&".join(fragments)

    @http.route('')
    def web_login(self, redirect=None, **kw):
        response = super().web_login(redirect=redirect, **kw)

        if request.httprequest.method != "POST" or not request.session.uid:
            return response

        user = request.env.user
        if not any(user.has_group(group_xmlid) for group_xmlid in self._APPROVER_GROUPS):
            return response

        dashboard_url = self._get_approval_dashboard_url()
        if not dashboard_url:
            return response
        server_url = request.env["ir.config_parameter"].sudo().get_param("web.base.url")
        return request.redirect(f"{server_url}/{dashboard_url}")
