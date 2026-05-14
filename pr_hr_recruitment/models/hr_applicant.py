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

    def action_move_to_next_stage(self):
        for rec in self:
            next_stage = rec.next_stage_id
            if not next_stage:
                raise UserError(_("There is no next recruitment stage configured for %s.") % rec.display_name)
            rec.stage_id = next_stage.id
        return True

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
            if rec.stage_id and rec.stage_id.sequence == 1:
                rec.check_first_interview_stage_sequence = True
            else:
                rec.check_first_interview_stage_sequence = False

    @api.depends("stage_id")
    def _compute_check_second_interview_stage_sequence(self):
        for rec in self:
            if rec.stage_id and rec.stage_id.sequence == 2:
                rec.check_second_interview_stage_sequence = True
            else:
                rec.check_second_interview_stage_sequence = False

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
