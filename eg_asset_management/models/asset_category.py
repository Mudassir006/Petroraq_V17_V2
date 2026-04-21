from odoo import fields, models, api
from odoo.exceptions import ValidationError


class AssetCategory(models.Model):
    _name = "asset.category"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Asset Category"
    _order = "id"
    _rec_name = 'name'

    name = fields.Char(string="Name", required=True, tracking=True)
    company_id = fields.Many2one('res.company', required=True, string="Company", default=lambda self: self.env.company,)

    def unlink(self):
        for category in self:
            asset_ids = self.env["asset.detail"].search([("category_id", "=", category.id)])
            if asset_ids:
                raise ValidationError("This Category Already Has Many Assets, So You Can Not Delete !!")
        return super().unlink()