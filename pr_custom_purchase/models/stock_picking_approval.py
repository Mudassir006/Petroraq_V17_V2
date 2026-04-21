from odoo import _, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    receipt_approval_state_ui = fields.Selection(
        [
            ("pending", "Pending Approval"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Receipt Approval",
        compute="_compute_receipt_approval_state_ui",
        store=False,
    )

    def _get_receipt_approval_state(self):
        """Schema-free approval state based on chatter markers."""
        self.ensure_one()
        if self.picking_type_code != "incoming":
            return "pending"
        last_msg = self.env["mail.message"].sudo().search([
            ("model", "=", "stock.picking"),
            ("res_id", "=", self.id),
            ("body", "ilike", "[RECEIPT_APPROVAL_STATE:"),
        ], order="id desc", limit=1)
        body = (last_msg.body or "") if last_msg else ""
        if "[RECEIPT_APPROVAL_STATE:APPROVED]" in body:
            return "approved"
        if "[RECEIPT_APPROVAL_STATE:REJECTED]" in body:
            return "rejected"
        return "pending"

    def _compute_receipt_approval_state_ui(self):
        for picking in self:
            picking.receipt_approval_state_ui = picking._get_receipt_approval_state()

    def button_validate(self):
        for picking in self:
            if picking.picking_type_code != "incoming":
                continue
            if picking._get_receipt_approval_state() != "approved":
                raise UserError(_("This receipt must be approved by Inventory Administration before validation."))
        return super().button_validate()

    def action_approve_receipt(self):
        group = self.env.ref("pr_custom_purchase.inventory_admin", raise_if_not_found=False)
        if group and self.env.user not in group.users:
            raise UserError(_("Only Inventory Administration can approve receipts."))
        for rec in self.filtered(lambda p: p.picking_type_code == "incoming"):
            rec.message_post(
                body=_(
                    "[RECEIPT_APPROVAL_STATE:APPROVED] Receipt approved by Inventory Administration."
                )
            )
        return True

    def action_open_receipt_reject_wizard(self):
        self.ensure_one()
        if self.picking_type_code != "incoming":
            raise UserError(_("Rejection is only available for incoming receipts."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Reject Receipt"),
            "res_model": "stock.picking.reject.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_picking_id": self.id},
        }


class StockPickingRejectWizard(models.TransientModel):
    _name = "stock.picking.reject.wizard"
    _description = "Stock Picking Rejection Wizard"

    picking_id = fields.Many2one("stock.picking", required=True)
    rejection_reason = fields.Text(string="Rejection Reason", required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        group = self.env.ref("pr_custom_purchase.inventory_admin", raise_if_not_found=False)
        if group and self.env.user not in group.users:
            raise UserError(_("Only Inventory Administration can reject receipts."))
        if self.picking_id.picking_type_code != "incoming":
            raise UserError(_("Rejection is only available for incoming receipts."))
        self.picking_id.message_post(
            body=_(
                "[RECEIPT_APPROVAL_STATE:REJECTED] Receipt rejected by Inventory Administration. Reason: %s"
            ) % self.rejection_reason
        )
        self.picking_id.action_cancel()
        return {"type": "ir.actions.act_window_close"}