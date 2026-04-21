import threading

from odoo import api, fields, models


class Users(models.Model):
    _inherit = 'res.users'

    # this field is for the SaaS to charge instances having marketplace users. See the module viin_marketplace
    marketplace_merchant = fields.Boolean(
        compute='_compute_marketplace_merchant', string='Marketplace Merchant User', store=True,
        help="External user with limited access to marketplace merchant functionalities"
        )

    @api.depends('groups_id')
    def _compute_marketplace_merchant(self):
        self.marketplace_merchant = False

    def _default_groups(self):
        """
        Skip in other tests
        """
        if self.env.registry.in_test_mode() or getattr(threading.current_thread(), 'testing', False):
            self.env['ir.config_parameter'].sudo().set_param("base_setup.default_user_rights_minimal", False)
        return super()._default_groups()

    def _apply_groups_to_existing_employees(self):
        """
        Skip in other tests
        """
        if self.env.registry.in_test_mode() or getattr(threading.current_thread(), 'testing', False):
            self.env['ir.config_parameter'].sudo().set_param("base_setup.default_user_rights_minimal", False)
        return super()._apply_groups_to_existing_employees()
