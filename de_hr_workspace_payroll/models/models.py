# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    line_ids_filtered = fields.One2many("hr.payslip.line", "slip_id", compute="_compute_line_ids_filtered")

    @api.depends("line_ids", "line_ids.total")
    def _compute_line_ids_filtered(self):
        for rec in self:
            if rec.line_ids:
                line_ids_filtered = rec.line_ids.filtered(lambda l: l.total != 0)
                if line_ids_filtered:
                    rec.line_ids_filtered = line_ids_filtered.ids
                else:
                    rec.line_ids_filtered = False
            else:
                rec.line_ids_filtered = False
