import json
import random

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class HrEmployee(models.Model):
    """
    """
    # region [Initial]
    _inherit = 'hr.employee'
    # _order = 'code asc'
    # _rec_name = 'complete_name'
    # _rec_names_search = ['code', 'name', 'identification_id']
    # endregion [Initial]

    # region [Fields]
    # New Fields
    complete_name = fields.Char(string='Complete Name', compute='_compute_complete_name')
    code = fields.Char(string='Employee Code', size=4, help="Internal Employee Code")
    state = fields.Selection([('new', 'New'),
                              ('in_service', 'In-Service'),
                              ('in_leave', 'In-Leave'),
                              ('hold', 'Hold'),
                              ('out_service', 'Out-Service'),
                              ('escaped', 'Escaped')],
                             default='new', string='Status',
                             help='Current Status Of Company Employee\n'
                                  'New: Draft Employee, Not Yet in Service ,\n'
                                  'In-Service: Already In Service\n'
                                  'In-Leave: Employee in Vacation (already in service)\n'
                                  'Hold: in Case of Holding Employee Contract\n'
                                  'Out-Service: Employee Leave Company (Resign)\n'
                                  'Escaped: Employee has Escape Report, Can Reset to In-Service or Out_Service\n')
    signature = fields.Binary("Signature", attachment=True, max_width=150, max_height=150)
    signature_password = fields.Char(string='Signature Password', default='')
    iqama_count = fields.Integer(string="IQAMA", compute="_compute_iqama_count")
    insurance_count = fields.Integer(string="Medical Insurance", compute="_compute_insurance_count")
    has_subrules = fields.Boolean(string="Has Subrules ?", related="department_id.has_subrules", store=True)
    subrule_department_domain = fields.Char(compute="_compute_subrule_department_domain")
    subrule_department_id = fields.Many2one('hr.department.subrule', string='Subrule', index=True, check_company=True)
    subrule_parent_id = fields.Many2one('hr.employee', string='Subrule Manager', compute="_compute_subrule_department_id", store=True,
                                        index=True, check_company=True)

    # endregion [Fields]

    # region [Onchange Methods]

    @api.onchange("job_id")
    def _onchange_job_id_(self):
        self.ensure_one()
        if self.job_id:
            if self.job_id.department_id:
                self.department_id = self.job_id.department_id.id
                if self.job_id.department_id.manager_id:
                    self.parent_id = self.job_id.department_id.manager_id.id

    # endregion [Onchange Methods]

    # region [Constrains]

    @api.constrains("identification_id")
    def _check_identification_id(self):
        for employee in self:
            if employee.identification_id:
                existing_employee_identification_id = self.env["hr.employee"].search([("identification_id", "=", employee.identification_id), ("id", "!=", employee.id)], limit=1)
                if existing_employee_identification_id:
                    raise ValidationError(f"This Identification ID {employee.identification_id} Exist Before With Employee {existing_employee_identification_id.name}")

    @api.constrains("code")
    def _check_code(self):
        for employee in self:
            if employee.code:
                existing_employee_code_id = self.env["hr.employee"].search(
                    [("code", "=", employee.code), ("id", "!=", employee.id)], limit=1)
                if existing_employee_code_id:
                    raise ValidationError(
                        f"This Code {employee.code} Exist Before With Employee {existing_employee_code_id.name}")

    # endregion [Constrains]

    # region [Compute Methods]

    @api.depends('code', 'name')
    def _compute_complete_name(self):
        for record in self:
            code = '[' + record.code + ']' if record.code else ''
            display_name = f'{code} {record.name}'
            record.complete_name = display_name

    @api.depends('department_id')
    def _compute_parent_id(self):
        # for employee in self.filtered('department_id.manager_id'):
        for employee in self:
            if employee.department_id.manager_id:
                if employee.department_id.manager_id.id != employee.ids[0]:
                    employee.parent_id = employee.department_id.manager_id
                else:
                    if employee.department_id.parent_id and employee.department_id.parent_id.manager_id:
                        if employee.department_id.parent_id.manager_id.id != employee.ids[0]:
                            employee.parent_id = employee.department_id.parent_id.manager_id.id
                        else:
                            employee.parent_id = False
                    else:
                        employee.parent_id = False
            else:
                if employee.department_id.parent_id and employee.department_id.parent_id.manager_id:
                    if employee.department_id.parent_id.manager_id.id != employee.ids[0]:
                        employee.parent_id = employee.department_id.parent_id.manager_id.id
                    else:
                        employee.parent_id = False
                else:
                    employee.parent_id = False

    @api.onchange("subrule_department_id", "subrule_department_id.manager_id",
                  "subrule_department_id.parent_id", "subrule_department_id.parent_id.manager_id")
    @api.depends("subrule_department_id", "subrule_department_id.manager_id",
                 "subrule_department_id.parent_id", "subrule_department_id.parent_id.manager_id")
    def _compute_subrule_department_id(self):
        for emp in self:
            if emp.subrule_department_id:
                if emp.subrule_department_id.manager_id:
                    if not emp.subrule_department_id.manager_id.id == emp.ids[0]:
                        emp.subrule_parent_id = emp.subrule_department_id.manager_id.id
                    else:
                        if emp.subrule_department_id.parent_id and emp.subrule_department_id.parent_id.manager_id:
                            if not emp.subrule_department_id.parent_id.manager_id.id == emp.ids[0]:
                                emp.subrule_parent_id = emp.subrule_department_id.parent_id.manager_id.id
                            else:
                                emp.subrule_parent_id = False
                        else:
                            emp.subrule_parent_id = False
                else:
                    if emp.subrule_department_id.parent_id and emp.subrule_department_id.parent_id.manager_id:
                        if not emp.subrule_department_id.parent_id.manager_id.id == emp.ids[0]:
                            emp.subrule_parent_id = emp.subrule_department_id.parent_id.manager_id.id
                        else:
                            emp.subrule_parent_id = False
                    else:
                        emp.subrule_parent_id = False
            else:
                emp.subrule_parent_id = False

    @api.depends("has_subrules", "department_id", "department_id.has_subrules", "department_id.subrule_department_ids")
    def _compute_subrule_department_domain(self):
        for employee in self:
            if employee.has_subrules and employee.department_id and employee.department_id.has_subrules and employee.department_id.subrule_department_ids:
                subrule_ids = employee.department_id.subrule_department_ids
                subrule_department_domain = json.dumps([('id', 'in', employee.department_id.subrule_department_ids.ids)])
                employee.subrule_department_domain = subrule_department_domain
            else:
                employee.subrule_department_domain = "[]"

    def _compute_iqama_count(self):
        for employee in self:
            iqama_count = self.env["hr.employee.iqama.line"].sudo().search_count([("employee_id", "=", employee.id)])
            if iqama_count == 0:
                iqama_count = self.env["hr.employee.iqama"].sudo().search_count(
                    [("employee_id", "=", employee.id)])
            employee.iqama_count = iqama_count

    def _compute_insurance_count(self):
        for employee in self:
            insurance_count = self.env["hr.employee.medical.insurance.line"].sudo().search_count([("employee_id", "=", employee.id)])
            if insurance_count == 0:
                insurance_count = self.env["hr.employee.medical.insurance"].sudo().search_count(
                    [("employee_id", "=", employee.id)])
            employee.insurance_count = insurance_count

    # endregion [Compute Methods]

    # region [Onchange Methods]

    @api.onchange("department_id")
    def _onchange_department_id_(self):
        self.ensure_one()
        if self.department_id:
            if self.department_id.resource_calendar_id:
                self.resource_calendar_id = self.department_id.resource_calendar_id.id

    # endregion [Onchange Methods]

    # region [Actions]

    def open_related_iqamas(self):
        self.ensure_one()
        form_id = self.env.ref('pr_hr.hr_employee_iqama_view_form').id
        list_id = self.env.ref('pr_hr.hr_employee_iqama_view_tree').id
        action = {
                'type': 'ir.actions.act_window',
                'name': _(f'{self.name} IQAMA'),
                'res_model': 'hr.employee.iqama',
                'view_type': 'list',
                'view_mode': 'list',
                'views': [[list_id, 'list'], [form_id, 'form']],
                'domain': [('employee_id', '=', self.id)],
            }
        iqama_line_ids = self.env["hr.employee.iqama.line"].sudo().search([("employee_id", "=", self.id)])
        iqama_ids = self.env["hr.employee.iqama"].sudo().search([("employee_id", "=", self.id)])
        if iqama_line_ids or iqama_ids:
            return action
        else:
            return {
                "type": "ir.actions.act_window",
                'res_model': 'hr.employee.iqama',
                "views": [[False, "form"]],
                "view_mode": 'form',
                "context": {'default_employee_id': self.id},
            }

    def open_related_insurance(self):
        self.ensure_one()
        form_id = self.env.ref('pr_hr.hr_employee_medical_insurance_view_form').id
        list_id = self.env.ref('pr_hr.hr_employee_medical_insurance_view_tree').id
        action = {
                'type': 'ir.actions.act_window',
                'name': _(f'{self.name} Medical Insurance'),
                'res_model': 'hr.employee.medical.insurance',
                'view_type': 'list',
                'view_mode': 'list',
                'views': [[list_id, 'list'], [form_id, 'form']],
                'domain': [('employee_id', '=', self.id)],
            }
        insurance_line_ids = self.env["hr.employee.medical.insurance.line"].sudo().search([("employee_id", "=", self.id)])
        insurance_ids = self.env["hr.employee.medical.insurance"].sudo().search([("employee_id", "=", self.id)])
        if insurance_line_ids or insurance_ids:
            return action
        else:
            return {
                "type": "ir.actions.act_window",
                'res_model': 'hr.employee.medical.insurance',
                "views": [[False, "form"]],
                "view_mode": 'form',
                "context": {'default_employee_id': self.id},
            }

    def set_out_of_service(self):
        """
        This Method to Change Employee State to Out Of Service
        Should be inherited in EOS Module
        :return:
        """
        for employee in self:
            return True

    # endregion [Actions]

    # region [Set In Service Methods]

    def set_in_service(self):
        """

        """
        for employee in self:
            # Check the Required Field (Call the method)
            missed_required_fields = employee.check_in_service_required_fields()
            if missed_required_fields:
                # If some required fields aren't added → Raise error
                message = '\n'.join(missed_required_fields)
                raise ValidationError(
                    f"To Set Employee {employee.name} In Service You Must Set The Following Required Data\n{message}")

            # Update Employee State to In Service (Noe Employee can do all processes in the system)
            employee.write(
                {'state': 'in_service'})
            return True

    def check_in_service_required_fields(self):
        """
        Check All Required Fields to Convert Employee to In Service
        This Method should be inherited in other modules (hr_contract, hr_project, hr_account, ...)
        :return: List of missed required fields
        """
        missed_required_fields = []
        for employee in self:
            if not employee.code:
                missed_required_fields.append('Code')
            if not employee.name:
                missed_required_fields.append('Name')
            if not employee.gender:
                missed_required_fields.append('Gender')
            if not employee.job_id:
                missed_required_fields.append('Job Position')
            if not employee.department_id:
                missed_required_fields.append('Department')
            if not employee.country_id:
                missed_required_fields.append('Nationality')
            if not employee.identification_id:
                missed_required_fields.append('Identification No')
            if not employee.work_email:
                missed_required_fields.append('Work Email')
            if not employee.work_phone:
                missed_required_fields.append('Work Phone')
            if not employee.company_id:
                missed_required_fields.append('Employee Company')
            # if not employee.bank_account_id:
            #     missed_required_fields.append('Bank Account')
            return missed_required_fields

    # endregion [Set In Service Methods]
