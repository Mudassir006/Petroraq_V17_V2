from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrderRejectWizard(models.TransientModel):
    _name = "sale.order.reject.wizard"
    _description = "Reject Sale Order with Reason"

    order_id = fields.Many2one("sale.order", required=True, ondelete="cascade")
    reason = fields.Text(string="Rejection Reason", required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        order = self.order_id
        # reuse existing security check
        if order.approval_state not in ("to_manager", "to_md"):
            raise UserError(_("Only waiting approvals can be rejected."))

        # record reason and reject
        order.approval_comment = self.reason
        order.approval_state = "rejected"
        order.state = "cancel"
        order.message_post(body=_("Quotation has been rejected. Reason: %s") % self.reason)
        return {"type": "ir.actions.act_window_close"}
