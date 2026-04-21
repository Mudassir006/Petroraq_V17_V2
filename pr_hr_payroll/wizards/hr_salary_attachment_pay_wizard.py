from odoo import api, models, fields
from datetime import datetime, date
import json


class HrSalaryAttachmentPayWizard(models.TransientModel):
    _name = 'hr.salary.attachment.pay.wizard'

    account_id = fields.Many2one('account.account', string='Account Code', required=True)
    account_name = fields.Char(string='Account Name', related="account_id.name")
    salary_attachment_id = fields.Many2one('hr.salary.attachment', string='Salary Attachment', required=True)
    accounting_date = fields.Date(string="Accounting Date", required=True, default=fields.Date.today)

    def action_paid(self):
        for wizard in self:
            journal_entry_id = self.env['account.move'].sudo().create({
                'ref': wizard.salary_attachment_id.description,
                'date': wizard.accounting_date,
                'move_type': 'entry',
            })
            if journal_entry_id:
                journal_entry_id = journal_entry_id.with_context(check_move_validity=False)
                move_line = self.env['account.move.line'].with_context(check_move_validity=False,
                                                                       skip_invoice_sync=True)
                line_ids = [
                    move_line.create({
                        "move_id": journal_entry_id.id,
                        "account_id": wizard.account_id.id,
                        "name": f"Debit Line For {wizard.salary_attachment_id.description}",
                        "analytic_distribution": {str(wizard.salary_attachment_id.employee_ids[0].id): 100},
                        "debit": wizard.salary_attachment_id.total_amount,
                        "credit": 0.0,
                    }),
                    move_line.create({
                        "move_id": journal_entry_id.id,
                        "account_id": wizard.salary_attachment_id.deduction_type_id.account_id.id,
                        "name": f"Credit Line For {wizard.salary_attachment_id.description}",
                        "analytic_distribution": {str(wizard.salary_attachment_id.employee_ids[0].id): 100},
                        "credit": wizard.salary_attachment_id.total_amount,
                        "debit": 0.0,
                    })
                ]

                journal_entry_id.action_post()
                wizard.salary_attachment_id.paid_move_id = journal_entry_id.id
                wizard.salary_attachment_id.payment_state = "paid"

