
from odoo import models, fields, tools, api, exceptions, _
from odoo.exceptions import UserError, ValidationError


class BankPayment(models.Model):
    _inherit = 'pr.account.bank.payment'

    salary_attachment_id = fields.Many2one('hr.salary.attachment', readonle=True)

    def open_salary_attachment(self):
        for rec in self:
            view = self.env.ref("hr_payroll.hr_salary_attachment_view_form")
            if rec.salary_attachment_id:
                action = {
                    "name": _("Advance Allowances"),
                    "type": "ir.actions.act_window",
                    "res_model": "hr.salary.attachment",
                    "views": [[view.id, "form"]],
                    "res_id": rec.salary_attachment_id.id,
                    "target": "current",
                }
                return action

    def action_post(self):
        res = super().action_post()
        for rec in self:
            if rec.salary_attachment_id:
                rec.salary_attachment_id.sudo().state = "open"
        return res