# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero


class ServiceReceiptNote(models.Model):
    _name = "service.receipt.note"
    _description = "Service Receipt Note"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="SRN Number",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
        tracking=True,
    )
    purchase_id = fields.Many2one(
        "purchase.order",
        string="Purchase Order",
        required=True,
        tracking=True,
        ondelete="cascade",
    )
    partner_id = fields.Many2one(
        related="purchase_id.partner_id",
        string="Vendor",
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        related="purchase_id.company_id",
        string="Company",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        related="purchase_id.currency_id",
        string="Currency",
        store=True,
        readonly=True,
    )
    date = fields.Datetime(
        string="Receipt Date",
        default=fields.Datetime.now,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("ready", "Ready"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        default="ready",
        tracking=True,
    )
    line_ids = fields.One2many(
        "service.receipt.note.line",
        "receipt_id",
        string="Lines",
        copy=True,
    )
    note = fields.Text(string="Notes")
    approval_state = fields.Selection(
        [
            ("pending", "Pending Approval"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Approval",
        default="pending",
        tracking=True,
        copy=False,
    )
    rejection_reason = fields.Text(string="Rejection Reason", readonly=True, copy=False)
    backorder_id = fields.Many2one(
        "service.receipt.note",
        string="Source Backorder Of",
        copy=False,
    )
    backorder_ids = fields.One2many(
        "service.receipt.note",
        "backorder_id",
        string="Backorders",
    )
    backorder_count = fields.Integer(
        compute="_compute_backorder_count",
        string="Backorder Count",
    )
    purchase_state = fields.Selection(
        related="purchase_id.state",
        string="PO Status",
        store=True,
        readonly=True,
    )
    work_order_id = fields.Many2one(
        "pr.work.order",
        string="Work Order",
        related="purchase_id.requisition_id.expense_bucket_id.work_order_id",
        store=True,
        readonly=True,
    )

    @api.depends("backorder_ids")
    def _compute_backorder_count(self):
        for rec in self:
            rec.backorder_count = len(rec.backorder_ids)

    @api.model_create_multi
    def create(self, vals_list):
        seq_model = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = seq_model.next_by_code("service.receipt.note") or _("New")
        return super().create(vals_list)

    def action_set_ready(self):
        for rec in self:
            if rec.state == "draft":
                rec.state = "ready"
                rec.approval_state = "pending"
                rec.rejection_reason = False

    def action_approve(self):
        group = self.env.ref("pr_custom_purchase.inventory_admin", raise_if_not_found=False)
        if group and self.env.user not in group.users:
            raise UserError(_("Only Inventory Administration can approve SRN."))
        for rec in self.filtered(lambda r: r.state not in ("done", "cancel")):
            rec.write({"approval_state": "approved", "rejection_reason": False})

    def action_open_reject_wizard(self):
        self.ensure_one()
        if self.state in ("done", "cancel"):
            raise UserError(_("You cannot reject a done/cancelled SRN."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Reject SRN"),
            "res_model": "service.receipt.reject.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_receipt_id": self.id},
        }

    def action_cancel(self):
        for rec in self:
            if rec.state == "done":
                raise UserError(_("You cannot cancel a validated Service Receipt Note."))
            rec.state = "cancel"

    def action_reset_to_draft(self):
        for rec in self:
            if rec.state == "done":
                raise UserError(_("You cannot reset a validated Service Receipt Note to draft."))
            rec.state = "draft"
            rec.approval_state = "pending"
            rec.rejection_reason = False

    def action_view_backorders(self):
        self.ensure_one()
        action = self.env.ref("service_receipt_note.action_service_receipt_note").read()[0]
        action["domain"] = [("id", "in", self.backorder_ids.ids)]
        if len(self.backorder_ids) == 1:
            action["views"] = [(self.env.ref("service_receipt_note.view_service_receipt_note_form").id, "form")]
            action["res_id"] = self.backorder_ids.id
        return action

    def _validate_lines(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError(_("You cannot validate an SRN without lines."))

            has_any_qty = False
            for line in rec.line_ids:
                rounding = line.uom_id.rounding or 0.01

                if line.done_qty < 0:
                    raise ValidationError(
                        _("Done quantity cannot be negative for product %s.") % (line.product_id.display_name,)
                    )

                if float_compare(
                    line.done_qty,
                    line.remaining_qty_before,
                    precision_rounding=rounding,
                ) > 0:
                    raise ValidationError(
                        _(
                            "Done quantity for product '%s' cannot exceed remaining quantity.\n"
                            "Remaining: %s"
                        )
                        % (line.product_id.display_name, line.remaining_qty_before)
                    )

                if not float_is_zero(line.done_qty, precision_rounding=rounding):
                    has_any_qty = True

            if not has_any_qty:
                raise ValidationError(_("Please enter at least one non-zero Done Qty before validation."))

    def _prepare_backorder_vals(self, remaining_lines):
        self.ensure_one()
        return {
            "purchase_id": self.purchase_id.id,
            "state": "ready",
            "backorder_id": self.id,
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "purchase_line_id": line.purchase_line_id.id,
                        "name": line.name,
                        "done_qty": 0.0,
                    },
                )
                for line in remaining_lines
            ],
        }

    def _create_backorder_if_needed(self):
        self.ensure_one()
        remaining_lines = self.line_ids.filtered(
            lambda l: float_compare(
                l.balance_qty,
                0.0,
                precision_rounding=l.uom_id.rounding or 0.01,
            ) > 0
        )
        if not remaining_lines:
            return False
        backorder = self.create(self._prepare_backorder_vals(remaining_lines))
        message = _("Backorder %s has been created.") % backorder.display_name
        self.message_post(body=message)
        backorder.message_post(body=_("Created from %s.") % self.display_name)
        return backorder

    def action_validate(self):
        for rec in self:
            if rec.state in ("done", "cancel"):
                continue

            if rec.purchase_id.state not in ("purchase", "done"):
                raise UserError(_("The related Purchase Order must be confirmed before validating SRN."))

            if rec.approval_state != "approved":
                raise UserError(_("SRN must be approved by Inventory Administration before validation."))

            rec._validate_lines()
            rec.state = "done"

            rec.line_ids.mapped("purchase_line_id")._update_qty_received_from_srn()

            backorder = rec._create_backorder_if_needed()
            if backorder:
                rec.message_post(
                    body=_("Service Receipt Note validated successfully and backorder %s created.")
                    % backorder.display_name
                )
            else:
                rec.message_post(body=_("Service Receipt Note validated successfully."))


class ServiceReceiptRejectWizard(models.TransientModel):
    _name = "service.receipt.reject.wizard"
    _description = "Service Receipt Rejection Wizard"

    receipt_id = fields.Many2one("service.receipt.note", required=True)
    rejection_reason = fields.Text(string="Rejection Reason", required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        group = self.env.ref("pr_custom_purchase.inventory_admin", raise_if_not_found=False)
        if group and self.env.user not in group.users:
            raise UserError(_("Only Inventory Administration can reject SRN."))
        if self.receipt_id.state in ("done", "cancel"):
            raise UserError(_("You cannot reject a done/cancelled SRN."))
        self.receipt_id.write({
            "approval_state": "rejected",
            "rejection_reason": self.rejection_reason,
        })
        return {"type": "ir.actions.act_window_close"}


class ServiceReceiptNoteLine(models.Model):
    _name = "service.receipt.note.line"
    _description = "Service Receipt Note Line"
    _order = "id"

    receipt_id = fields.Many2one(
        "service.receipt.note",
        string="Receipt",
        required=True,
        ondelete="cascade",
    )
    purchase_line_id = fields.Many2one(
        "purchase.order.line",
        string="Purchase Order Line",
        required=True,
        domain=[("display_type", "=", False)],
    )
    product_id = fields.Many2one(
        related="purchase_line_id.product_id",
        string="Product",
        store=True,
        readonly=True,
    )
    name = fields.Text(string="Description", required=True)
    uom_id = fields.Many2one(
        related="purchase_line_id.product_uom",
        string="UoM",
        store=True,
        readonly=True,
    )
    ordered_qty = fields.Float(
        related="purchase_line_id.product_qty",
        string="Ordered Qty",
        store=True,
        readonly=True,
    )
    already_received_qty = fields.Float(
        string="Already Received",
        compute="_compute_quantities",
        digits="Product Unit of Measure",
    )
    remaining_qty_before = fields.Float(
        string="Remaining Qty",
        compute="_compute_quantities",
        digits="Product Unit of Measure",
    )
    done_qty = fields.Float(
        string="Done Qty",
        digits="Product Unit of Measure",
        default=0.0,
    )
    balance_qty = fields.Float(
        string="Balance After This SRN",
        compute="_compute_quantities",
        digits="Product Unit of Measure",
    )
    company_id = fields.Many2one(
        related="receipt_id.company_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        related="receipt_id.currency_id",
        store=True,
        readonly=True,
    )

    @api.constrains("purchase_line_id")
    def _check_service_product(self):
        for rec in self:
            if rec.purchase_line_id.product_id.detailed_type != "service":
                raise ValidationError(
                    _("Only service products can be added to Service Receipt Notes.")
                )

    @api.depends("purchase_line_id", "done_qty", "receipt_id.state")
    def _compute_quantities(self):
        ReceiptLine = self.env["service.receipt.note.line"]
        for line in self:
            if not line.purchase_line_id:
                line.already_received_qty = 0.0
                line.remaining_qty_before = 0.0
                line.balance_qty = 0.0
                continue

            domain = [
                ("purchase_line_id", "=", line.purchase_line_id.id),
                ("receipt_id.state", "=", "done"),
            ]
            # During onchange, unsaved one2many records may have a temporary NewId_* string,
            # which cannot be compared against integer ids in SQL.
            line_id = line._origin.id
            if line_id:
                domain.append(("id", "!=", line_id))

            prior_done_lines = ReceiptLine.search(domain)

            already_received = sum(prior_done_lines.mapped("done_qty"))
            ordered = line.purchase_line_id.product_qty
            remaining_before = max(ordered - already_received, 0.0)
            balance = max(remaining_before - line.done_qty, 0.0)

            line.already_received_qty = already_received
            line.remaining_qty_before = remaining_before
            line.balance_qty = balance
