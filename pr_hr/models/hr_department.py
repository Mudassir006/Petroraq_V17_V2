from odoo import api, fields, models, _


class HrDepartment(models.Model):
    """

    """
    # region [Initial]
    _inherit = 'hr.department'
    # endregion [Initial]

    # region [Fields]

    resource_calendar_id = fields.Many2one('resource.calendar', string="Working Schedule", check_company=True, tracking=True)
    has_subrules = fields.Boolean(string="Has Subrules ?")
    subrule_department_ids = fields.Many2many('hr.department.subrule', string='Subrules', check_company=True)

    # endregion

    @api.constrains("has_subrules","subrule_department_ids")
    def _check_subrule_departments(self):
        for department in self:
            if department.has_subrules and department.subrule_department_ids:
                for subrule in department.subrule_department_ids:
                    subrule.department_id = department.id
