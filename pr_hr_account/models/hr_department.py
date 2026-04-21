from odoo import api, fields, models, _


class HrDepartment(models.Model):
    # region [Initial]
    _inherit = 'hr.department'
    # endregion [Initial]

    department_cost_center_id = fields.Many2one("account.analytic.account", string="Department Cost Center",
                                    domain="[('analytic_plan_type', '=', 'department')]")


