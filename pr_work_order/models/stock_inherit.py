from odoo import fields, models, api


class StockMove(models.Model):
    _inherit = "stock.move"

    work_order_id = fields.Many2one("pr.work.order", string="Work Order")

    def _action_done(self, *args, **kwargs):
        res = super()._action_done(*args, **kwargs)

        Analytic = self.env["account.analytic.line"]

        for move in self:
            wo = move.work_order_id
            if not wo:
                continue

            cost = move.value

            if not cost:
                continue

            Analytic.create({
                "name": f"Material Usage – {move.product_id.display_name}",
                "account_id": wo.analytic_account_id.id,
                "work_order_id": wo.id,
                "date": fields.Date.today(),
                "amount": -abs(cost),
                "unit_amount": move.product_uom_qty,
                "product_id": move.product_id.id,
                "company_id": move.company_id.id,
            })

        return res


class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.model_create_multi
    def create(self, vals_list):
        pickings = super().create(vals_list)

        for picking in pickings:
            sale = picking.sale_id
            if sale and sale.work_order_id:
                wo = sale.work_order_id

                picking.move_ids_without_package.write({
                    "work_order_id": wo.id,
                })

        return pickings
