from odoo import models, _
from odoo.tools import frozendict
from odoo.exceptions import UserError


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    def _prepare_down_payment_lines_values(self, order):
        self.ensure_one()

        currency = order.currency_id

        commercial_total = order.amount_total

        untaxed_total = order.amount_untaxed or 0.0
        if not untaxed_total:
            return []

        # 2) Scaling factor (keep float, but always round monetary results later)
        scaling_factor = commercial_total / untaxed_total

        # 3) Advance ratio
        if self.advance_payment_method == "percentage":
            advance_ratio = self.amount / 100.0
        else:
            advance_ratio = self.fixed_amount / commercial_total if commercial_total else 0.0

        # ✅ Odoo target (what total DP should be)
        target_dp_total = currency.round(commercial_total * advance_ratio)

        # 4) Core base
        order_lines = order.order_line.filtered(lambda l: not l.display_type and not l.is_downpayment)
        base_vals = self._prepare_base_downpayment_line_values(order)

        tax_base_lines = [
            line._convert_to_tax_base_line_dict(
                analytic_distribution=line.analytic_distribution,
                handle_price_include=False,
            )
            for line in order_lines
        ]
        computed_taxes = self.env["account.tax"]._compute_taxes(tax_base_lines)

        down_payment_values = []

        for base_line, tax_data in computed_taxes["base_lines_to_update"]:
            taxes = base_line["taxes"].flatten_taxes_hierarchy()
            fixed_taxes = taxes.filtered(lambda t: t.amount_type == "fixed")

            # ✅ ROUND like Odoo: monetary value rounded in currency
            scaled_subtotal = currency.round(tax_data["price_subtotal"] * scaling_factor)

            down_payment_values.append([
                taxes - fixed_taxes,
                base_line["analytic_distribution"],
                scaled_subtotal,
            ])

            # Fixed taxes: keep Odoo logic (do not scale fixed tax amount)
            for fixed_tax in fixed_taxes:
                if fixed_tax.price_include:
                    continue

                if fixed_tax.include_base_amount:
                    pct_tax = taxes[list(taxes).index(fixed_tax) + 1:] \
                        .filtered(lambda t: t.is_base_affected and t.amount_type != "fixed")
                else:
                    pct_tax = self.env["account.tax"]

                fixed_amt = currency.round(base_line["quantity"] * fixed_tax.amount)

                down_payment_values.append([
                    pct_tax,
                    base_line["analytic_distribution"],
                    fixed_amt,
                ])

        # 5) Group per tax
        line_map = {}
        analytic_map = {}

        for taxes, analytic_dist, subtotal in down_payment_values:
            key = frozendict({"tax_id": tuple(sorted(taxes.ids))})

            line_map.setdefault(key, {
                **base_vals,
                **key,
                "product_uom_qty": 0.0,
                "price_unit": 0.0,
            })

            # ✅ monetary sum, keep float but will round later
            line_map[key]["price_unit"] += subtotal

            if analytic_dist:
                analytic_map.setdefault(key, [])
                analytic_map[key].append((subtotal, analytic_dist))

        # 6) Build final lines + apply advance + rounding
        lines = []
        for key, vals in line_map.items():
            if order.currency_id.is_zero(vals["price_unit"]):
                continue

            if analytic_map.get(key):
                merged_analytic = {}
                total = vals["price_unit"] or 1.0
                for subtotal, dist in analytic_map[key]:
                    for acc, ratio in dist.items():
                        merged_analytic.setdefault(acc, 0.0)
                        merged_analytic[acc] += (subtotal / total) * ratio
                vals["analytic_distribution"] = merged_analytic

            # ✅ Apply % and round in currency (Odoo-style)
            vals["price_unit"] = currency.round(vals["price_unit"] * advance_ratio)

            lines.append(vals)

        # ✅ 7) BUFFER FIX: force sum(lines.price_unit) == target_dp_total
        if lines:
            current_total = currency.round(sum(l["price_unit"] for l in lines))
            diff = currency.round(target_dp_total - current_total)

            # Put diff on last line (same as typical Odoo buffer behavior)
            if not currency.is_zero(diff):
                lines[-1]["price_unit"] = currency.round(lines[-1]["price_unit"] + diff)

        return lines

    def create_invoices(self):
        orders = self.env["sale.order"].browse(self._context.get("active_ids", []))
        if self.advance_payment_method in ("percentage", "fixed"):
            orders_with_downpayment = orders.filtered(
                lambda order: order.order_line.filtered(
                    lambda line: not line.display_type and line.is_downpayment
                )
            )
            if orders_with_downpayment:
                raise UserError(
                    _(
                        "Only one down payment is allowed per sales order. "
                        "Remove the existing down payment before creating another."
                    )
                )

        res = super().create_invoices()

        if self.advance_payment_method == "percentage":
            for order in orders:
                order.dp_percent = self.amount / 100.0
        elif self.advance_payment_method == "fixed":
            for order in orders:
                base = order.amount_untaxed or 0.0
                order.dp_percent = (self.amount / base) if base else 0.0

        return res
