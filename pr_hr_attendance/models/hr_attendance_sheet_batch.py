from odoo import models, fields, api, _
from odoo.tools import date_utils
from odoo.osv import expression
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
import re
import json
import math
from random import randint
import logging
from datetime import datetime, timedelta
import pandas as pd


_logger = logging.getLogger(__name__)


class HrAttendanceSheetBatch(models.Model):
    """
    """
    # region [Initial]
    _inherit = 'attendance.sheet.batch'
    # endregion [Initial]

    # region [Fields]

    att_sheet_ids_count = fields.Integer(compute="_compute_att_sheet_ids_count")

    # endregion [Fields]

    @api.depends("att_sheet_ids")
    def _compute_att_sheet_ids_count(self):
        for att_sheet_batch in self:
            att_sheet_batch.att_sheet_ids_count = len(att_sheet_batch.att_sheet_ids)

    def open_related_attendance_sheets(self):
        self.ensure_one()
        form_id = self.env.ref('gs_hr_attendance_sheet.attendance_sheet_form_view').id
        list_id = self.env.ref('gs_hr_attendance_sheet.attendance_sheet_tree_view').id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Attendance Sheets'),
            'res_model': 'attendance.sheet',
            'view_type': 'list',
            'view_mode': 'list',
            'views': [[list_id, 'list'], [form_id, 'form']],
            'domain': [('id', 'in', self.att_sheet_ids.ids)],
            'target': 'current'
        }

    def open_related_payslips(self):
        self.ensure_one()
        form_id = self.env.ref('hr_payroll.view_hr_payslip_form').id
        list_id = self.env.ref('hr_payroll.view_hr_payslip_tree').id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Payslips'),
            'res_model': 'hr.payslip',
            'view_type': 'list',
            'view_mode': 'list',
            'views': [[list_id, 'list'], [form_id, 'form']],
            'domain': [('attendance_sheet_id', 'in', self.att_sheet_ids.ids)],
            'target': 'current'
        }

    def open_related_payslip_batch(self):
        self.ensure_one()
        form_id = self.env.ref('hr_payroll.hr_payslip_run_form').id
        list_id = self.env.ref('hr_payroll.hr_payslip_run_tree').id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Payslip Batch'),
            'res_model': 'hr.payslip.run',
            'view_type': 'list',
            'view_mode': 'list',
            'views': [[list_id, 'list'], [form_id, 'form']],
            'domain': [('id', '=', self.payslip_batch_id.id)],
            'target': 'current'
        }