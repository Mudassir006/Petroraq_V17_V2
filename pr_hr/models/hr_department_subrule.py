from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from hijri_converter import Gregorian
from datetime import date
from dateutil.relativedelta import relativedelta


class DepartmentSubrule(models.Model):
    _name = "hr.department.subrule"
    _description = "Subrule Department"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "id"
    _rec_name = 'complete_name'
    _parent_store = True

    name = fields.Char('Subrule Name', required=True, translate=True)
    complete_name = fields.Char('Complete Name', compute='_compute_complete_name', recursive=True, store=True)
    active = fields.Boolean('Active', default=True)
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company)
    department_id = fields.Many2one('hr.department', string='Department', index=True, check_company=True,
                                    domain="[('has_subrules', '=', True)]")
    parent_id = fields.Many2one('hr.department.subrule', string='Parent Subrule', index=True, check_company=True)
    child_ids = fields.One2many('hr.department.subrule', 'parent_id', string='Child Subrule Departments')
    manager_id = fields.Many2one('hr.employee', string='Manager', tracking=True, check_company=True)
    member_ids = fields.One2many('hr.employee', 'subrule_department_id', string='Members', readonly=True)
    total_employee = fields.Integer(compute='_compute_total_employee', string='Total Employee')
    jobs_ids = fields.One2many('hr.job', 'subrule_department_id', string='Jobs')
    note = fields.Text('Note')
    color = fields.Integer('Color Index')
    parent_path = fields.Char(index=True, unaccent=False)
    master_department_id = fields.Many2one(
        'hr.department.subrule', 'Master Subrule', compute='_compute_master_department_id', store=True)

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for subrule_dept in self:
            if subrule_dept.parent_id:
                subrule_dept.complete_name = '%s / %s' % (subrule_dept.parent_id.complete_name, subrule_dept.name)
            else:
                subrule_dept.complete_name = subrule_dept.name

    def _compute_total_employee(self):
        emp_data = self.env['hr.employee']._read_group([('subrule_department_id', 'in', self.ids)], ['subrule_department_id'], ['__count'])
        result = {subrule_dept.id: count for subrule_dept, count in emp_data}
        for department in self:
            department.total_employee = result.get(department.id, 0)

    @api.depends('parent_path')
    def _compute_master_department_id(self):
        for department in self:
            department.master_department_id = int(department.parent_path.split('/')[0])

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive departments.'))

    @api.constrains("department_id")
    def _check_department_(self):
        for subrule in self:
            if subrule.department_id:
                if subrule.id not in subrule.department_id.subrule_department_ids.ids:
                    subrule.department_id.write({
                        'subrule_department_ids': [(4, subrule.id)]
                    })

    @api.model_create_multi
    def create(self, vals_list):
        # TDE note: auto-subscription of manager done by hand, because currently
        # the tracking allows to track+subscribe fields linked to a res.user record
        # An update of the limited behavior should come, but not currently done.
        departments = super(DepartmentSubrule, self.with_context(mail_create_nosubscribe=True)).create(vals_list)
        for department, vals in zip(departments, vals_list):
            manager = self.env['hr.employee'].browse(vals.get("manager_id"))
            if manager.user_id:
                department.message_subscribe(partner_ids=manager.user_id.partner_id.ids)
        return departments

    def write(self, vals):
        """ If updating manager of a department, we need to update all the employees
            of department hierarchy, and subscribe the new manager.
        """
        # TDE note: auto-subscription of manager done by hand, because currently
        # the tracking allows to track+subscribe fields linked to a res.user record
        # An update of the limited behavior should come, but not currently done.
        if 'manager_id' in vals:
            manager_id = vals.get("manager_id")
            if manager_id:
                manager = self.env['hr.employee'].browse(manager_id)
                # subscribe the manager user
                if manager.user_id:
                    self.message_subscribe(partner_ids=manager.user_id.partner_id.ids)
            # set the employees's parent to the new manager
            self._update_employee_subrule_manager(manager_id)
        return super(DepartmentSubrule, self).write(vals)

    def _update_employee_subrule_manager(self, manager_id):
        employees = self.env['hr.employee']
        for subrule_dept in self:
            domain = [
                ('id', '!=', manager_id),
                ('subrule_department_id', '=', subrule_dept.id),
            ]
            if manager_id:
                domain.append(('subrule_parent_id', '=', manager_id.manager_id.id))
            employees = employees | self.env['hr.employee'].search(domain)
        employees.write({'subrule_parent_id': manager_id})

    def get_children_department_ids(self):
        return self.env['hr.department.subrule'].search([('id', 'child_of', self.ids)])

    def get_department_hierarchy(self):
        if not self:
            return {}

        hierarchy = {
            'parent': {
                'id': self.parent_id.id,
                'name': self.parent_id.name,
                'employees': self.parent_id.total_employee,
            } if self.parent_id else False,
            'self': {
                'id': self.id,
                'name': self.name,
                'employees': self.total_employee,
            },
            'children': [
                {
                    'id': child.id,
                    'name': child.name,
                    'employees': child.total_employee
                } for child in self.child_ids
            ]
        }

        return hierarchy
