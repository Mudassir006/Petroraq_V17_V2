from odoo import api, fields, models, _


class HrEmployee(models.Model):
    # region [Initial]
    _inherit = 'hr.employee'
    # endregion [Initial]

    department_cost_center_id = fields.Many2one("account.analytic.account", string="Department Cost Center",
                                              domain="[('analytic_plan_type', '=', 'department')]")
    section_cost_center_id = fields.Many2one("account.analytic.account", string="Section Cost Center",
                                                domain="[('analytic_plan_type', '=', 'section')]")
    project_cost_center_id = fields.Many2one("account.analytic.account", string="Project Cost Center",
                                             domain="[('analytic_plan_type', '=', 'project')]")
    employee_cost_center_id = fields.Many2one("account.analytic.account", string="Employee Cost Center",
                                    domain="[('analytic_plan_type', '=', 'employee')]")
    employee_account_id = fields.Many2one("account.account", string="Employee Account")


