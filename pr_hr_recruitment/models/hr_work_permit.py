from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class HRWorkPermit(models.Model):
    _name = 'hr.work.permit'
    _description = 'HR Work Permit/Iqama Flow'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "id"

    # region [Fields]

    applicant_onboarding_id = fields.Many2one("hr.applicant.onboarding", string="Application Onboarding")
    name = fields.Char(string='Name', required=True)
    employee_id = fields.Many2one("hr.employee", string="Employee", required=True)
    visa_number = fields.Char(string='Visa Number', required=True)
    iqama_profession = fields.Char(string='Iqama & Work Permit Profession', required=True)
    work_permit_fees = fields.Float(string='Iqama & Work Permit Fees', required=True)
    iqama_issuance_date = fields.Date(string='Iqama & Work Permit Issuance Date', required=True)
    iqama_expiry_date = fields.Date(string='Iqama & Work Permit Expiry Date', required=True)
    work_permit_expiry_date = fields.Date(string='Iqama & Work Permit Expiry Date', required=True)
    work_permit_renewal_date = fields.Date('Iqama & Work Permit Renewal Date')
    state = fields.Selection(
        [('draft', 'Draft'),
         ('submit', 'Pending Approval'),
         ('approved', 'Approved'),
         ('issued', 'Issued'),
         ('reject', 'Rejected')],
        string='Status', default='draft')
    payment_state = fields.Selection(
        [('draft', 'Draft'), ('pending', 'Pending'), ('paid', 'Paid')],
        string='Payment Status', default='draft', readonly=True)
    bank_payment_id = fields.Many2one('pr.account.bank.payment', readonle=True)
    paid_move_id = fields.Many2one('account.move', related="bank_payment_id.journal_entry_id", store=True)

    # endregion [Fields]

    @api.onchange("work_permit_expiry_date")
    def _set_work_permit_renewal_date(self):
        for rec in self:
            if rec.work_permit_expiry_date:
                rec.work_permit_renewal_date = rec.work_permit_expiry_date - timedelta(
                    days=30)  # 30 days before expiry

    def action_submit(self):
        for rec in self:
            rec.state = "submit"

    def action_approve(self):
        for rec in self:
            bank_account_id = self.env["account.account"].sudo().search([("code", "=", "1001.02.00.07")], limit=1)
            account_id = bank_account_id if bank_account_id else self.env["account.account"].sudo().browse(749)
            bank_payment_id = self.env["pr.account.bank.payment"].sudo().create({
                "account_id": account_id.id,
                "description": f"Payment For Work Permit of Visa Number {rec.visa_number}",
            })
            if bank_payment_id:
                rec.bank_payment_id = bank_payment_id.id
                bank_payment_id.work_permit_id = rec.id
            if rec.applicant_onboarding_id:
                rec.applicant_onboarding_id.work_permit_id = rec.id
                rec.applicant_onboarding_id.state = "work_permit"
            rec.state = "approved"
            rec.payment_state = "pending"

    def action_reject(self):
        for rec in self:
            rec.state = "reject"

    def open_bank_payment_view_form(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Work Permit Payment'),
            'res_model': 'pr.account.bank.payment',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': self.bank_payment_id.id,
        }

    def trigger_alerts(self):
        # Trigger alerts for Iqama expiry and work permit renewal window
        for rec in self:
            if rec.iqama_expiry_date:
                if fields.Date.today() >= rec.iqama_expiry_date:
                    # Send Iqama Expiry Alert
                    rec._send_notification()
            if rec.work_permit_renewal_date:
                if fields.Date.today() >= rec.work_permit_renewal_date:
                    # Send Work Permit Renewal Reminder
                    rec._send_notification()

    @api.model
    def _cron_check_alerts(self):
        # Scheduled job to run daily to check for alerts
        self.trigger_alerts()

    def _send_notification(self):
        for rec in self:
            hr_email = "hr@petroraq.com"
            mail = self.env["mail.mail"]
            try:
                body_message = f"""
                                Dear HR,<br/><br/>

We wish to inform you that a This Is Notification from the system about work permit/Iqama Expiry Of {rec.name}<br/><br/>

Thank you for your attention to this matter.<br/><br/>
Best regards,<br/>
<strong>HR Department</strong><br/>
Petroraq Engineering
"""
                receivers_emails = [hr_email]
                for receiver in receivers_emails:
                    message = {
                        "email_from": "hr@petroraq.com",
                        "subject": f"{rec.name} - Alert For Work Permit/Iqama Expiry",
                        "body_html": body_message,
                        "email_to": receiver,
                    }
                    mail_id = mail.sudo().create(message)
                    if mail_id:
                        mail_id.sudo().send()
            except Exception as e:
                _logger.error("Success email is not sent {}".format(e))

    def unlink(self):
        if self.state != 'draft':
            raise ValidationError("You Can Not Delete This Work Permit !!")
        return super().unlink()

