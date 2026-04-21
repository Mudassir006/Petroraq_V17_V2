from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ExpenseBucket(models.Model):
    _inherit = "pr.expense.bucket"

    work_order_id = fields.Many2one("pr.work.order", string="Work Order", tracking=True)

    @api.onchange("scope")
    def _onchange_scope_work_order(self):
        for rec in self:
            if rec.scope == "department":
                rec.work_order_id = False

    @api.constrains("scope", "work_order_id")
    def _check_scope_target_work_order(self):
        for rec in self:
            if rec.scope == "project" and not rec.work_order_id:
                raise ValidationError(_("Work Order is required when scope is Project."))

    def write(self, vals):
        if "work_order_id" in vals:
            for rec in self:
                if rec.state == "approved":
                    raise ValidationError(_("Approved expense bucket cannot be edited."))
        return super().write(vals)