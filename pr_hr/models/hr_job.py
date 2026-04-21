from odoo import api, fields, models, _


class HrJob(models.Model):
    """

    """
    # region [Initial]
    _inherit = 'hr.job'
    # endregion [Initial]

    # region [Fields]
    position_count = fields.Integer('Max Position Count', default=0,
                                    help='Max. No. Of Employees for This Job, Zero for Unlimited')
    nationality_ids = fields.Many2many('res.country', string='Nationalities',
                                       help='This Job accept only employee from specified nationalities, open if empty')
    employees_count = fields.Integer('Employees Count', compute="_compute_employees_count")
    locked = fields.Boolean('Locked', default=False, tracking=True)
    subrule_department_id = fields.Many2one('hr.department.rule', string='Subrule', index=True, check_company=True)

    # endregion

    # region [Actions]
    def set_locked(self):
        for rec in self:
            if not rec.locked:
                rec.locked = True

    def set_unlocked(self):
        for rec in self:
            if rec.locked:
                rec.locked = False

    # endregion [Actions]

    @api.depends('employee_ids')
    def _compute_employees_count(self):
        """
        Compute Count of All Valid Employees only
        :return:
        """
        for rec in self:
            employees_count = self.env['hr.employee'].sudo().search_count(
                [('state', '=', "in_service"), ('job_id', '=', rec.id)])
            rec.employees_count = employees_count

    def open_employees_records(self):
        """
        Open Employee List With Filter of Employees with the same Job
        Open All Employees not only Valid Employees
        :return:
        """
        return {
            'name': 'Employees',
            'res_model': 'hr.employee',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.employee_ids.ids)],
        }
