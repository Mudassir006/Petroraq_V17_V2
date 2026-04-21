from odoo import models, _, api, fields
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        for picking in self:
            if picking.picking_type_code != "outgoing":
                continue

            sale = picking.sale_id
            if not sale:
                continue

            # ==========================================================
            # (1) BLOCK OVER-DELIVERY (supports partial deliveries)
            # total_after = already_delivered + done_in_this_picking
            # ==========================================================
            done_by_sol = {}

            # Use move lines (qty_done) because that's what user edits/validates
            for ml in picking.move_line_ids:
                move = ml.move_id
                sol = move.sale_line_id

                if not sol or move.scrapped or move.state == "cancel":
                    continue

                sale_uom = sol.product_uom
                qty_sale_uom = ml.product_uom_id._compute_quantity(ml.quantity, sale_uom)

                done_by_sol[sol] = done_by_sol.get(sol, 0.0) + qty_sale_uom

            for sol, done_this in done_by_sol.items():
                ordered = sol.product_uom_qty  # in sale UoM
                delivered = sol.qty_delivered  # already delivered (historical), in sale UoM
                total_after = delivered + done_this
                prec = sol.product_uom.rounding

                if float_compare(total_after, ordered, precision_rounding=prec) > 0:
                    raise UserError(_(
                        "Over-delivery is not allowed.\n\n"
                        "Delivery: %(picking)s\n"
                        "Sale Order: %(so)s\n"
                        "Product: %(product)s\n"
                        "Ordered: %(ordered)s\n"
                        "Already delivered: %(delivered)s\n"
                        "This delivery: %(this)s\n"
                        "Total after: %(total)s"
                    ) % {
                                        "picking": picking.name,
                                        "so": sale.name,
                                        "product": sol.product_id.display_name,
                                        "ordered": ordered,
                                        "delivered": delivered,
                                        "this": done_this,
                                        "total": total_after,
                                    })

            # ==========================================================
            # (2) ADVANCE requires paid DP (your rule)
            # ==========================================================
            if sale.payment_term_id and (sale.payment_term_id.name or "").strip().lower() == "advance":
                dp_invoices = sale.invoice_ids.filtered(lambda inv:
                                                        inv.state == "posted"
                                                        and inv.move_type == "out_invoice"
                                                        and inv.payment_state in ("paid", "in_payment")
                                                        and any(
                                                            (aml.price_subtotal or 0.0) > 0
                                                            and aml.sale_line_ids.filtered(
                                                                lambda sol: getattr(sol, "is_downpayment", False))
                                                            for aml in inv.invoice_line_ids
                                                        )
                                                        )
                if not dp_invoices:
                    raise UserError(_(
                        "You cannot validate this delivery.\n\n"
                        "A Down Payment invoice must be posted and paid (or in payment) "
                        "before delivering an Advance order."
                    ))

        return super().button_validate()


# class StockMoveLine(models.Model):
#     _inherit = "stock.move.line"
#
#     @api.constrains("qty_done")
#     def _constrains_no_overdelivery(self):
#         for ml in self:
#             picking = ml.picking_id
#             move = ml.move_id
#
#             if not picking or picking.picking_type_code != "outgoing" or not picking.sale_id:
#                 continue
#             if not move.sale_line_id or move.scrapped:
#                 continue
#
#             ordered = move.sale_line_id.product_uom_qty
#             done = sum(move.move_line_ids.mapped("qty_done"))
#             rounding = move.product_uom.rounding or 0.0
#
#             if done > ordered + rounding:
#                 raise ValidationError(_(
#                     "Over-delivery is not allowed.\n\n"
#                     "Product: %(product)s\n"
#                     "Ordered: %(ordered)s\n"
#                     "Trying to deliver: %(done)s"
#                 ) % {
#                                           "product": move.product_id.display_name,
#                                           "ordered": ordered,
#                                           "done": done,
#                                       })


class SaleOrderDiscount(models.TransientModel):
    _inherit = "sale.order.discount"

    @api.model
    def _get_discount_type_selection(self):
        """Keep only 'On All Order Lines'"""
        return [
            ('sol_discount', "On All Order Lines"),
        ]

    discount_type = fields.Selection(
        selection=_get_discount_type_selection,
        default='sol_discount',
        required=True,
    )
