from odoo import fields, models


class CrossoveredBudget(models.Model):
    _inherit = "crossovered.budget"

    # Declare these links in pr_work_order context as well, so when this
    # module is installed the relation to pr.work.order is always a real model
    # (not `_unknown`) and auto-created budgets keep their source document links.
    sale_order_id = fields.Many2one("sale.order", string="Sale Order")
    work_order_id = fields.Many2one("pr.work.order", string="Work Order")
