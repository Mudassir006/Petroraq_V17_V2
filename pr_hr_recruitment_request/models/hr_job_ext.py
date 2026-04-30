from odoo import fields, models


class Job(models.Model):
    _inherit = 'hr.job'

    job_shift_id = fields.Many2one('hr.job.shift', string='Job Shift')
    preferred_gender = fields.Selection([('male', 'Male'), ('female', 'Female')], string='Preferred Gender')
    education_level_id = fields.Many2one('hr.recruitment.degree')
    career_level_id = fields.Many2one('hr.career.level', string='Career Level')


class JobShift(models.Model):
    _name = 'hr.job.shift'
    _description = 'Job Shift'

    name = fields.Char(string='Name', required=True)



class CareerLevel(models.Model):
    _name = 'hr.career.level'
    _description = 'Career Level'

    name = fields.Char(string='Name', required=True)
