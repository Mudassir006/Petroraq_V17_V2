from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from hijri_converter import Gregorian
from datetime import date
from dateutil.relativedelta import relativedelta


class HREmployeeMedicalInsurance(models.Model):
    """

    """

    # region [Initial]
    _name = 'hr.employee.medical.insurance'
    _description = 'Employee Medical Insurance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "id"
    # endregion [Initial]

    # region [Fields]
    name = fields.Char(string='Description', required=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, ondelete='restrict', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=False, ondelete='restrict', tracking=True,
                                 related="employee_id.company_id", store=True)
    identification_id = fields.Char(string='Iqama No.', required=True, tracking=True)
    insurance_company = fields.Char(string="Insurance Company", required=True, tracking=True)
    insurance_category = fields.Char(string="Insurance Category", required=True, tracking=True)
    expiry_date = fields.Date(string="Expiry Date", required=True, tracking=True)
    expiry_date_hijri = fields.Char(string="Expiry Date Hijri", required=False, compute="_compute_expiry_date_hijri", store=True, tracking=True)
    state = fields.Selection([('draft', 'Initiated'),
                              ('pending_approval', 'Pending Approval'),
                              ('approve', 'Approved'),
                              ('valid', 'Valid'),
                              ('expired', 'Expired')], default="draft", required=False, string="Status", tracking=True)
    active = fields.Boolean(string="Active", default=True, tracking=True)
    insurance_line_ids = fields.One2many("hr.employee.medical.insurance.line", "insurance_id", string="Insurance Lines")
    check_renews = fields.Boolean(compute="_compute_check_renews")

    # endregion [Fields]

    # region [Methods]

    @api.constrains("identification_id")
    def _check_identification_id(self):
        for employee in self:
            if employee.identification_id:
                existing_employee_identification_id = self.env["hr.employee.medical.insurance"].search(
                    [("identification_id", "=", employee.identification_id), ("id", "!=", employee.id)], limit=1)
                if existing_employee_identification_id:
                    raise ValidationError(
                        f"This Identification ID {employee.identification_id} Exist Before With The Employee {existing_employee_identification_id.name}")

    @api.depends("expiry_date")
    def _compute_expiry_date_hijri(self):
        for dependent in self:
            if dependent.expiry_date:
                # Convert it to Hijri date
                gregorian_date_obj = Gregorian(dependent.expiry_date.year, dependent.expiry_date.month, dependent.expiry_date.day)
                hijri_date = gregorian_date_obj.to_hijri()
                dependent.expiry_date_hijri = f'{hijri_date}'
            else:
                dependent.expiry_date_hijri = False

    def action_request_approval(self):
        for rec in self:
            rec.state = "pending_approval"

    def action_approve(self):
        for rec in self:
            rec.state = "approve"

    def action_renew(self):
        """
        """
        self_relation_id = self.env.ref("pr_hr.employee_dependent_relationship_self")
        self.ensure_one()
        new_line_from_date = False
        if self.insurance_line_ids:
            to_date = max(self.insurance_line_ids.mapped("to_date"))
            new_line_from_date = to_date + relativedelta(days=1)
        return {
            'name': self.name,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.employee.medical.insurance.line.add.wizard',
            'context': {
                    'default_insurance_id': self.id,
                    'default_employee_id': self.employee_id.id,
                    'default_relation_id': self_relation_id.id,
                    'default_identification_id': self.identification_id,
                    'default_check_renews': self.check_renews,
                    'default_from_date': new_line_from_date ,
                    'default_insurance_company': self.insurance_company ,
                    'default_insurance_category': self.insurance_category ,
                },
            'target': 'new',
        }

    @api.depends("insurance_line_ids")
    def _compute_check_renews(self):
        for iqama in self:
            if iqama.insurance_line_ids or len(iqama.insurance_line_ids) >= 1:
                iqama.check_renews = True
            else:
                iqama.check_renews = False

    # endregion [Methods]


