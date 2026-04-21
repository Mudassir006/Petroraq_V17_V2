from odoo import models, fields


class ResUsers(models.Model):
    _inherit = "res.users"

    supervisor_user_id = fields.Many2one(
        "res.users",
        string="Supervisor",

        help="Direct supervisor responsible for approving this user's PRs.",
    )
