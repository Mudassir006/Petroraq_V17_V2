from odoo import models, _
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    # def button_confirm(self):
    #     CostCenter = self.env["pr.work.order.cost.center"]
    #
    #     for po in self:
    #         for line in po.order_line:
    #             dist = line.analytic_distribution or {}
    #             if not dist:
    #                 raise ValidationError(
    #                     _("Please set Analytic Distribution on all PO lines.")
    #                 )
    #
    #             line_amount = line.price_subtotal  # exclude taxes
    #
    #             for analytic_key, percent in dist.items():
    #                 if not percent:
    #                     continue
    #
    #                 analytic_id = int(analytic_key)
    #                 allocated = (line_amount * percent) / 100.0
    #
    #                 # 🔑 derive cost center (and WO) from analytic
    #                 cc = CostCenter.search(
    #                     [("analytic_account_id", "=", analytic_id)],
    #                     limit=1
    #                 )
    #
    #                 if not cc:
    #                     raise ValidationError(_(
    #                         "Analytic account %s is not linked to any Work Order Cost Center.\n"
    #                         "PO Line: %s"
    #                     ) % (analytic_id, line.display_name))
    #
    #                 # optional safety: ensure analytic is not reused across WOs
    #                 if CostCenter.search_count(
    #                     [("analytic_account_id", "=", analytic_id)]
    #                 ) > 1:
    #                     raise ValidationError(_(
    #                         "Analytic account %s is linked to multiple Work Orders.\n"
    #                         "Please fix configuration."
    #                     ) % analytic_id)
    #
    #                 if float_compare(
    #                     cc.remaining_amount,
    #                     allocated,
    #                     precision_rounding=po.currency_id.rounding
    #                 ) < 0:
    #                     raise ValidationError(_(
    #                         "Budget exceeded for section '%s' (WO: %s).\n"
    #                         "Remaining: %s\n"
    #                         "Trying to reserve: %s"
    #                     ) % (
    #                         cc.section_name,
    #                         cc.work_order_id.name,
    #                         cc.remaining_amount,
    #                         allocated,
    #                     ))
    #
    #     return super().button_confirm()
