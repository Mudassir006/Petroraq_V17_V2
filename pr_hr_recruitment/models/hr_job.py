from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class HrJob(models.Model):
    """
    """
    # region [Initial]
    _inherit = 'hr.job'
    # endregion [Initial]

    # region [Fields]

    job_salary = fields.Float(string="Salary")
    experience_years = fields.Float(string="Years Of Experience")
    job_state = fields.Selection([
        ("initialize", "Initialized"),
        ("review", "Reviewed"),
        ("post", "Posted"),
        ("reject", "Rejected"),
    ], string="Status", default="initialize")
    approval_state = fields.Selection([
        ("initialize", "Initialized"),
        ("review", "Reviewed / Pending Approval"),
        ("post", "Posted"),
        ("reject", "Rejected"),
    ], string="Status", default="initialize")

    # endregion [Fields]

    def action_review(self):
        for rec in self:
            rec.job_state = "review"
            rec.approval_state = "review"

    def action_post(self):
        for rec in self:
            rec.website_published = True
            rec.job_state = "post"
            rec.approval_state = "post"

    def action_reject(self):
        for rec in self:
            rec.job_state = "reject"
            rec.approval_state = "reject"
