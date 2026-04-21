from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ExpenseBucket(models.Model):
    _inherit = "pr.expense.bucket"

    scope = fields.Selection(
        selection_add=[("trading", "Trading")],
        ondelete={"trading": "set default"},
    )
    work_order_id = fields.Many2one("pr.work.order", string="Work Order", tracking=True)
    sale_order_id = fields.Many2one("sale.order", string="Sale Order", tracking=True)
    po_reference = fields.Char(string="PO Reference", tracking=True)
    source_budget_limit = fields.Float(
        string="Source Budget Limit",
        tracking=True,
        copy=False,
        help="Maximum budget amount allowed based on the originating Work Order/Sale Order.",
    )

    @api.onchange("scope")
    def _onchange_scope_work_order(self):
        for rec in self:
            if rec.scope != "project":
                rec.work_order_id = False
            if rec.scope != "trading":
                rec.sale_order_id = False

    @api.constrains("scope", "work_order_id", "sale_order_id")
    def _check_scope_target_work_order(self):
        for rec in self:
            if rec.scope == "project" and not rec.work_order_id:
                raise ValidationError(_("Work Order is required when scope is Project."))
            if rec.scope == "trading" and not rec.sale_order_id:
                raise ValidationError(_("Sale Order is required when scope is Trading."))

    @api.constrains("budget_amount", "source_budget_limit", "work_order_id", "sale_order_id")
    def _check_source_budget_limit(self):
        for rec in self:
            budget_limit = rec.source_budget_limit or 0.0
            if budget_limit <= 0.0:
                continue
            if (rec.budget_amount or 0.0) > budget_limit:
                raise ValidationError(
                    _(
                        "Bucket budget (%s) cannot exceed source amount (%s)."
                    ) % (rec.budget_amount, budget_limit)
                )

    def write(self, vals):
        if "work_order_id" in vals or "sale_order_id" in vals:
            for rec in self:
                if rec.state == "approved":
                    raise ValidationError(_("Approved expense bucket cannot be edited."))
        return super().write(vals)
