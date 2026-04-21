from odoo import api, fields, models, _


class AccountMoveLine(models.Model):
    # region [Initial]
    _inherit = 'account.move.line'
    # endregion [Initial]

    account_name = fields.Char(string='Acc. Name', related="account_id.name", store=True,
                               tracking=True)
    cs_project_id = fields.Many2one("account.analytic.account", string="Project",
                                    domain="[('analytic_plan_type', '=', 'project')]")
    check_cost_centers_block = fields.Boolean(compute="_compute_check_cost_centers_block")
    journal_voucher_view = fields.Boolean(related="move_id.journal_voucher_view", store=True)

    # @api.depends("account_id", "account_id.cash_equivalents_subcategory", "account_id.accounts_receivable_subcategory")
    # @api.onchange("account_id", "account_id.cash_equivalents_subcategory", "account_id.accounts_receivable_subcategory")
    @api.depends("account_id", "account_id.main_head")
    @api.onchange("account_id", "account_id.main_head")
    def _compute_check_cost_centers_block(self):
        for line in self:
            if line.account_id and line.account_id.main_head in ["revenue", "expense"]:
                line.check_cost_centers_block = True
            else:
                line.check_cost_centers_block = False

        # region [Onchange Methods]

    @api.onchange("account_id")
    def _onchange_account_id(self):
        for line in self:
            if line.account_id:
                line.analytic_distribution = False
                line.partner_id = False

    @api.onchange("cs_project_id")
    def _onchange_cs_project_id(self):
        for line in self:
            project_ids = self.env["account.analytic.account"].sudo().search(
                [("analytic_plan_type", "=", "project")]).mapped("id")

            analytic_distribution = {}
            if line.cs_project_id:
                # Analytic Distribution
                if line.cs_project_id.department_id:
                    analytic_distribution.update({
                        str(line.cs_project_id.department_id.id): 100.0
                    })
                if line.cs_project_id.section_id:
                    analytic_distribution.update({
                        str(line.cs_project_id.section_id.id): 100.0
                    })
                analytic_distribution.update({
                    str(line.cs_project_id.id): 100.0
                })

                # Project Manager
                if line.cs_project_id.project_partner_id:
                    line.partner_id = line.cs_project_id.project_partner_id.id
            line.analytic_distribution = analytic_distribution
            # Analytic Distribution

        # endregion [Onchange Methods]
