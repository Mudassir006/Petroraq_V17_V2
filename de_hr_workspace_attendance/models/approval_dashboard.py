from odoo import _, api, models
from odoo.tools.safe_eval import safe_eval
from odoo.osv import expression


class HrApprovalDashboardService(models.AbstractModel):
    _name = "de.hr.approval.dashboard.service"
    _description = "HR Approval Dashboard Service"

    @api.model
    def _get_visible_approval_menus(self):
        parent = self.env.ref(
            "de_hr_workspace.menu_my_employee_approvals",
            raise_if_not_found=False,
        )
        if not parent:
            return self.env["ir.ui.menu"]

        menus = self.env["ir.ui.menu"].sudo().search([
            ("id", "child_of", parent.id),
            ("id", "!=", parent.id),
        ], order="sequence, id")

        filter_visible = getattr(self.env["ir.ui.menu"], "_filter_visible_menus", None)
        if filter_visible:
            menus = menus._filter_visible_menus()
        else:
            user_groups = self.env.user.groups_id
            menus = menus.filtered(
                lambda m: not m.groups_id or bool(m.groups_id & user_groups)
            )

        return menus.filtered(lambda m: bool(m.action))

    @api.model
    def _domain_from_action(self, action):
        domain_str = action.domain or "[]"
        eval_context = {
            "uid": self.env.uid,
            "user": self.env.user,
            "context": dict(self.env.context),
        }
        try:
            domain = safe_eval(domain_str, eval_context)
            return domain if isinstance(domain, (list, tuple)) else []
        except Exception:
            return []

    @api.model
    def _shortage_pending_domain(self):
        return [
            "|", "|",
            ("employee_manager_id.user_id", "=", self.env.uid),
            ("hr_supervisor_ids", "in", self.env.uid),
            ("hr_manager_ids", "in", self.env.uid),
            ("approval_state", "in", ["draft", "manager_approve", "hr_supervisor"]),
        ]

    @api.model
    def _leave_pending_domain(self):
        return [
            ("state", "in", ["confirm", "validate1"]),
            "|",
            ("employee_id.parent_id.user_id", "=", self.env.uid),
            ("holiday_status_id.responsible_id", "=", self.env.uid),
        ]

    @api.model
    def _leave_request_pending_domain(self):
        user = self.env.user
        role_domains = [
            [("employee_manager_id.user_id", "=", self.env.uid), ("state", "=", "draft")],
            [("state", "=", "cancel_request")],
        ]

        if user.has_group("hr_holidays.group_hr_holidays_manager"):
            role_domains.append([
                ("state", "=", "hr_supervisor"),
                ("hr_manager_ids", "in", self.env.uid),
            ])
        if user.has_group("pr_hr_holidays.custom_group_hr_holidays_supervisor"):
            role_domains.append([
                ("state", "=", "manager_approve"),
                ("hr_supervisor_ids", "in", self.env.uid),
            ])

        return expression.OR(role_domains)

    @api.model
    def _override_domain_for_menu(self, menu, action, domain):
        menu_name = (menu.name or "").lower()
        if action.res_model == "pr.hr.shortage.request" or "shortage" in menu_name:
            return self._shortage_pending_domain()
        if action.res_model == "pr.hr.leave.request":
            return self._leave_request_pending_domain()
        if action.res_model == "hr.leave" or "leave" in menu_name:
            return self._leave_pending_domain()
        return domain

    @api.model
    def _count_for_action(self, menu, action):
        if action._name != "ir.actions.act_window" or not action.res_model:
            return 0
        try:
            domain = self._domain_from_action(action)
            domain = self._override_domain_for_menu(menu, action, domain)
            return self.env[action.res_model].search_count(domain)
        except Exception:
            return 0

    @api.model
    def _style_for_menu(self, menu_name):
        name = (menu_name or "").lower()
        if "leave" in name:
            return "fa-calendar-check-o", "success"
        if "shortage" in name:
            return "fa-clock-o", "warning"
        if "account" in name:
            return "fa-money", "info"
        if "pay" in name:
            return "fa-file-text-o", "danger"
        if "sale" in name:
            return "fa-line-chart", "primary"
        if "recruit" in name:
            return "fa-users", "warning"
        if "purchase" in name:
            return "fa-shopping-cart", "primary"
        if "hr" in name:
            return "fa-id-badge", "info"
        return "fa-check-square-o", "primary"

    @api.model
    def get_tiles(self):
        tiles = []
        for menu in self._get_visible_approval_menus():
            action = menu.sudo().action
            count = self._count_for_action(menu, action)
            icon, tone = self._style_for_menu(menu.name)
            tiles.append({
                "key": f"menu_{menu.id}",
                "name": menu.name or _("Approval"),
                "count": count,
                "icon": icon,
                "tone": tone,
                "action_id": action.id,
            })
        return tiles