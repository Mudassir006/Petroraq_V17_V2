from odoo import fields, models, api
from datetime import datetime
from odoo.exceptions import ValidationError


class AssetDetail(models.Model):
    _name = "asset.detail"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Asset Detail"
    _order = "id"
    _rec_name = 'name'

    name = fields.Char(string="Name", required=True, tracking=True)
    asset_image = fields.Binary(string="Image")
    company_id = fields.Many2one('res.company', required=True, string="Company", default=lambda self: self.env.company,)
    category_id = fields.Many2one(comodel_name="asset.category", string="Category", required=True, tracking=True, ondelete="restrict")
    asset_code = fields.Char(string="Asset Code", tracking=True)
    asset_model = fields.Char(string="Asset Model", tracking=True)
    serial_no = fields.Char(string="Serial No.", tracking=True)
    purchase_date = fields.Date(string="Purchase Date", tracking=True)
    purchase_value = fields.Float(string="Purchase Value", tracking=True)
    location_id = fields.Many2one(comodel_name="asset.location", string="Current Location", tracking=True, ondelete="restrict")
    employee_id = fields.Many2one(comodel_name="hr.employee", string="Employee", tracking=True, ondelete="restrict")
    vendor_id = fields.Many2one(comodel_name="res.partner", string="Vendor", tracking=True, ondelete="restrict")
    warranty_start = fields.Date(string="Warranty Start", tracking=True)
    warranty_end = fields.Date(string="Warranty End", tracking=True)
    note = fields.Html(string="Note")
    state = fields.Selection([('draft', 'New'), ('active', 'Active'), ('scrap', 'Scrap')], string='State', default="draft", tracking=True)

    @api.model
    def create(self, vals):
        location_id = self.env["asset.location"].search([("is_default", "=", True)], limit=1)
        vals["location_id"] = location_id.id if location_id and not vals.get("location_id") else None
        res = super(AssetDetail, self).create(vals)
        res.asset_code = self.env["ir.sequence"].next_by_code("asset.detail", sequence_date=datetime.now().year) or "New"
        return res

    def scrap_asset(self):
        for asset_id in self:
            location_id = self.env["asset.location"].search([("is_scrap", "=", True)], limit=1)
            if location_id:
                asset_id.state = "scrap"

    def confirm_asset(self):
        for asset_id in self:
            asset_id.state = "active"

    def unlink(self):
        if self.state != 'draft':
            raise ValidationError("This Asset Should Be New To Can Delete !!")
        return super().unlink()