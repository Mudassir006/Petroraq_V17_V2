from odoo import fields, models, api, _

from odoo.tools.float_utils import float_round, float_compare
from odoo.exceptions import UserError, ValidationError


class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"

    petroraq_selectable = fields.Boolean(
        string="Selectable for Petroraq Sales",
        default=False,
    )
    is_trading_term = fields.Boolean(
        string="Trading Payment Term",
        default=False,
        help="If enabled, this payment term is ONLY allowed when inquiry type is Trading."
    )


class SaleOrder(models.Model):
    _inherit = "sale.order"

    dp_remaining_amount_ui = fields.Monetary(
        string="Remaining Down Payment",
        compute="_compute_dp_remaining_amount_ui",
        currency_field="currency_id",
        store=False,
    )

    can_refund_remaining_dp = fields.Boolean(
        compute="_compute_can_refund_remaining_dp",
        store=False,
    )

    @api.depends("order_line.invoice_lines.move_id.state", "order_line.invoice_lines.move_id.move_type",
                 "order_line.invoice_lines.price_subtotal")
    def _compute_dp_remaining_amount_ui(self):
        for order in self:
            order.dp_remaining_amount_ui = order._dp_remaining_amount()

    @api.depends("state", "dp_remaining_amount_ui")
    def _compute_can_refund_remaining_dp(self):
        for order in self:
            currency = order.currency_id or order.company_id.currency_id
            order.can_refund_remaining_dp = (
                    order.state not in ("cancel",) and
                    not currency.is_zero(order.dp_remaining_amount_ui or 0.0)
            )

    def action_refund_remaining_dp(self):
        self.ensure_one()
        currency = self.currency_id or self.company_id.currency_id

        remaining = currency.round(self._dp_remaining_amount())
        if currency.is_zero(remaining):
            raise UserError(_("No remaining down payment to refund."))

        dp_so_line = self._dp_sale_line()
        if not dp_so_line:
            raise UserError(_("No down payment line found on this Sale Order."))

        # Find the posted positive DP invoice line (to reuse account/taxes/journal)
        dp_amls = dp_so_line.invoice_lines.filtered(
            lambda l: l.move_id.state == "posted"
                      and l.move_id.move_type == "out_invoice"
                      and (l.price_subtotal or 0.0) > 0.0
        )
        if not dp_amls:
            raise UserError(_("No posted down payment invoice found to refund from."))

        base_aml = dp_amls[0]
        journal = base_aml.move_id.journal_id
        account = base_aml.account_id
        taxes = base_aml.tax_ids

        partner = self.partner_invoice_id or self.partner_id

        refund = self.env["account.move"].create({
            "move_type": "out_refund",
            "partner_id": partner.id,
            "invoice_origin": self.name,
            "ref": _("Refund Remaining DP - %s") % (self.name,),
            "company_id": self.company_id.id,
            "currency_id": currency.id,
            "journal_id": journal.id,
            "invoice_payment_term_id": self.payment_term_id.id,
            "invoice_line_ids": [(0, 0, {
                "name": _("Refund of unused Down Payment - %s") % (self.name,),
                "product_id": dp_so_line.product_id.id,
                "quantity": 1.0,
                "price_unit": remaining,
                "account_id": account.id,
                "tax_ids": [(6, 0, taxes.ids)],
                "analytic_distribution": base_aml.analytic_distribution or False,

                # ✅ THIS is the actual link to sale order (invoice_ids)
                "sale_line_ids": [(6, 0, dp_so_line.ids)],
            })],
        })

        return {
            "type": "ir.actions.act_window",
            "name": _("Remaining DP Refund"),
            "res_model": "account.move",
            "res_id": refund.id,
            "view_mode": "form",
            "target": "current",
        }

    def _dp_paid_amount(self):
        """Total DP untaxed that was posted (positive DP invoices only)."""
        self.ensure_one()
        dp_line = self._dp_sale_line()
        if not dp_line:
            return 0.0

        amls = dp_line.invoice_lines.filtered(
            lambda l: l.move_id.state == "posted"
                      and l.move_id.move_type == "out_invoice"
                      and (getattr(l, "price_subtotal_signed", l.price_subtotal) or 0.0) > 0.0
        )
        return sum(abs(getattr(l, "price_subtotal_signed", l.price_subtotal) or 0.0) for l in amls) or 0.0

    def _dp_remaining_amount(self):
        """Remaining DP = paid - deducted - refunded (all posted, untaxed)."""
        self.ensure_one()
        currency = self.currency_id or self.company_id.currency_id

        paid = currency.round(self._dp_paid_amount())
        deducted = currency.round(self._dp_deducted_amount())
        refunded = currency.round(self._dp_refunded_amount())

        return max(0.0, currency.round(paid - deducted - refunded))

    def _dp_sale_line(self):
        self.ensure_one()
        return self.order_line.filtered(lambda l: l.is_downpayment and not l.display_type)[:1]

    def _dp_deducted_amount(self):
        """Total DP deducted (untaxed) from posted regular invoices (negative dp lines)."""
        self.ensure_one()
        dp_line = self._dp_sale_line()
        if not dp_line:
            return 0.0

        amls = self.env["account.move.line"].search([
            ("move_id.state", "=", "posted"),
            ("move_id.move_type", "=", "out_invoice"),
            "|",
            ("sale_line_ids", "in", dp_line.ids),
            ("dp_source_sale_line_id", "=", dp_line.id),
        ])
        amls = amls.filtered(lambda l: (getattr(l, "price_subtotal_signed", l.price_subtotal) or 0.0) < 0.0)
        return sum(abs(getattr(l, "price_subtotal_signed", l.price_subtotal) or 0.0) for l in amls) or 0.0

    def _is_fully_delivered(self):
        """Final invoice if all stockable/consu lines are fully delivered."""
        self.ensure_one()
        lines = self.order_line.filtered(
            lambda l: not l.display_type and not l.is_downpayment and l.product_id
        ).filtered(lambda l: l.product_id.type in ("product", "consu"))

        if not lines:
            return False

        for l in lines:
            if float_compare(
                    l.qty_delivered, l.product_uom_qty,
                    precision_rounding=l.product_uom.rounding
            ) < 0:
                return False
        return True

    def _get_invoiceable_lines(self, final=False):
        lines = super()._get_invoiceable_lines(final=final)

        dp_deduct_amounts = dict(self.env.context.get("dp_deduct_amounts") or {})

        for order in self:
            currency = order.currency_id or order.company_id.currency_id
            dp_so_line = order._dp_sale_line()

            # ------------------------------------------------------------
            # (A) CRITICAL: If a DP was already taken (posted DP invoice exists),
            # never allow the DP line to be invoiceable again as a positive line.
            # We will only re-add it when we explicitly deduct.
            # ------------------------------------------------------------
            if dp_so_line:
                paid_dp = currency.round(order._dp_paid_amount())
                if not currency.is_zero(paid_dp):
                    lines = lines.filtered(lambda l: l.id != dp_so_line.id)

            # ------------------------------------------------------------
            # (B) Your deduction logic (keep it), but now it's the ONLY way
            # the DP line can appear on future invoices.
            # ------------------------------------------------------------
            dp_percent = order.dp_percent or 0.0
            if not dp_percent:
                continue

            remaining_dp_amount = currency.round(order._dp_remaining_amount())
            if currency.is_zero(remaining_dp_amount):
                continue

            base_lines = lines.filtered(
                lambda l: l.order_id == order and not l.display_type and not l.is_downpayment
            )

            invoice_base = 0.0
            for l in base_lines:
                qty = l.qty_to_invoice or 0.0
                if not qty:
                    continue
                unit = l.price_unit or 0.0
                disc = (l.discount or 0.0) / 100.0
                net_unit = unit * (1.0 - disc)
                invoice_base += currency.round(net_unit * qty)

            invoice_base = currency.round(invoice_base)
            if invoice_base <= 0:
                continue

            target_amount = min(remaining_dp_amount, currency.round(invoice_base * dp_percent))
            if currency.is_zero(target_amount):
                continue

            dp_deduct_amounts[order.id] = target_amount

            if dp_so_line:
                lines |= dp_so_line
                dp_so_line.qty_to_invoice = -1.0

        return lines.with_context(dp_deduct_amounts=dp_deduct_amounts)

    def _dp_refunded_amount(self):
        """Total DP refunded (untaxed) via posted credit notes linked to DP line."""
        self.ensure_one()
        dp_line = self._dp_sale_line()
        if not dp_line:
            return 0.0

        amls = self.env["account.move.line"].search([
            ("move_id.state", "=", "posted"),
            ("move_id.move_type", "=", "out_refund"),
            "|",
            ("sale_line_ids", "in", dp_line.ids),
            ("dp_source_sale_line_id", "=", dp_line.id),
        ])
        return sum(abs(getattr(l, "price_subtotal_signed", l.price_subtotal) or 0.0) for l in amls) or 0.0