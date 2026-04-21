
from odoo import models, fields, tools, api, exceptions, _
from odoo.exceptions import UserError, ValidationError


class HrSalaryAttachmentType(models.Model):
    _inherit = 'hr.salary.attachment.type'

    account_id = fields.Many2one('account.account', string='Account Code', required=True,
                                 ondelete='restrict', tracking=True, index=True, )
    account_name = fields.Char(string='Account Name', related="account_id.name", store=True,
                               tracking=True)