from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    work_order_id = fields.Many2one("pr.work.order", string="Work Order")

    def action_post(self):
        for move in self:
            if move.move_type not in ("in_invoice", "in_refund"):
                continue

            wo = move.work_order_id
            if not wo:
                continue

            for line in move.invoice_line_ids:
                cc = line.wo_cost_center_id
                if not cc:
                    raise ValidationError(_("Please set WO Cost Center on all bill lines."))

                # bill line amount (use line.price_subtotal in invoice currency)
                spend = line.price_subtotal

                # remaining budget
                if cc.remaining_amount < spend:
                    raise ValidationError(_(
                        "Budget exceeded for section '%s'. Remaining: %s, trying to spend: %s"
                    ) % (cc.section_name, cc.remaining_amount, spend))

        return super().action_post()

    @api.onchange("work_order_id")
    def _onchange_work_order_id(self):
        """
        When a Work Order is selected on the bill header:
        - Clear WO cost center on lines (because its domain depends on WO)
        - Optionally set default analytic distribution from WO main cost center
        """
        for move in self:
            wo_analytic = move.work_order_id.analytic_account_id if move.work_order_id else False

            for line in move.invoice_line_ids:
                # Clear cost center when WO changes (domain depends on WO)
                line.wo_cost_center_id = False

                # If WO has a main analytic account and line has no analytic_distribution, default it
                if wo_analytic and not line.analytic_distribution:
                    line.analytic_distribution = {str(wo_analytic.id): 100}


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    work_order_id = fields.Many2one(
        "pr.work.order",
        string="Work Order",
        help="Work Order this analytic entry belongs to.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line in lines:
            aml = line.move_line_id  # correct link in Odoo 17
            if aml and not line.work_order_id and aml.move_id.work_order_id:
                line.work_order_id = aml.move_id.work_order_id.id
        return lines


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    wo_cost_center_id = fields.Many2one(
        "pr.work.order.cost.center",
        string="WO Cost Center",
        domain="[('work_order_id', '=', parent.work_order_id)]",
    )

    @api.onchange("wo_cost_center_id")
    def _onchange_wo_cost_center_id(self):
        """
        When user selects a WO cost center on the bill line,
        set analytic_distribution to that cost center's analytic account.
        """
        for line in self:
            if line.wo_cost_center_id and line.wo_cost_center_id.analytic_account_id:
                analytic = line.wo_cost_center_id.analytic_account_id
                line.analytic_distribution = {str(analytic.id): 100}
            # else: don't force-clear analytic_distribution (keep user's existing selection)
