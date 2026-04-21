from odoo import models, fields, tools, api, exceptions, _
from odoo.exceptions import UserError, ValidationError


class HrSalaryAttachment(models.Model):
    _inherit = 'hr.salary.attachment'

    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('open', 'Running'),
            ('close', 'Completed'),
            ('cancel', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
        copy=False,
    )
    payment_state = fields.Selection([("draft", "Draft"), ("paid", "Paid")], default="draft", string="Payment Status",
                                     readonly=True)
    bank_payment_id = fields.Many2one('pr.account.bank.payment', readonle=True)
    paid_move_id = fields.Many2one('account.move', related="bank_payment_id.journal_entry_id", store=True)

    def action_pay(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Advance Allowances Payment',
            'res_model': 'hr.salary.attachment.pay.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_salary_attachment_id': self.id,
            },
        }

    def action_request(self):
        for rec in self:
            # NOTE:
            # BPV auto-creation is intentionally disabled.
            # Creating salary attachments should not generate empty bank payment vouchers.
            # bank_account_id = self.env["account.account"].search([("code", "=", "1001.02.00.07")], limit=1)
            # account_id = bank_account_id if bank_account_id else rec.deduction_type_id.account_id
            # bank_payment_id = self.env["pr.account.bank.payment"].sudo().create({
            #     "account_id": account_id.id,
            # })
            # if bank_payment_id:
            #     rec.bank_payment_id = bank_payment_id.id
            #     bank_payment_id.salary_attachment_id = rec.id
            continue
