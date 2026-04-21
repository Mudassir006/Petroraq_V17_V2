from odoo import api, fields, models, _


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    is_retention = fields.Boolean(
        string="Is Retention Line",
        default=False,
        copy=False,
        help="Technical line used to generate retention deduction on invoices.",
    )

    def _prepare_invoice_line(self, **optional_values):
        vals = super()._prepare_invoice_line(**optional_values)

        # Retention deduction line: force amount-based deduction (similar to DP logic)
        if getattr(self, "is_retention", False) and not self.display_type:
            qty = vals.get("quantity") or 0.0
            if qty < 0:
                amount_map = self.env.context.get("retention_deduct_amounts") or {}
                target_amount = amount_map.get(self.order_id.id)
                if target_amount:
                    vals["quantity"] = -1.0
                    vals["price_unit"] = target_amount
                    vals["discount"] = 0.0

                    # Keep taxes empty by default (withholding, not taxable)
                    vals["tax_ids"] = [(6, 0, [])]

                    # Optional: keep analytic distribution from order line if you want
                    # vals["analytic_distribution"] = self.analytic_distribution or False

        return vals
