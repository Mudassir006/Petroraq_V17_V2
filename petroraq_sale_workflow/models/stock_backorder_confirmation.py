from odoo import _, api, fields, models


class StockBackorderConfirmation(models.TransientModel):
    _inherit = "stock.backorder.confirmation"

    def process_cancel_backorder(self):
        if self._context.get("skip_sale_close_confirmation"):
            return super().process_cancel_backorder()

        pickings = self.pick_ids
        if pickings.filtered("sale_id"):
            return {
                "type": "ir.actions.act_window",
                "res_model": "sale.order.close.no.backorder.confirm",
                "view_mode": "form",
                "target": "new",
                "context": {
                    "default_picking_ids": pickings.ids,
                    "backorder_confirmation_id": self.id,
                },
            }

        return super().process_cancel_backorder()


class SaleOrderCloseNoBackorderConfirm(models.TransientModel):
    _name = "sale.order.close.no.backorder.confirm"
    _description = "Confirm closing sale order without backorder"

    picking_ids = fields.Many2many(
        "stock.picking",
        string="Pickings",
        readonly=True,
    )
    sale_order_names = fields.Char(
        string="Sale Orders",
        compute="_compute_sale_order_names",
    )

    @api.depends("picking_ids")
    def _compute_sale_order_names(self):
        for wizard in self:
            sale_names = wizard.picking_ids.mapped("sale_id.name")
            wizard.sale_order_names = ", ".join(sale_names)

    def action_confirm_close(self):
        backorder_confirmation_id = self._context.get("backorder_confirmation_id")
        backorder = self.env["stock.backorder.confirmation"].browse(
            backorder_confirmation_id
        )
        return backorder.with_context(skip_sale_close_confirmation=True).process_cancel_backorder()
