from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import json


class AccountAnalyticAccount(models.Model):
    # region [Initial]
    _inherit = 'account.analytic.account'
    # endregion [Initial]


    project_code = fields.Char(string="Code")
    project_partner_id = fields.Many2one("res.partner", string="Manager", tracking=True)
    analytic_plan_type = fields.Selection([
        ("department", "Department"),
        ("section", "Section"),
        ("project", "Project"),
        ("employee", "Employee"),
        ("asset", "Asset"),
    ], related="plan_id.analytic_plan_type", string="Plan Type", store=True, tracking=True)
    department_id = fields.Many2one("account.analytic.account", string="Department", domain="[('analytic_plan_type', '=', 'department')]")
    section_id = fields.Many2one("account.analytic.account", string="Section", domain="[('analytic_plan_type', '=', 'section')]")
    section_id_domain = fields.Char(string='Section Domain', compute="_compute_section_id_domain")
    project_id = fields.Many2one("account.analytic.account", string="Project", domain="[('analytic_plan_type', '=', 'project')]")

    @api.constrains("project_code")
    def _check_project_code(self):
        for rec in self:
            if rec.project_code:
                project_cost_center_id = self.env["account.analytic.account"].sudo().search([
                    ("project_code", "=", rec.project_code),
                    ("analytic_plan_type", "=", "project"),
                    ("id", "!=", rec.id),
                ], limit=1)
                if project_cost_center_id:
                    raise ValidationError(f"This Project Code {rec.project_code} Exists Before With Project {project_cost_center_id.name}, Please Check !!")

    @api.depends("analytic_plan_type", "department_id")
    def _compute_section_id_domain(self):
        for rec in self:
            if rec.analytic_plan_type == "project" and rec.department_id:
                section_ids = self.env["account.analytic.account"].sudo().search([("analytic_plan_type", "=", "section"), ("department_id", "=", rec.department_id.id)])
                if section_ids:
                    rec.section_id_domain = json.dumps([('id', 'in', section_ids.ids)])
                else:
                    rec.section_id_domain = "[('analytic_plan_type', '=', 'section')]"
            else:
                rec.section_id_domain = "[('analytic_plan_type', '=', 'section')]"

    @api.model
    def create(self, vals):
        '''
        We Inherit Create Method To Pass Sequence Fo Field Name
        '''
        res = super().create(vals)
        if res.analytic_plan_type == 'project':
            res.project_code = self.env['ir.sequence'].next_by_code('pr.account.project.cost.center.seq.code') or ''
        return res

    @api.depends('name', 'project_code', 'analytic_plan_type')
    def _compute_display_name(self):
        for rec in self:
            if rec.name:
                if rec.analytic_plan_type == 'project':
                    name = f"{rec.project_code} - {rec.name}"
                else:
                    name = rec.name
                rec.display_name = name.strip()
            else:
                rec.display_name = False