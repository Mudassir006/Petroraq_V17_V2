from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    designation = fields.Char(
        string="Designation",
        help="Designation/title used for customer contact persons in sale inquiries.",
    )
