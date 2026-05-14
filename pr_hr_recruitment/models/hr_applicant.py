import base64
from datetime import timedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
import random
import string

_logger = logging.getLogger(__name__)

AVAILABLE_PRIORITIES = [
    ('0', 'Normal'),
    ('1', 'Good'),
    ('2', 'Very Good'),
    ('3', 'Excellent')
]

INTERVIEW_SCORE_SELECTION = [
    ('0', 'Not Rated'),
    ('1', '1'),
    ('2', '2'),
    ('3', '3'),
    ('4', '4'),
    ('5', '5'),
]

INTERVIEW_RECOMMENDATION_SELECTION = [
    ('shortlist', 'Shortlist for Next Round'),
    ('reject', 'Reject'),
    ('hold', 'Keep on Hold'),
    ('hire', 'Hire'),
]

FIRST_INTERVIEW_STAGE_KEYWORDS = (
    '1st interview',
    'first interview',
)
SECOND_INTERVIEW_STAGE_KEYWORDS = (
    '2nd interview',
    'second interview',
)
CONTRACT_PROPOSAL_STAGE_KEYWORDS = (
    'contract proposal',
    'offer letter',
    'job offer',
)


class HrApplicant(models.Model):
    """
    """
    # region [Initial]
    _inherit = 'hr.applicant'
    # endregion [Initial]

    # region [Fields]

    applicant_onboarding_id = fields.Many2one("hr.applicant.onboarding", string="Application Onboarding")
    second_interviewer_ids = fields.Many2many('res.users', 'hr_applicant_res_users_2interviewers_rel',
                                              string='Interviewers', index=True, tracking=True,
                                              domain="[('share', '=', False), ('company_ids', 'in', company_id)]")
    second_priority = fields.Selection(AVAILABLE_PRIORITIES, "Evaluation", default='0')
    second_availability = fields.Date("Availability",
                               help="The date at which the applicant will be available to start working", tracking=True)
    second_salary_proposed = fields.Float("Proposed Salary", group_operator="avg", help="Salary Proposed by the Organisation",
                                   tracking=True, groups="hr_recruitment.group_hr_recruitment_user")
    check_first_interview_stage_sequence = fields.Boolean(compute="_compute_check_first_interview_stage_sequence")
    check_second_interview_stage_sequence = fields.Boolean(compute="_compute_check_second_interview_stage_sequence")
    next_stage_id = fields.Many2one(
        "hr.recruitment.stage", string="Next Stage", compute="_compute_next_stage_id")
    show_first_interview_evaluation = fields.Boolean(compute="_compute_interview_evaluation_visibility")
    show_second_interview_evaluation = fields.Boolean(compute="_compute_interview_evaluation_visibility")
    readonly_first_interview_evaluation = fields.Boolean(compute="_compute_interview_evaluation_visibility")
    readonly_second_interview_evaluation = fields.Boolean(compute="_compute_interview_evaluation_visibility")
    check_contract_proposal_stage = fields.Boolean(compute="_compute_check_contract_proposal_stage")
    offer_letter_attachment_id = fields.Many2one(
        "ir.attachment", string="Offer Letter PDF", readonly=True, copy=False)
    offer_letter_sent_date = fields.Datetime(string="Offer Letter Sent On", readonly=True, copy=False)

    first_communication_score = fields.Selection(
        INTERVIEW_SCORE_SELECTION, string="Communication Skills", default='0', tracking=True)
    first_technical_score = fields.Selection(
        INTERVIEW_SCORE_SELECTION, string="Technical Knowledge", default='0', tracking=True)
    first_experience_score = fields.Selection(
        INTERVIEW_SCORE_SELECTION, string="Relevant Experience", default='0', tracking=True)
    first_behavior_score = fields.Selection(
        INTERVIEW_SCORE_SELECTION, string="Attitude / Behavior", default='0', tracking=True)
    first_overall_score = fields.Selection(
        INTERVIEW_SCORE_SELECTION, string="Overall Rating", default='0', tracking=True)
    first_total_score = fields.Integer(
        string="Total Score", compute="_compute_interview_scores", store=True)
    first_average_score = fields.Float(
        string="Average Score", compute="_compute_interview_scores", store=True, digits=(16, 2))
    first_interview_summary = fields.Text(string="Interview Summary", tracking=True)
    first_strengths = fields.Text(string="Strengths", tracking=True)
    first_recommendation = fields.Selection(
        INTERVIEW_RECOMMENDATION_SELECTION, string="Recommendation", tracking=True)

    second_communication_score = fields.Selection(
        INTERVIEW_SCORE_SELECTION, string="Communication Skills", default='0', tracking=True)
    second_technical_score = fields.Selection(
        INTERVIEW_SCORE_SELECTION, string="Technical Knowledge", default='0', tracking=True)
    second_experience_score = fields.Selection(
        INTERVIEW_SCORE_SELECTION, string="Relevant Experience", default='0', tracking=True)
    second_behavior_score = fields.Selection(
        INTERVIEW_SCORE_SELECTION, string="Attitude / Behavior", default='0', tracking=True)
    second_overall_score = fields.Selection(
        INTERVIEW_SCORE_SELECTION, string="Overall Rating", default='0', tracking=True)
    second_total_score = fields.Integer(
        string="Total Score", compute="_compute_interview_scores", store=True)
    second_average_score = fields.Float(
        string="Average Score", compute="_compute_interview_scores", store=True, digits=(16, 2))
    second_interview_summary = fields.Text(string="Interview Summary", tracking=True)
    second_strengths = fields.Text(string="Strengths", tracking=True)
    second_recommendation = fields.Selection(
        INTERVIEW_RECOMMENDATION_SELECTION, string="Recommendation", tracking=True)

    # endregion [Fields]

    @staticmethod
    def _stage_matches_keywords(stage, keywords):
        if not stage:
            return False
        stage_name = (stage.name or '').casefold()
        return any(keyword in stage_name for keyword in keywords)

    def _get_interview_stage(self, keywords):
        self.ensure_one()
        domain = []
        if self.job_id:
            domain = ["|", ("job_ids", "=", False), ("job_ids", "in", self.job_id.ids)]
        stages = self.env["hr.recruitment.stage"].search(domain, order="sequence, id")
        return stages.filtered(lambda stage: self._stage_matches_keywords(stage, keywords))[:1]

    def _get_next_recruitment_stage(self, from_stage=False):
        self.ensure_one()
        stage = from_stage or self.stage_id
        if not stage:
            return self.env["hr.recruitment.stage"]

        domain = [("sequence", ">", stage.sequence)]
        if self.job_id:
            domain += ["|", ("job_ids", "=", False), ("job_ids", "in", self.job_id.ids)]
        return self.env["hr.recruitment.stage"].search(domain, order="sequence, id", limit=1)

    @api.depends("stage_id", "job_id")
    def _compute_next_stage_id(self):
        for rec in self:
            rec.next_stage_id = rec._get_next_recruitment_stage()

    @api.depends("stage_id", "job_id")
    def _compute_interview_evaluation_visibility(self):
        for rec in self:
            stage = rec.stage_id
            first_stage = rec._get_interview_stage(FIRST_INTERVIEW_STAGE_KEYWORDS)
            second_stage = rec._get_interview_stage(SECOND_INTERVIEW_STAGE_KEYWORDS)
            is_first_stage = rec._stage_matches_keywords(stage, FIRST_INTERVIEW_STAGE_KEYWORDS)
            is_second_stage = rec._stage_matches_keywords(stage, SECOND_INTERVIEW_STAGE_KEYWORDS)

            after_first_stage = bool(first_stage and stage and stage.sequence > first_stage.sequence)
            after_second_stage = bool(second_stage and stage and stage.sequence > second_stage.sequence)

            rec.show_first_interview_evaluation = is_first_stage or after_first_stage
            rec.show_second_interview_evaluation = is_second_stage or after_second_stage
            rec.readonly_first_interview_evaluation = not is_first_stage
            rec.readonly_second_interview_evaluation = not is_second_stage

    def action_move_to_next_stage(self):
        for rec in self:
            next_stage = rec.next_stage_id
            if not next_stage:
                raise UserError(_("There is no next recruitment stage configured for %s.") % rec.display_name)
            rec.stage_id = next_stage.id
        return True

    def _get_offer_letter_email(self):
        self.ensure_one()
        return self.email_from or self.partner_id.email

    @api.depends("stage_id")
    def _compute_check_contract_proposal_stage(self):
        for rec in self:
            rec.check_contract_proposal_stage = rec._stage_matches_keywords(
                rec.stage_id, CONTRACT_PROPOSAL_STAGE_KEYWORDS)

    def _format_offer_letter_date(self, date_value):
        date_value = fields.Date.to_date(date_value)
        day = date_value.day
        if 10 <= day % 100 <= 20:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
        return date_value.strftime(f"{day}{suffix} %B %Y")

    @staticmethod
    def _format_offer_letter_amount(amount, currency_name='SAR'):
        return f"{amount:,.2f} {currency_name or 'SAR'}"

    def _get_offer_letter_values(self):
        self.ensure_one()
        offer_date = fields.Date.context_today(self)
        validity_date = offer_date + timedelta(days=1)
        gross_salary = self.second_salary_proposed or self.salary_proposed or 0.0
        basic_salary = gross_salary / 1.35 if gross_salary else 0.0
        country = self.env['res.country']
        if 'country_id' in self._fields and self.country_id:
            country = self.country_id
        elif self.partner_id.country_id:
            country = self.partner_id.country_id
        nationality = country.name or ''
        if country and 'nationality' in country._fields and country.nationality:
            nationality = country.nationality
        currency_name = (self.company_id.currency_id or self.env.company.currency_id).name or 'SAR'
        return {
            'date': self._format_offer_letter_date(offer_date),
            'validity_date': self._format_offer_letter_date(validity_date),
            'candidate_name': self.partner_name or self.name or '',
            'nationality': nationality,
            'position': self.job_id.name or '',
            'basic_salary': self._format_offer_letter_amount(basic_salary, currency_name),
            'gross_salary': self._format_offer_letter_amount(gross_salary, currency_name),
            'housing_allowance': '25% of Basic Salary',
            'transportation_allowance': '10% of Basic Salary',
            'contract_status': 'Single',
            'medical': 'Provided by company as per company policy',
            'contract_duration': '02 (Two) Years (Renewable)',
            'probation_period': '90 Days',
            'vacation': '21 working days paid vacation per annum',
            'working_hours': '48 hours per week',
            'company_name': self.company_id.name or self.env.company.name or 'Petroraq Engineering Co. Ltd.',
            'signatory_name': 'Mustafa Abdulrasheed',
            'signatory_title': 'Managing Director',
        }

    def _get_offer_letter_pdf_filename(self):
        self.ensure_one()
        candidate_name = self.partner_name or self.name or _('Applicant')
        return f"Offer Letter - {candidate_name}.pdf"

    def _generate_offer_letter_attachment(self):
        self.ensure_one()
        report = self.env.ref('pr_hr_recruitment.action_report_applicant_offer_letter', raise_if_not_found=False)
        if not report:
            raise UserError(_(
                "The offer letter report is not installed. Please upgrade the Petroraq HR Recruitment module."))
        pdf_content, _content_type = self.env['ir.actions.report']._render_qweb_pdf(report.report_name, self.ids)
        attachment = self.env['ir.attachment'].sudo().create({
            'name': self._get_offer_letter_pdf_filename(),
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })
        self.offer_letter_attachment_id = attachment.id
        return attachment

    def _get_offer_letter_email_template(self):
        template = self.env.ref(
            'pr_hr_recruitment.email_template_applicant_offer_letter', raise_if_not_found=False)
        if template:
            return template

        model_id = self.env['ir.model']._get_id('hr.applicant')
        return self.env['mail.template'].search([
            ('name', '=', 'Applicant Offer Letter'),
            ('model_id', '=', model_id),
        ], limit=1)

    def _send_offer_letter_fallback_email(self, attachment):
        self.ensure_one()
        body_message = f"""
            <p>Dear {self.partner_name or self.name},</p>
            <p>
                Congratulations. Please find attached your offer letter for
                <strong>{self.job_id.name or 'the offered position'}</strong>.
            </p>
            <p>
                Kindly review the attached PDF, sign the acceptance section, and return the signed copy to HR.
            </p>
            <p>
                Best regards,<br/>
                <strong>Human Resources Department</strong><br/>
                {self.company_id.name or self.env.company.name}
            </p>
        """
        email_from = (
            self.user_id.email_formatted
            or self.company_id.email
            or self.env.user.email_formatted
        )
        mail = self.env['mail.mail'].sudo().create({
            'email_from': email_from,
            'email_to': self._get_offer_letter_email(),
            'subject': f"Offer Letter - {self.job_id.name or self.company_id.name or 'Petroraq'}",
            'body_html': body_message,
            'attachment_ids': [(4, attachment.id)],
        })
        mail.send()

    def action_send_offer_letter(self):
        template = self._get_offer_letter_email_template()
        for rec in self:
            email_to = rec._get_offer_letter_email()
            if not email_to:
                raise UserError(_(
                    "Please set an email address for %s before sending the offer letter.") % rec.display_name)
            attachment = rec._generate_offer_letter_attachment()
            if template:
                template.send_mail(
                    rec.id,
                    force_send=True,
                    email_values={'attachment_ids': [(4, attachment.id)]},
                )
            else:
                rec._send_offer_letter_fallback_email(attachment)
            rec.offer_letter_sent_date = fields.Datetime.now()
        return True

    def _send_offer_letter_on_contract_proposal(self):
        for rec in self:
            if (
                rec.stage_id
                and not rec.offer_letter_sent_date
                and rec._stage_matches_keywords(rec.stage_id, CONTRACT_PROPOSAL_STAGE_KEYWORDS)
            ):
                rec.action_send_offer_letter()

    def write(self, vals):
        res = super().write(vals)
        if 'stage_id' in vals:
            self._send_offer_letter_on_contract_proposal()
        return res

    @api.depends(
        "first_communication_score", "first_technical_score", "first_experience_score",
        "first_behavior_score", "first_overall_score", "second_communication_score",
        "second_technical_score", "second_experience_score", "second_behavior_score",
        "second_overall_score")
    def _compute_interview_scores(self):
        first_fields = [
            "first_communication_score", "first_technical_score", "first_experience_score",
            "first_behavior_score", "first_overall_score",
        ]
        second_fields = [
            "second_communication_score", "second_technical_score", "second_experience_score",
            "second_behavior_score", "second_overall_score",
        ]
        for rec in self:
            first_total = sum(int(getattr(rec, field_name) or 0) for field_name in first_fields)
            second_total = sum(int(getattr(rec, field_name) or 0) for field_name in second_fields)
            rec.first_total_score = first_total
            rec.first_average_score = first_total / len(first_fields)
            rec.second_total_score = second_total
            rec.second_average_score = second_total / len(second_fields)

    @api.depends("stage_id")
    def _compute_check_first_interview_stage_sequence(self):
        for rec in self:
            rec.check_first_interview_stage_sequence = rec._stage_matches_keywords(
                rec.stage_id, FIRST_INTERVIEW_STAGE_KEYWORDS)

    @api.depends("stage_id")
    def _compute_check_second_interview_stage_sequence(self):
        for rec in self:
            rec.check_second_interview_stage_sequence = rec._stage_matches_keywords(
                rec.stage_id, SECOND_INTERVIEW_STAGE_KEYWORDS)

    @api.constrains("stage_id")
    def _check_stage_to_generate_onboarding(self):
        for rec in self:

            # Check Next Stage

            old_stage = rec.last_stage_id
            new_stage = rec.stage_id
            if old_stage and new_stage and new_stage.sequence != 0:
                next_stage = rec._get_next_recruitment_stage(from_stage=old_stage)
                if new_stage != next_stage:
                    raise ValidationError("You can not go to this step directly, please forward the rules")

            if rec.stage_id and rec.stage_id.hired_stage and not rec.applicant_onboarding_id:
                employee_id = self.env["hr.employee"].sudo().create({
                    "name": rec.partner_name,
                    # "code": "Enter Code Here",
                    "code": self.generate_random_4_char_string(),
                    "company_id": self.env.company.id,
                })
                applicant_onboarding_id = self.env["hr.applicant.onboarding"].create({
                    "name": rec.partner_name,
                    "applicant_id": rec.id,
                    "employee_id": employee_id.id if employee_id else False,
                    "hire_type": "local",
                    "state": "initialize",
                })
                if applicant_onboarding_id:
                    rec.applicant_onboarding_id = applicant_onboarding_id.id

    def generate_random_4_char_string(self):
        """Generates a random four-character string composed of letters and digits."""
        characters = string.ascii_letters + string.digits  # All uppercase/lowercase letters and digits
        random_string = ''.join(random.choice(characters) for _ in range(4))
        return random_string

    def open_applicant_onboarding_id_view_form(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Applicant Onboarding'),
            'res_model': 'hr.applicant.onboarding',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': self.applicant_onboarding_id.id,
        }
