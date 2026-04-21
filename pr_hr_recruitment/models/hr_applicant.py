from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
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


    # endregion [Fields]

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

            old_sequence = rec.last_stage_id.sequence
            new_sequence = rec.stage_id.sequence
            if new_sequence != 0 and (old_sequence + 1) != new_sequence:
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
