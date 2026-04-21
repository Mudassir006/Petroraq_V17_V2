
from odoo import models, fields, tools, api, exceptions, _
from odoo.exceptions import UserError, ValidationError


class HrContract(models.Model):
    _inherit = 'hr.contract'

    other_first_payslip = fields.Boolean(string="Other First Payslip", tracking=True)