from datetime import timedelta

from odoo import api, fields, models
from odoo.tools import date_utils


class LeaveAnalyticsWizard(models.TransientModel):
    _name = 'de.hr.leave.analytics.wizard'
    _description = 'Leave Analytics Wizard'

    duration = fields.Selection([
        ('week', 'This Week'),
        ('month', 'This Month'),
        ('year', 'This Year'),
        ('custom', 'Custom Range'),
    ], default='month', required=True)
    date_from = fields.Date(required=True, default=fields.Date.today)
    date_to = fields.Date(required=True, default=fields.Date.today)
    line_ids = fields.One2many('de.hr.leave.analytics.wizard.line', 'wizard_id', readonly=True)

    @api.onchange('duration')
    def _onchange_duration(self):
        for rec in self:
            rec.date_from, rec.date_to = rec._get_date_range()

    def _get_date_range(self):
        self.ensure_one()
        today = fields.Date.today()
        if self.duration == 'week':
            return date_utils.start_of(today, 'week'), date_utils.end_of(today, 'week') - timedelta(days=1)
        if self.duration == 'year':
            return date_utils.start_of(today, 'year'), date_utils.end_of(today, 'year') - timedelta(days=1)
        if self.duration == 'custom':
            return self.date_from, self.date_to
        return date_utils.start_of(today, 'month'), date_utils.end_of(today, 'month') - timedelta(days=1)

    def _build_summary_data(self):
        self.ensure_one()
        date_from, date_to = self._get_date_range()

        employees = self.env['hr.employee'].sudo().search([('active', '=', True)])
        summary = {
            emp.id: {
                'employee_id': emp.id,
                'employee_code': emp.code or '',
                'employee_name': emp.name,
                'department_name': emp.department_id.name or '',
                'manager_name': emp.parent_id.name or '',
                'annual_days': 0.0,
                'sick_days': 0.0,
                'other_days': 0.0,
                'total_leave_days': 0.0,
                'absence_days': 0.0,
            }
            for emp in employees
        }

        leave_domain = [
            ('state', '=', 'validate'),
            ('employee_id', 'in', employees.ids),
            ('request_date_from', '>=', date_from),
            ('request_date_to', '<=', date_to),
        ]
        leaves = self.env['hr.leave'].sudo().search(leave_domain)
        for leave in leaves:
            row = summary.get(leave.employee_id.id)
            if not row:
                continue
            days = leave.number_of_days or 0.0
            leave_kind = leave.holiday_status_id.leave_type
            if leave_kind == 'annual_leave':
                row['annual_days'] += days
            elif leave_kind == 'sick_leave':
                row['sick_days'] += days
            else:
                row['other_days'] += days
            row['total_leave_days'] += days

        sheet_domain = [
            ('employee_id', 'in', employees.ids),
            ('state', '=', 'done'),
            ('date_from', '>=', date_from),
            ('date_to', '<=', date_to),
        ]
        sheets = self.env['hr.attendance.sheet'].sudo().search(sheet_domain)
        for sheet in sheets:
            row = summary.get(sheet.employee_id.id)
            if row:
                row['absence_days'] += (sheet.no_absence or 0.0)

        return [
            vals for vals in summary.values()
            if any(vals[k] for k in ['annual_days', 'sick_days', 'other_days', 'total_leave_days', 'absence_days'])
        ]

    def action_generate(self):
        self.ensure_one()
        self.line_ids.unlink()
        lines = [(0, 0, row) for row in self._build_summary_data()]
        self.write({'line_ids': lines})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'de.hr.leave.analytics.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }

    def action_export_pdf(self):
        self.ensure_one()
        if not self.line_ids:
            self.action_generate()
        return self.env.ref('de_hr_workspace_leave_management.leave_analytics_pdf_report').report_action(self)

    def action_export_xlsx(self):
        self.ensure_one()
        if not self.line_ids:
            self.action_generate()
        return self.env.ref('de_hr_workspace_leave_management.leave_analytics_xlsx_report').report_action(self)


class LeaveAnalyticsWizardLine(models.TransientModel):
    _name = 'de.hr.leave.analytics.wizard.line'
    _description = 'Leave Analytics Wizard Line'

    wizard_id = fields.Many2one('de.hr.leave.analytics.wizard', ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', readonly=True)
    employee_code = fields.Char(readonly=True)
    employee_name = fields.Char(readonly=True)
    department_name = fields.Char(readonly=True)
    manager_name = fields.Char(readonly=True)
    annual_days = fields.Float(readonly=True)
    sick_days = fields.Float(readonly=True)
    other_days = fields.Float(readonly=True)
    total_leave_days = fields.Float(readonly=True)
    absence_days = fields.Float(readonly=True)


class LeaveAnalyticsPdfReport(models.AbstractModel):
    _name = 'report.de_hr_workspace_leave_management.leave_analytics_pdf'
    _description = 'Leave Analytics PDF Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['de.hr.leave.analytics.wizard'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'de.hr.leave.analytics.wizard',
            'docs': docs,
        }


class LeaveAnalyticsXlsxReport(models.AbstractModel):
    _name = 'report.de_hr_workspace_leave_management.leave_analytics_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Leave Analytics XLSX Report'

    def generate_xlsx_report(self, workbook, data, wizard):
        sheet = workbook.add_worksheet('Leave Analytics')
        header = workbook.add_format({'bold': True, 'bg_color': '#DCE6F1', 'border': 1})
        cell = workbook.add_format({'border': 1})

        titles = ['Code', 'Employee', 'Department', 'Manager', 'Annual', 'Sick', 'Other', 'Total Leave', 'Absence']
        for col, title in enumerate(titles):
            sheet.write(0, col, title, header)

        row_no = 1
        for line in wizard.line_ids:
            sheet.write(row_no, 0, line.employee_code or '', cell)
            sheet.write(row_no, 1, line.employee_name or '', cell)
            sheet.write(row_no, 2, line.department_name or '', cell)
            sheet.write(row_no, 3, line.manager_name or '', cell)
            sheet.write(row_no, 4, line.annual_days, cell)
            sheet.write(row_no, 5, line.sick_days, cell)
            sheet.write(row_no, 6, line.other_days, cell)
            sheet.write(row_no, 7, line.total_leave_days, cell)
            sheet.write(row_no, 8, line.absence_days, cell)
            row_no += 1
