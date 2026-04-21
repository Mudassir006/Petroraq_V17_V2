from odoo import fields, models, _
from odoo.exceptions import UserError


class HrPublicHoliday(models.Model):
    _inherit = "hr.public.holiday"

    approval_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("to_approve", "To Approve"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Approval Status",
        default="draft",
        tracking=True,
    )
    approved_by_id = fields.Many2one("res.users", string="Approved By", readonly=True, tracking=True)
    approved_on = fields.Datetime(string="Approved On", readonly=True, tracking=True)

    def write(self, vals):
        if "approval_state" in vals and not self.env.user.has_group("hr.group_hr_manager"):
            raise UserError(_("Only HR Managers can change holiday approval status."))
        return super().write(vals)

    def action_submit_for_approval(self):
        for rec in self:
            rec.write({"approval_state": "to_approve"})

    def action_hr_manager_approve(self):
        if not self.env.user.has_group("hr.group_hr_manager"):
            raise UserError(_("Only HR Managers can approve public holidays."))
        now = fields.Datetime.now()
        for rec in self:
            rec.write({
                "approval_state": "approved",
                "approved_by_id": self.env.user.id,
                "approved_on": now,
                "state": "active",
            })

    def action_hr_manager_reject(self):
        if not self.env.user.has_group("hr.group_hr_manager"):
            raise UserError(_("Only HR Managers can reject public holidays."))
        for rec in self:
            rec.write({
                "approval_state": "rejected",
                "approved_by_id": False,
                "approved_on": False,
                "state": "inactive",
            })