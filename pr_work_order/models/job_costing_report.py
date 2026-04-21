from odoo import fields, models, tools


class PRWorkOrderCostingReport(models.Model):
    _name = "pr.work.order.costing.report"
    _description = "Work Order Costing Report"
    _auto = False

    work_order_id = fields.Many2one("pr.work.order", string="Work Order", readonly=True)
    sale_order_id = fields.Many2one("sale.order", string="Sale Order", readonly=True)
    project_id = fields.Many2one("project.project", string="Project", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Customer", readonly=True)
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    analytic_account_id = fields.Many2one("account.analytic.account", string="Cost Center", readonly=True)
    state = fields.Selection(selection=lambda self: self.env["pr.work.order"]._fields["state"].selection)

    contract_amount = fields.Monetary(string="Contract Amount", readonly=True)
    budgeted_cost = fields.Monetary(string="Budgeted Cost", readonly=True)
    budgeted_margin = fields.Monetary(string="Budgeted Margin", readonly=True)
    overhead_amount = fields.Monetary(string="Overhead Amount", readonly=True)
    risk_amount = fields.Monetary(string="Risk Amount", readonly=True)
    total_expected_cost = fields.Monetary(string="Total Expected Cost", readonly=True)
    profit_amount = fields.Monetary(string="Profit Amount", readonly=True)
    total_with_profit = fields.Monetary(string="Total With Profit", readonly=True)
    actual_revenue = fields.Monetary(string="Actual Revenue", readonly=True)
    actual_cost = fields.Monetary(string="Actual Cost", readonly=True)
    actual_margin = fields.Monetary(string="Actual Margin", readonly=True)
    currency_id = fields.Many2one("res.currency", readonly=True)

    date_start = fields.Date(string="Planned Start Date", readonly=True)
    date_end = fields.Date(string="Planned End Date", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    row_number() OVER () AS id,
                    wo.id AS work_order_id,
                    wo.sale_order_id,
                    wo.project_id,
                    wo.partner_id,
                    wo.company_id,
                    wo.analytic_account_id,
                    wo.state,
                    wo.contract_amount,
                    wo.budgeted_cost,
                    wo.budgeted_margin,
                    wo.overhead_amount,
                    wo.risk_amount,
                    wo.total_expected_cost,
                    wo.profit_amount,
                    wo.total_with_profit,
                    wo.actual_revenue,
                    wo.actual_cost,
                    wo.actual_margin,
                    wo.currency_id,
                    wo.date_start,
                    wo.date_end
                FROM pr_work_order wo
            )
            """ % self._table
        )


class PRWorkOrderCostingSectionReport(models.Model):
    _name = "pr.work.order.costing.section.report"
    _description = "Work Order Costing Section Report"
    _auto = False

    work_order_id = fields.Many2one("pr.work.order", string="Work Order", readonly=True)
    cost_center_id = fields.Many2one("pr.work.order.cost.center", string="Cost Center", readonly=True)
    section_name = fields.Char(string="Section", readonly=True)
    analytic_account_id = fields.Many2one("account.analytic.account", string="Cost Center Account", readonly=True)
    estimated_cost = fields.Monetary(string="Estimated Cost", readonly=True)
    actual_cost = fields.Monetary(string="Actual Cost", readonly=True)
    variance = fields.Monetary(string="Variance", readonly=True)
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    state = fields.Selection(selection=lambda self: self.env["pr.work.order"]._fields["state"].selection)
    currency_id = fields.Many2one("res.currency", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    row_number() OVER () AS id,
                    cc.id AS cost_center_id,
                    cc.work_order_id,
                    cc.section_name,
                    cc.analytic_account_id,
                    cc.estimated_cost,
                    COALESCE(actuals.actual_cost, 0) AS actual_cost,
                    (cc.estimated_cost - COALESCE(actuals.actual_cost, 0)) AS variance,
                    wo.company_id,
                    wo.currency_id,
                    wo.state
                FROM pr_work_order_cost_center cc
                JOIN pr_work_order wo ON wo.id = cc.work_order_id
                LEFT JOIN (
                    SELECT
                        account_id,
                        ABS(SUM(amount)) AS actual_cost
                    FROM account_analytic_line
                    GROUP BY account_id
                ) actuals ON actuals.account_id = cc.analytic_account_id
            )
            """ % self._table
        )
