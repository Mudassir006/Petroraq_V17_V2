from odoo import fields, models, api
from odoo.exceptions import ValidationError


class AssetLocation(models.Model):
    _name = "asset.location"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Asset Location"
    _order = "id"
    _rec_name = 'name'

    name = fields.Char(string="Name", required=True, tracking=True)
    company_id = fields.Many2one('res.company', required=True, string="Company", default=lambda self: self.env.company,)
    is_default = fields.Boolean(string="Default", tracking=True)
    is_scrap = fields.Boolean(string="Scrap", tracking=True)
    asset_line = fields.One2many(comodel_name="asset.detail", inverse_name="location_id")

    def unlink(self):
        for location in self:
            asset_ids = self.env["asset.detail"].search([("location_id", "=", location.id)])
            if asset_ids:
                raise ValidationError("This Location Already Has Many Assets, So You Can Not Delete !!")
        return super().unlink()

