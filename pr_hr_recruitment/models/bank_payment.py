
from odoo import models, fields, tools, api, exceptions, _
from odoo.exceptions import UserError, ValidationError


class BankPayment(models.Model):
    _inherit = 'pr.account.bank.payment'

    work_permit_id = fields.Many2one('hr.work.permit', readonle=True)

    def open_work_permit(self):
        self.ensure_one()
        view = self.env.ref("pr_hr_recruitment.hr_work_permit_form_view")
        if self.work_permit_id:
            action = {
                "name": _("Work Permit"),
                "type": "ir.actions.act_window",
                "res_model": "hr.work.permit",
                "views": [[view.id, "form"]],
                "res_id": self.work_permit_id.id,
                "target": "current",
            }
            return action
        return None

    def action_post(self):
        res = super().action_post()
        for rec in self:
            if rec.work_permit_id:
                rec.work_permit_id.sudo().state = "issued"
                rec.work_permit_id.sudo().payment_state = "paid"
        return res