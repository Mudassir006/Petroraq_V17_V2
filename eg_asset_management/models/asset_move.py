from odoo import fields, models, api
from datetime import datetime
from odoo.exceptions import ValidationError


class AssetMove(models.Model):
    _name = "asset.move"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Asset Move"
    _order = "id"
    _rec_name = 'name'

    name = fields.Char(string="Name", required=True, tracking=True)
    company_id = fields.Many2one('res.company', required=True, string="Company", default=lambda self: self.env.company,)
    location_id = fields.Many2one(comodel_name="asset.location", string="Source Location", ondelete="restrict")
    location_dest_id = fields.Many2one(comodel_name="asset.location", string="Destination Location", ondelete="restrict")
    asset_id = fields.Many2one(comodel_name="asset.detail", string="Asset", ondelete="restrict")
    state = fields.Selection([('draft', 'Draft'),('done', 'Done'),('cancel', 'Cancel')], string='State', default="draft")

    @api.model
    def create(self, vals):
        res = super().create(vals)
        res.name = self.env["ir.sequence"].next_by_code("asset.move", sequence_date=datetime.now().year) or "New"
        return super(AssetMove, self).create(vals)

    @api.onchange("asset_id")
    def onchange_asset(self):
        self.ensure_one()
        self.location_id = self.asset_id.location_id.id

    def move_asset(self):
        for asset_id in self:
            if asset_id.asset_id:
                asset_id.asset_id.location_id = asset_id.location_dest_id.id
            asset_id.state = "done"

    def cancel_move(self):
        for asset_id in self:
            asset_id.state = "cancel"

    def unlink(self):
        if self.state != 'draft':
            raise ValidationError("This Asset Move Should Be Draft To Can Delete !!")
        return super().unlink()