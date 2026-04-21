# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    partner_code = fields.Char(string='Code', required=True)
    arabic_name = fields.Char(string='Arabic Name', required=True)
    arabic_street = fields.Char(string='Arabic Street', required=True)
    arabic_street2 = fields.Char(string='Arabic Street', required=True)

    # # cr_no = fields.Char(string="Customer Registration", copy=False, required=True)
    #
    # @api.constrains("is_company", "vat")
    # def _check_vat_cr_required(self):
    #     for p in self:
    #         # apply only on customers/companies (adjust if you want for vendors too)
    #         if p.is_company:
    #             if not p.vat:
    #                 raise ValidationError(_("VAT is required for company customers."))
    #             if not p.company_registry:
    #                 raise ValidationError(_("CR No. is required for company customers."))
    # cr_no = fields.Char(string="Customer Registration", copy=False, required=True)