class HREmployeeMedicalInsureLine(models.Model):
    """

    """

    # region [Initial]
    _name = 'hr.employee.medical.insurance.line'
    _description = 'Employee Medical Insurance Lines'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "id"
    # endregion [Initial]

    # region [Fields]
    name = fields.Char(string='Description', required=False, tracking=True)
    insurance_id = fields.Many2one('hr.employee.medical.insurance', string='Employee Insurance', required=True, ondelete='restrict', tracking=True)
    sequence_ref = fields.Integer('No', compute="_compute_sequence_ref", copy=False)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, ondelete='restrict', tracking=True,
                                  related="insurance_id.employee_id", store=True)
    company_id = fields.Many2one('res.company', string='Company', required=False, ondelete='restrict', tracking=True,
                                 related="employee_id.company_id", store=True)
    relation_id = fields.Many2one('hr.employee.dependent.relation', string='Relation', required=True, ondelete='restrict', tracking=True)
    country_id = fields.Many2one('res.country', string='Nationality', required=False, ondelete='restrict', tracking=True)
    identification_id = fields.Char(string='Iqama No.', required=True, tracking=True)
    insurance_company = fields.Char(string="Insurance Company", required=True, tracking=True)
    insurance_category = fields.Char(string="Insurance Category", required=True, tracking=True)
    from_date = fields.Date(string="From Date", required=True, tracking=True)
    to_date = fields.Date(string="To Date", required=True, tracking=True)
    expiry_date = fields.Date(string="Expiry Date", required=True, tracking=True)
    expiry_date_hijri = fields.Char(string="Expiry Date Hijri", required=False, compute="_compute_expiry_date_hijri", store=True, tracking=True)
    birthday = fields.Date(string='Date Of Birth', required=False, tracking=True)
    age = fields.Float(string='Age', digits=(16, 2), compute='get_employee_age', tracking=True)
    phone = fields.Char(string='Phone', tracking=True)
    amount = fields.Float(string="Amount", required=True)
    state = fields.Selection([('initiated', 'Initiated'), ('in_progress', 'In Progress'), ('issued', 'Issued')],
                                     default="initiated", required=False, string="Request Status", tracking=True)
    check_self_relation = fields.Boolean(compute="_compute_check_self_relation")

    # endregion [Fields]

    # region [Methods]

    @api.depends('insurance_id.insurance_line_ids')
    def _compute_sequence_ref(self):
        for line in self:
            count = 0
            if line.insurance_id.insurance_line_ids:
                for ln in line.insurance_id.insurance_line_ids:
                    count += 1
                    ln.sequence_ref = count
            else:
                line.sequence_ref = 0

    @api.depends("relation_id")
    def _compute_check_self_relation(self):
        for rec in self:
            self_relation_id = self.env.ref('pr_hr.employee_dependent_relationship_self').id
            if rec.relation_id and rec.relation_id.id == self_relation_id:
                rec.check_self_relation = True
            else:
                rec.check_self_relation = False

    @api.depends("expiry_date")
    def _compute_expiry_date_hijri(self):
        for line in self:
            if line.expiry_date:
                # Convert it to Hijri date
                gregorian_date_obj = Gregorian(line.expiry_date.year, line.expiry_date.month, line.expiry_date.day)
                hijri_date = gregorian_date_obj.to_hijri()
                line.expiry_date_hijri = f'{hijri_date}'
            else:
                line.expiry_date_hijri = False

    @api.depends('birthday')
    def get_employee_age(self):
        """
        Method Description:
        - This method computes the age of the dependent based on the birthday.
        - Age is calculated as the difference between the current date and the birthday.
        - The result is formatted to two decimal places.
        """
        for rec in self:
            if rec.birthday:
                today = datetime.today()
                age = fields.Date.from_string(str(today)) - fields.Date.from_string(str(rec.birthday))
                years = age.days // 365
                months = (age.days % 365) // 30
                months = months / 12
                rec.age = "{:.2f}".format(years + months)
            else:
                rec.age = 0

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        """
        Method Description:
        - This method triggers when the employee field changes.
        - It automatically sets the country based on the selected employee’s nationality.
        """
        for rec in self:
            if rec.employee_id:
                rec.country_id = rec.employee_id.country_id and rec.employee_id.country_id.id or False

    @api.onchange('insurance_id')
    def _onchange_insurance_id(self):
        """
        Method Description:
        - This method triggers when the employee field changes.
        - It automatically sets the country based on the selected employee’s nationality.
        """
        for rec in self:
            if rec.insurance_id:
                rec.identification_id = rec.insurance_id.identification_id.id if rec.insurance_id.identification_id else False

    @api.constrains("state")
    def _check_state(self):
        for line in self:
            if line.state == "issued":
                self_relation_id = self.env.ref("pr_hr.employee_dependent_relationship_self")
                if line.relation_id.id == self_relation_id.id:
                    line.insurance_id.sudo().write({
                        "expiry_date": line.expiry_date,
                        "expiry_date_hijri": line.expiry_date_hijri,
                        "insurance_company": line.insurance_company if line.insurance_company else False,
                        "insurance_category": line.insurance_category if line.insurance_category else False,
                    })
                line.insurance_id.state = "valid"

    def action_post(self):
        for rec in self:
            print("POST")

    # endregion [Methods]


