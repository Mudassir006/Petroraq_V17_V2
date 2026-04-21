from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from hijri_converter import Gregorian
from datetime import date


class HREmployeeIqamaLineAddWizard(models.Model):
    """
    """

    # region [Initial]
    _name = 'hr.employee.iqama.line.add.wizard'
    _description = 'Iqama Line Add'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    # endregion [Initial]

    # region [Fields]

    from_date = fields.Date(string="From Date", required=True)
    to_date = fields.Date(string="To Date", required=True)
    iqama_id = fields.Many2one('hr.employee.iqama', string='Iqama', required=True, readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, readonly=True)
    relation_id = fields.Many2one('hr.employee.dependent.relation', string='Relation', required=True)
    country_id = fields.Many2one('res.country', string='Nationality', required=False)
    identification_id = fields.Char(string='Iqama No.', required=True)
    place_of_issue = fields.Char(string="Place Of Issue")
    expiry_date = fields.Date(string="Expiry Date", required=True)
    expiry_date_hijri = fields.Char(string="Expiry Date Hijri", required=False, compute="_compute_expiry_date_hijri")
    birthday = fields.Date(string='Date Of Birth', required=False, tracking=True)
    age = fields.Float(string='Age', digits=(16, 2), compute='get_employee_age', tracking=True)
    phone = fields.Char(string='Phone', tracking=True)
    amount = fields.Float(string="Amount", required=True)
    check_self_relation = fields.Boolean(compute="_compute_check_self_relation")
    check_renews = fields.Boolean(readonly=True)

    # endregion [Fields]

    @api.onchange("expiry_date")
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

    @api.onchange("to_date")
    def _onchange_to_date(self):
        for line in self:
            if line.to_date:
                line.expiry_date = line.to_date

    @api.onchange('birthday')
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

    @api.onchange("relation_id")
    @api.depends("relation_id")
    def _compute_check_self_relation(self):
        for rec in self:
            self_relation_id = self.env.ref('pr_hr.employee_dependent_relationship_self').id
            if rec.relation_id and rec.relation_id.id == self_relation_id:
                rec.check_self_relation = True
            else:
                rec.check_self_relation = False

    def action_renew(self):
        for rec in self:
            if rec.amount == 0:
                raise ValidationError("Amount Of IQAMA Should Be Greater Than 0 (Zero)")
            iqama_line_id = self.env["hr.employee.iqama.line"].sudo().create({
                "iqama_id": rec.iqama_id.id,
                "employee_id": rec.employee_id.id,
                "relation_id": rec.relation_id.id,
                "identification_id": rec.identification_id,
                "place_of_issue": rec.place_of_issue if rec.place_of_issue else False,
                "from_date": rec.from_date,
                "to_date": rec.to_date,
                "expiry_date": rec.expiry_date,
                "expiry_date_hijri": rec.expiry_date_hijri,
                "country_id": rec.country_id.id if rec.country_id else False,
                "birthday": rec.birthday if rec.birthday else False,
                "age": rec.age if rec.age else False,
                "phone": rec.phone if rec.phone else False,
                "amount": rec.amount if rec.amount else False,
                "state": "initiated",
            })
            return iqama_line_id





