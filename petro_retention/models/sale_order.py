from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    retention_percent = fields.Float(
        string="Retention (%)",
        digits=(16, 4),
        default=0.0,
        copy=False,
        help="Retention percentage withheld from each invoice (based on invoice base).",
    )

    retention_amount_total = fields.Monetary(
        string="Retention Amount",
        currency_field="currency_id",
        compute="_compute_retention_totals",
        inverse="_inverse_retention_amount_total",
        store=True,
        copy=False,
        help="Total retention to be withheld across all invoices (computed from %). You can edit it; % will be recalculated.",
    )

    retention_withheld_total = fields.Monetary(
        string="Retention Withheld",
        currency_field="currency_id",
        compute="_compute_retention_totals",
        store=False,
        copy=False,
    )

    retention_remaining = fields.Monetary(
        string="Retention Remaining",
        currency_field="currency_id",
        compute="_compute_retention_totals",
        store=False,
        copy=False,
    )

    # -------------------------
    # Helpers
    # -------------------------
    def _retention_total_amount(self):
        """Total retention based on amount_untaxed (common in construction)."""
        self.ensure_one()
        currency = self.currency_id or self.company_id.currency_id
        base = currency.round(self.amount_untaxed or 0.0)
        return currency.round(base * (self.retention_percent or 0.0) / 100.0)

    def _retention_withheld_amount(self):
        """Net withheld from posted invoices/refunds using the tracked invoice retention amount."""
        self.ensure_one()
        currency = self.currency_id or self.company_id.currency_id
        invoices = self.invoice_ids.filtered(
            lambda m: m.state == "posted" and m.move_type in ("out_invoice", "out_refund")
        )
        if not invoices:
            return 0.0

        withheld = 0.0
        for move in invoices:
            amount = currency.round(move.retention_deduct_amount or 0.0)
            if move.move_type == "out_refund":
                withheld -= amount
            else:
                withheld += amount
        return max(0.0, currency.round(withheld))

    def _retention_remaining_amount(self):
        self.ensure_one()
        currency = self.currency_id or self.company_id.currency_id
        total = currency.round(self.retention_amount_total or 0.0)
        withheld = currency.round(self._retention_withheld_amount())
        return max(0.0, currency.round(total - withheld))

    # -------------------------
    # Computes / inverse
    # -------------------------
    @api.depends(
        "amount_untaxed",
        "retention_percent",
        "invoice_ids.state",
        "invoice_ids.move_type",
        "invoice_ids.retention_deduct_amount",
    )
    def _compute_retention_totals(self):
        for order in self:
            currency = order.currency_id or order.company_id.currency_id
            computed_total = order._retention_total_amount()

            # If retention_amount_total is empty but % is set -> fill it
            # If user already set amount manually -> keep it (inverse will adjust %)
            if (order.retention_percent or 0.0) and currency.is_zero(order.retention_amount_total or 0.0):
                order.retention_amount_total = computed_total

            withheld = order._retention_withheld_amount()
            remaining = order._retention_remaining_amount()

            order.retention_withheld_total = withheld
            order.retention_remaining = remaining

    def _inverse_retention_amount_total(self):
        """If user enters Retention Amount, compute the % from amount_untaxed."""
        for order in self:
            currency = order.currency_id or order.company_id.currency_id
            base = currency.round(order.amount_untaxed or 0.0)
            if currency.is_zero(base):
                order.retention_percent = 0.0
                continue
            amt = currency.round(order.retention_amount_total or 0.0)
            order.retention_percent = (amt / base) * 100.0

    # -------------------------
    # Invoice hook (DP-style)
    # -------------------------
    def _create_invoices(self, grouped=False, final=False, date=None):
        moves = super()._create_invoices(grouped=grouped, final=final, date=date)
        if not moves:
            return moves

        remaining_map = {}
        for order in self:
            currency = order.currency_id or order.company_id.currency_id
            remaining_map[order.id] = currency.round(order._retention_remaining_amount())

        for move in moves:
            retention_total = 0.0
            invoice_lines = move.invoice_line_ids.filtered(
                lambda l: not l.display_type and not getattr(l, "is_downpayment", False)
            )
            for order in move.invoice_line_ids.mapped("sale_line_ids.order_id"):
                currency = order.currency_id or order.company_id.currency_id
                retention_pct = order.retention_percent or 0.0
                if retention_pct <= 0:
                    continue

                remaining = currency.round(remaining_map.get(order.id, 0.0))
                if currency.is_zero(remaining):
                    continue

                order_lines = invoice_lines.filtered(
                    lambda l: order in l.sale_line_ids.order_id
                )
                invoice_base = currency.round(sum(order_lines.mapped("price_subtotal")) or 0.0)
                if invoice_base <= 0:
                    continue

                target = min(remaining, currency.round(invoice_base * retention_pct / 100.0))
                if currency.is_zero(target):
                    continue

                retention_total += target
                remaining_map[order.id] = currency.round(remaining - target)

            move.retention_deduct_amount = retention_total

        return moves