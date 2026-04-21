from odoo import fields, models


class LeaveDashboardExportWizard(models.TransientModel):
    _name = 'de.hr.leave.dashboard.export.wizard'
    _description = 'Leave Dashboard Export Wizard'

    duration = fields.Selection([
        ('today', 'Today'),
        ('this_week', 'This week'),
        ('this_month', 'This month'),
        ('this_year', 'This year'),
    ], default='this_month', required=True)
    include_absentees = fields.Boolean(default=True)
    include_sick_leaves = fields.Boolean(default=True)
    include_annual_leaves = fields.Boolean(default=True)
    include_other_leaves = fields.Boolean(default=True)
    include_leave_type_metrics = fields.Boolean(default=True)
    include_leave_availability = fields.Boolean(default=True)

    def _export_data(self):
        self.ensure_one()
        return {
            'duration': self.duration,
            'include_absentees': self.include_absentees,
            'include_sick_leaves': self.include_sick_leaves,
            'include_annual_leaves': self.include_annual_leaves,
            'include_other_leaves': self.include_other_leaves,
            'include_leave_type_metrics': self.include_leave_type_metrics,
            'include_leave_availability': self.include_leave_availability,
        }

    def action_export_pdf(self):
        self.ensure_one()
        return self.env.ref('de_hr_workspace_leave_management.period_absentees_pdf_report_action').report_action(
            self, data=self._export_data()
        )

    def action_export_xlsx(self):
        self.ensure_one()
        return self.env.ref('de_hr_workspace_leave_management.period_absentees_xlsx_report_action').report_action(
            self, data=self._export_data()
        )
