# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.exceptions import ValidationError



class HrContractGosi(models.Model):
    """
    - GOSI: General Organization for Social Insurance
    - This model is to record settings of Gosi deduction
    - Constrain to add only one record in database
    - add paid portions by company and by employee for citizen and resident
    - this setting will affect salary deductions
    - in Data already one default record is added, can be used
    """
    # region [Initial]
    _name = 'hr.contract.gosi'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Hr Contract Gosi'
    # endregion

    # region [Fields]
    name = fields.Char(string='Name', required=True, tracking=True)
    citizen_employee_portion = fields.Float(string='Citizen Employee Portion', required=True, tracking=True,
                                            help='The Default Citizen Employee Portion')
    citizen_company_portion = fields.Float(string='Citizen Company Portion', required=True, tracking=True,
                                           help='The Default Citizen Company Portion')
    resident_employee_portion = fields.Float(string='Resident Employee Portion', required=True, tracking=True,
                                             help='The Default Resident Employee Portion')
    resident_company_portion = fields.Float(string='Resident Company Portion', required=True, tracking=True,
                                            help='The Default Resident Company Portion')
    # gosi_salary_rule_ids = fields.Many2many('hr.salary.rule', string='Gosi Salary Rules',
    #                                         domain="[('appears_on_salary_rules_conf', '=', True)]", required=True,
    #                                         tracking=True, help='The Default Gosi Salary Rules')
    lock = fields.Boolean(string='Lock', tracking=True,
                          help='If Lock Is True: All Fields Will Be Readonly And You Can Not Edit'
                               'If Lock Is False: All Field Not Readonly And You Can Edit')
    # endregion [Fields]

    # region [Actions]
    @api.constrains('name')  # You can use any field, but here we use 'name'
    def _check_single_record(self):
        """
        Ensures that only one record can be created in the model.
        """
        if self.search_count([]) > 1:
            raise ValidationError("You can only create one record for this model.")

    def update_gosi(self):
        for rec in self:
            contract_ids = self.env['hr.contract'].sudo().search([('state', 'not in', ['close', 'cancel'])])
            if contract_ids:
                for contract in contract_ids:
                    contract._set_gosi_salary()

    def set_lock(self):
        for gosi in self:
            gosi.lock = True

    def set_unlock(self):
        for gosi in self:
            gosi.lock = False

    # endregion [Actions]

    # region [Compute Methods]

    # endregion [Compute Methods]
