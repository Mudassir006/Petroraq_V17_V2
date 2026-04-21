from odoo import fields, models


class Project(models.Model):
    _inherit = "project.project"

    work_order_id = fields.One2many("pr.work.order", "project_id", string="Work Orders")
    analytic_account_id = fields.Many2one("account.analytic.account", string="Cost Center")


class ProjectTask(models.Model):
    _inherit = "project.task"

    work_order_id = fields.Many2one("pr.work.order", string="Work Order")
