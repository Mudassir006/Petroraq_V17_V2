from odoo import models, fields, api


class ProjectProject(models.Model):
    _inherit = "project.project"

    budget_type = fields.Selection(
        [("opex", "Opex"), ("capex", "Capex")], string="Budget Type"
    )
    budget_code = fields.Char(string="Cost Center Code")
    budget_allowance = fields.Float(string="Budget Allowance")
    all_bank_accounts = fields.Many2many(
        "res.partner.bank",
        string="Bank Accounts",
        default=lambda self: self.env["res.partner.bank"].search([]),
    )
    budget_left = fields.Float(
        string="Budget Left", compute="_compute_budget_left", store=True
    )
    purchase_order_ids = fields.One2many(
        "purchase.order", "project_id", string="Purchase Orders"
    )

    @api.depends(
        "budget_allowance",
        "purchase_order_ids.grand_total",
        "purchase_order_ids.state",
    )
    def _compute_budget_left(self):
        for project in self:
            spent = 0
            for po in project.purchase_order_ids:
                if po.state == "purchase":  # only deduct if confirmed as Purchase
                    spent += po.grand_total
            project.budget_left = project.budget_allowance - spent
