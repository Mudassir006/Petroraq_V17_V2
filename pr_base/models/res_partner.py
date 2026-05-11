# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    partner_code = fields.Char(string='Code', required=False)
    arabic_name = fields.Char(string='Arabic Name', required=False)
    arabic_street = fields.Char(string='Arabic Street', required=False)
    arabic_street2 = fields.Char(string='Arabic Street', required=False)

    def _get_auto_code_sequence_code(self):
        self.ensure_one()
        if self.customer_rank > 0:
            return 'res.partner.customer.code'
        if self.supplier_rank > 0:
            return 'res.partner.vendor.code'
        return False

    def _assign_missing_partner_codes(self):
        for partner in self.filtered(lambda p: not p.partner_code):
            sequence_code = partner._get_auto_code_sequence_code()
            if sequence_code:
                partner.partner_code = self.env['ir.sequence'].next_by_code(sequence_code)

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        partners._assign_missing_partner_codes()
        return partners

    def write(self, vals):
        res = super().write(vals)
        if {'customer_rank', 'supplier_rank', 'partner_code'} & set(vals):
            self._assign_missing_partner_codes()
        return res

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

