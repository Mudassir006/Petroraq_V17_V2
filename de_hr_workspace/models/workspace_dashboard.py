from odoo import _, api, models


class HrWorkspaceDashboardService(models.AbstractModel):
    _name = "de.hr.workspace.dashboard.service"
    _description = "HR Workspace Dashboard Service"

    @api.model
    def _get_visible_workspace_menus(self):
        parent = self.env.ref("de_hr_workspace.menu_my_ws_employee", raise_if_not_found=False)
        dashboard_menu = self.env.ref("de_hr_workspace.menu_hr_workspace_dashboard", raise_if_not_found=False)
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
            menus = menus.filtered(lambda m: not m.groups_id or bool(m.groups_id & user_groups))

        return menus.filtered(
            lambda m: bool(m.action)
            and (not dashboard_menu or m.id != dashboard_menu.id)
            and not (
                m.action
                and getattr(m.action, "_name", "") == "ir.actions.client"
                and getattr(m.action, "tag", "") == "de_hr_workspace.workspace_dashboard"
            )
        )

    @api.model
    def _style_for_menu(self, menu_name):
        name = (menu_name or "").lower()
        if "leave" in name:
            return "fa-calendar-check-o", "success"
        if "attendance" in name:
            return "fa-clock-o", "warning"
        if "contract" in name:
            return "fa-file-text-o", "info"
        if "pay" in name:
            return "fa-money", "danger"
        if "insurance" in name:
            return "fa-shield", "primary"
        return "fa-folder-open", "primary"

    @api.model
    def get_tiles(self):
        tiles = []
        for menu in self._get_visible_workspace_menus():
            action = menu.sudo().action
            icon, tone = self._style_for_menu(menu.name)
            tiles.append({
                "key": f"menu_{menu.id}",
                "name": menu.name or _("Workspace Item"),
                "icon": icon,
                "tone": tone,
                "action_id": action.id,
            })
        return tiles
