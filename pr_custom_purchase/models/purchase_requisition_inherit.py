from odoo import models, fields


class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'

    rejection_reason = fields.Text(string='Reason for Rejection')

    def write(self, vals):
        res = super().write(vals)
        if 'rejection_reason' in vals:
            for rec in self:
                # Sync to related custom.pr by name if it exists
                custom_pr = self.env['custom.pr'].sudo().search([('name', '=', rec.name)], limit=1)
                if custom_pr:
                    custom_pr.sudo().write({'rejection_reason': rec.rejection_reason})
        return res


