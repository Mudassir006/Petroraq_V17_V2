# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    service_receipt_note_ids = fields.One2many(
        "service.receipt.note",
        "purchase_id",
        string="Service Receipt Notes",
    )
    service_receipt_note_count = fields.Integer(
        string="SRN Count",
        compute="_compute_service_receipt_note_count",
    )
    has_service_lines = fields.Boolean(
        string="Has Service Lines",
        compute="_compute_has_service_lines",
    )

    @api.depends("service_receipt_note_ids")
    def _compute_service_receipt_note_count(self):
        for order in self:
            order.service_receipt_note_count = len(order.service_receipt_note_ids)

    @api.depends("order_line.product_id", "order_line.display_type")
    def _compute_has_service_lines(self):
        for order in self:
            order.has_service_lines = any(
                line.product_id
                and not line.display_type
                and line.product_id.detailed_type == "service"
                for line in order.order_line
            )

    def action_create_service_receipt_note(self):
        self.ensure_one()

        if self.state not in ("purchase", "done"):
            raise UserError(_("Please confirm the Purchase Order first."))

        service_lines = self.order_line.filtered(
            lambda l: not l.display_type and l.product_id.detailed_type == "service"
        )
        if not service_lines:
            raise UserError(_("This Purchase Order has no service product lines."))

        line_commands = self._prepare_srn_line_commands(service_lines)

        if not line_commands:
            raise UserError(_("All service quantities for this Purchase Order are already received."))

        srn = self.env["service.receipt.note"].create({
            "purchase_id": self.id,
            "state": "ready",
            "line_ids": line_commands,
        })

        return {
            "type": "ir.actions.act_window",
            "name": _("Service Receipt Note"),
            "res_model": "service.receipt.note",
            "view_mode": "form",
            "res_id": srn.id,
            "target": "current",
        }

    def action_view_service_receipt_notes(self):
        self.ensure_one()
        action = self.env.ref("service_receipt_note.action_service_receipt_note").read()[0]
        action["domain"] = [("purchase_id", "=", self.id)]
        if self.service_receipt_note_count == 1:
            action["view_mode"] = "form"
            action["res_id"] = self.service_receipt_note_ids.id
        return action

    def _prepare_srn_line_commands(self, service_lines):
        self.ensure_one()
        line_commands = []
        for po_line in service_lines:
            already_received = sum(
                self.env["service.receipt.note.line"].search([
                    ("purchase_line_id", "=", po_line.id),
                    ("receipt_id.state", "=", "done"),
                ]).mapped("done_qty")
            )
            remaining = po_line.product_qty - already_received
            if remaining > 0:
                line_commands.append(
                    (
                        0,
                        0,
                        {
                            "purchase_line_id": po_line.id,
                            "name": po_line.name or po_line.product_id.display_name,
                            "done_qty": 0.0,
                        },
                    )
                )
        return line_commands

    def button_confirm(self):
        result = super().button_confirm()
        for order in self:
            if order.state not in ("purchase", "done"):
                continue
            if order.service_receipt_note_ids.filtered(lambda r: r.state in ("draft", "ready")):
                continue

            service_lines = order.order_line.filtered(
                lambda l: not l.display_type and l.product_id.detailed_type == "service"
            )
            line_commands = order._prepare_srn_line_commands(service_lines)
            if line_commands:
                self.env["service.receipt.note"].create({
                    "purchase_id": order.id,
                    "state": "ready",
                    "line_ids": line_commands,
                })
        return result


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    srn_received_qty = fields.Float(
        string="SRN Received Qty",
        compute="_compute_srn_received_qty",
        digits="Product Unit of Measure",
    )
    srn_remaining_qty = fields.Float(
        string="SRN Remaining Qty",
        compute="_compute_srn_received_qty",
        digits="Product Unit of Measure",
    )


    def _update_qty_received_from_srn(self):
        receipt_line_model = self.env["service.receipt.note.line"]
        for line in self.filtered(lambda l: l.product_id.detailed_type == "service"):
            done_lines = receipt_line_model.search([
                ("purchase_line_id", "=", line.id),
                ("receipt_id.state", "=", "done"),
            ])
            received = sum(done_lines.mapped("done_qty"))
            if line.qty_received != received:
                line.qty_received = received

    @api.depends("product_qty")
    def _compute_srn_received_qty(self):
        receipt_line_model = self.env["service.receipt.note.line"]
        for line in self:
            if line.product_id.detailed_type != "service":
                line.srn_received_qty = 0.0
                line.srn_remaining_qty = 0.0
                continue

            done_lines = receipt_line_model.search([
                ("purchase_line_id", "=", line.id),
                ("receipt_id.state", "=", "done"),
            ])
            received = sum(done_lines.mapped("done_qty"))
            line.srn_received_qty = received
            line.srn_remaining_qty = max(line.product_qty - received, 0.0)