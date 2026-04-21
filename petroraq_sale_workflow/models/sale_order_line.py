from string import digits

from odoo import api, fields, models, _
from odoo.tools import format_amount, html_escape


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    section_subtotal_amount = fields.Monetary(
        string="Section Subtotal",
        compute="_compute_section_subtotal_amount",
        store=False,
        currency_field="currency_id",
        help="Subtotal of the products within this section."
    )
    section_subtotal_display = fields.Html(
        string="Section Subtotal Display",
        compute="_compute_section_subtotal_amount",
        sanitize=False,
        help="Formatted subtotal snippet for section headers."
    )

    # IMPORTANT: not stored, and use Monetary
    final_price_unit = fields.Monetary(
        string="Final Unit Price",
        compute="_compute_final_price_unit",
        store=False,
        currency_field="currency_id",
    )

    cost_price_unit = fields.Float(
        string="Unit Cost",
        related="product_id.standard_price",
        readonly=True,
        digits="Product Price",
    )
    net_unit_price = fields.Float(
        string="Net Unit Price",
        currency_field="currency_id",
        compute="_compute_net_unit_price",
        store=True,
        readonly=True,
        digits='Product Price',
        precompute=True
    )

    @api.depends("price_unit", "discount", "currency_id")
    def _compute_net_unit_price(self):
        for line in self:
            price = line.price_unit or 0.0
            disc = line.discount or 0.0
            net = price * (1 - disc / 100.0)
            line.net_unit_price = net
            print(f"nnnnnnnnnnnnnnnnnnnnnn{net}")

    def _compute_sale_price_from_cost(self, cost):
        self.ensure_one()
        order = self.order_id
        currency = self.currency_id or order.currency_id or order.company_id.currency_id
        b = order._costing_line_breakdown(base_unit=cost or 0.0, qty=1.0, currency=currency)
        return b["final_u"]

    @api.onchange("product_id", "order_id.overhead_percent", "order_id.risk_percent", "order_id.profit_percent",
                  "product_uom_qty")
    def _onchange_set_sale_price_from_product_cost(self):
        for line in self:
            if line.display_type or getattr(line, "is_downpayment", False) or not line.order_id:
                continue
            if not line.product_id:
                continue
            line.price_unit = line._compute_sale_price_from_cost(line.product_id.standard_price)

    def _sync_price_unit_from_product_cost(self):
        for line in self:
            if line.display_type or getattr(line, "is_downpayment", False) or not line.order_id:
                continue
            if not line.product_id:
                continue

            sale_price = line._compute_sale_price_from_cost(line.product_id.standard_price)
            if not self.env.context.get("skip_sync_price_unit") and line.price_unit != sale_price:
                line.with_context(skip_sync_price_unit=True).price_unit = sale_price

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._sync_price_unit_from_product_cost()
        return lines

    def write(self, vals):
        res = super().write(vals)
        # if product or costing inputs changed, resync
        if set(vals).intersection({"product_id", "product_template_id"}):
            self._sync_price_unit_from_product_cost()
        return res

    @api.depends(
        "price_unit",
        "order_id.overhead_percent",
        "order_id.risk_percent",
        "order_id.profit_percent",
        "currency_id",
        "display_type",
        "is_downpayment",
    )
    def _compute_final_price_unit(self):
        for line in self:
            line.final_price_unit = line.price_unit or 0.0


    def _prepare_invoice_line(self, **optional_values):
        vals = super()._prepare_invoice_line(**optional_values)

        if not self.display_type and not getattr(self, "is_downpayment", False):
            order = self.order_id
            currency = self.currency_id or order.currency_id or order.company_id.currency_id

            return vals

        # Downpayment deduction line: force amount-based deduction
        if getattr(self, "is_downpayment", False) and not self.display_type:
            qty = vals.get("quantity") or 0.0
            if qty < 0:  # deduction line
                amount_map = self.env.context.get("dp_deduct_amounts") or {}
                target_amount = amount_map.get(self.order_id.id)

                if target_amount:
                    vals["quantity"] = -1.0
                    vals["price_unit"] = target_amount
                    vals["discount"] = 0.0

                    # Create deduction as a regular invoice line (same as manual add):
                    # keep taxes, but remove sale_line_ids linkage that forces
                    # account.move.line.is_downpayment=True.
                    vals["sale_line_ids"] = [(5, 0, 0)]
                    # vals["is_downpayment"] = False
                    vals["dp_source_sale_line_id"] = self.id

        return vals

    # =========================
    # Section subtotal chips
    # =========================
    @api.depends(
        "display_type",
        "sequence",
        "order_id.order_line.display_type",
        "order_id.order_line.sequence",
        "order_id.order_line.price_unit",
        "order_id.order_line.cost_price_unit",
        "order_id.order_line.product_uom_qty",
        "order_id.order_line.is_downpayment",
        "order_id.overhead_percent",
        "order_id.risk_percent",
        "order_id.profit_percent",
        "currency_id",
    )
    def _compute_section_subtotal_amount(self):
        label = _("Sub Total")

        for line in self:
            line.section_subtotal_amount = 0.0
            line.section_subtotal_display = False

        for order in self.mapped("order_id"):
            currency = order.currency_id or order.company_id.currency_id

            subtotal = 0.0
            current_section = None

            ordered_lines = order.order_line.sorted(key=lambda l: (l.sequence or 0, l.id or 0))
            for line in ordered_lines:
                if line.display_type == "line_section":
                    if current_section:
                        current_section._set_section_subtotal_values(subtotal, label)
                    current_section = line
                    subtotal = 0.0
                    line.section_subtotal_amount = 0.0
                    line.section_subtotal_display = False
                    continue

                if line.display_type or getattr(line, "is_downpayment", False):
                    continue

                # Costing subtotal (same as PDF)
                breakdown = order._costing_line_breakdown(
                    base_unit=line.cost_price_unit or 0.0,  # ✅ use COST as base
                    qty=line.product_uom_qty or 0.0,
                    currency=currency,
                )
                subtotal += breakdown["total_line"]

            if current_section:
                current_section._set_section_subtotal_values(subtotal, label)

    def _set_section_subtotal_values(self, amount, label):
        self.ensure_one()
        currency = self.order_id.currency_id or self.order_id.company_id.currency_id
        amount_display = format_amount(self.env, amount or 0.0, currency) if currency else f"{(amount or 0.0):.2f}"

        self.section_subtotal_amount = amount
        self.section_subtotal_display = (
            f"<span class='o_section_subtotal_chip_label'>{html_escape(label)}</span>"
            f"<span class='o_section_subtotal_chip_value'>{html_escape(amount_display)}</span>"
        )