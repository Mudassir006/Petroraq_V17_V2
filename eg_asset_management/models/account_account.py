from odoo import api, fields, models, _


class AccountAccount(models.Model):
    # region [Initial]
    _inherit = 'account.account'
    # endregion [Initial]

    # region [Fields]


    # endregion [Fields]

    def make_employee_asset_cost_center(self):
        employee_ids = self.env["hr.employee"].sudo().search([("active", "=", True)])
        for employee in employee_ids:
            employee_cost_center = self.env["account.analytic.account"].sudo().search([("analytic_plan_type", "=", "employee"), ("name", "=", employee.name)], limit=1)
            if not employee_cost_center:
                employee_plan = self.env.ref("pr_hr_account.pr_account_analytic_plan_employee")
                employee_cost_center = self.env["account.analytic.account"].sudo().create({
                    "name": employee.name,
                    "root_plan_id": employee_plan.id,
                    "plan_id": employee_plan.id,
                    "analytic_plan_type": "employee",
                })
        asset_ids = self.env["asset.detail"].sudo().search([("state", "=", "active")])
        for asset in asset_ids:
            asset_cost_center = self.env["account.analytic.account"].sudo().search(
                [("analytic_plan_type", "=", "asset"), ("name", "=", asset.name)], limit=1)
            if not asset_cost_center:
                asset_plan = self.env.ref("eg_asset_management.pr_account_analytic_plan_asset")
                asset_cost_center = self.env["account.analytic.account"].sudo().create({
                    "name": asset.name,
                    "root_plan_id": asset_plan.id,
                    "plan_id": asset_plan.id,
                    "analytic_plan_type": "asset",
                })

