from odoo import _, models


class PrWorkOrder(models.Model):
    _inherit = "pr.work.order"

    def action_open_my_work_order_approvals(self):
        states = []
        user = self.env.user
        if user.has_group("pr_work_order.custom_group_work_order_operations"):
            states.append("ops_approval")
        if user.has_group("pr_work_order.custom_group_work_order_accounts"):
            states.append("acc_approval")
        if user.has_group("pr_work_order.custom_group_work_order_management"):
            states.append("final_approval")

        domain = [("state", "in", states)] if states else [("id", "=", False)]
        return {
            "type": "ir.actions.act_window",
            "name": _("Work Orders"),
            "res_model": "pr.work.order",
            "view_mode": "list,form",
            "domain": domain,
            "context": {"create": False, "edit": False},
        }
