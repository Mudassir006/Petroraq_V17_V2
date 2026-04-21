from odoo import _, api, models
from odoo.exceptions import AccessError


class AccountMove(models.Model):
    _inherit = 'account.move'

    _BLOCKED_MOVE_TYPES = {
        'out_invoice',
        'in_invoice',
        'out_refund',
        'in_refund',
        'out_receipt',
        'in_receipt',
    }

    def _allow_restricted_invoice_create(self, vals):
        """Allow non-direct invoice creation flows (e.g., Sale Order invoicing)."""
        ctx = self.env.context
        if ctx.get('active_model') == 'sale.order':
            return True

        # Sale-generated invoices usually carry source order reference.
        if vals.get('invoice_origin'):
            return True

        return False

    @api.model_create_multi
    def create(self, vals_list):
        access_records = self.env['access.management'].sudo().search([
            ('active', '=', True),
            ('user_ids', 'in', self.env.user.id),
            ('restrict_invoice_create', '=', True),
        ])
        access_records = access_records.filtered(
            lambda x: x.is_apply_on_without_company or self.env.company.id in x.company_ids.ids
        )

        if access_records:
            for vals in vals_list:
                move_type = vals.get('move_type') or self.env.context.get('default_move_type') or 'entry'
                if move_type in self._BLOCKED_MOVE_TYPES and not self._allow_restricted_invoice_create(vals):
                    raise AccessError(_(
                        "Direct creation of Invoices/Bills/Credit Notes/Receipts is not allowed. "
                        "You can still create Journal Entries."
                    ))

        return super().create(vals_list)