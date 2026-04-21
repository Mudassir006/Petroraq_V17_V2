from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import random


class HrEmployee(models.Model):
    """
    Extension to the existed model hr.employee in HR Module
    Additional Fields:
        - contract_employment_type: Type of employment [Employment, Recruitment, Tranfere Kafala)
    Updated Fields:
        -  contract_id : Add groups to the field
    """
    # region [Initial]
    _inherit = 'hr.employee'
    # endregion [Initial]

    # region [Fields]
    contract_employment_type = fields.Selection([('employment', 'Employment'),
                                                 ('recruitment', 'Recruitment'),
                                                 ('transfer', 'Transfer Kafala')],
                                                string='Contract Employment Type',
                                                related='contract_id.contract_employment_type',
                                                store=True,
                                                tracking=True,
                                                help='The Type Of Contract Employment\n')
    joining_date = fields.Date(string="Joining Date",
                               related="contract_id.joining_date",
                               store=True,
                               tracking=True)

    # endregion [Fields]

    # region [Methods]

    def check_in_service_required_fields(self):
        """
           Inherited from bof_hr Module
           To Check All Required field of an employee to convert to In Service → Valid Employee
           Here We check Contract State and must be running contract
           :return: List of missed required fields
       """
        missed_required_fields = super().check_in_service_required_fields()
        for rec in self:
            if not rec.contract_id.state == 'open':
                missed_required_fields.append('Running Contract')
            return missed_required_fields

    @api.onchange('work_email', 'mobile_phone')
    @api.constrains('work_email', 'mobile_phone')
    def set_email_mobile(self):
        for employee in self:
            if employee.work_email:
                employee.work_contact_id.sudo().email = employee.work_email
            if employee.mobile_phone:
                employee.work_contact_id.sudo().mobile = employee.mobile_phone

    @api.onchange("department_id")
    def _onchange_department_id_(self):
        res = super()._onchange_department_id_()
        if self.department_id:
            if self.department_id.resource_calendar_id and self.contract_id:
                self.contract_id.resource_calendar_id = self.department_id.resource_calendar_id.id
        return res

    def action_open_contract(self):
        action = super().action_open_contract()
        action['target'] = 'current'
        return action

    # endregion [Methods]
