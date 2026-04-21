from odoo import models


class PeriodAbsenteesPdfReport(models.AbstractModel):
    _name = 'report.de_hr_workspace_leave_management.period_absentees_pdf'
    _description = 'Period Absentees PDF Report'

    def _get_report_values(self, docids, data=None):
        data = data or {}
        duration = data.get('duration', 'this_month')
        dashboard_data = self.env['hr.leave'].with_context(show_all_leave_dashboard=True).get_period_dashboard_data(duration)
        sections = {
            'include_absentees': data.get('include_absentees', True),
            'include_sick_leaves': data.get('include_sick_leaves', True),
            'include_annual_leaves': data.get('include_annual_leaves', True),
            'include_other_leaves': data.get('include_other_leaves', True),
            'include_leave_type_metrics': data.get('include_leave_type_metrics', True),
            'include_leave_availability': data.get('include_leave_availability', True),
        }
        return {
            'doc_ids': docids,
            'doc_model': 'hr.leave',
            'docs': self.env['hr.leave'],
            'duration': duration,
            'absentees': dashboard_data.get('absentees', []),
            'sick_leaves': dashboard_data.get('sick_leaves', []),
            'annual_leaves': dashboard_data.get('annual_leaves', []),
            'other_leaves': dashboard_data.get('other_leaves', []),
            'leave_type_metrics': dashboard_data.get('leave_type_metrics', []),
            'leave_availability': dashboard_data.get('leave_availability', []),
            'sections': sections,
        }


class PeriodAbsenteesXlsxReport(models.AbstractModel):
    _name = 'report.de_hr_workspace_leave_management.period_absentees_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Period Absentees XLSX Report'

    def generate_xlsx_report(self, workbook, data, records):
        data = data or {}
        duration = data.get('duration', 'this_month')
        include_absentees = data.get('include_absentees', True)
        include_sick = data.get('include_sick_leaves', True)
        include_annual = data.get('include_annual_leaves', True)
        include_other = data.get('include_other_leaves', True)
        include_metrics = data.get('include_leave_type_metrics', True)
        include_availability = data.get('include_leave_availability', True)
        dashboard_data = self.env['hr.leave'].with_context(show_all_leave_dashboard=True).get_period_dashboard_data(duration)
        absentees = dashboard_data.get('absentees', [])
        sick_leaves = dashboard_data.get('sick_leaves', [])
        annual_leaves = dashboard_data.get('annual_leaves', [])
        other_leaves = dashboard_data.get('other_leaves', [])
        leave_type_metrics = dashboard_data.get('leave_type_metrics', [])
        leave_availability = dashboard_data.get('leave_availability', [])

        sheet = workbook.add_worksheet('Leave Metrics')
        header = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2'})
        cell = workbook.add_format({'text_wrap': True})
        title = workbook.add_format({'bold': True})

        row = 0
        sheet.write(row, 0, f'Period: {duration}', title)
        row += 2

        if include_absentees:
            sheet.write(row, 0, 'Absentees', title)
            row += 1
            columns = ['Employee', 'Absent Days']
            for col, col_name in enumerate(columns):
                sheet.write(row, col, col_name, header)
            row += 1
            for absent in absentees:
                sheet.write(row, 0, absent.get('employee_name', ''), cell)
                sheet.write(row, 1, absent.get('absent_days', 0), cell)
                row += 1
            row += 1

        row += 1
        for show, section_title, leaves in [
            (include_sick, 'Sick Leaves', sick_leaves),
            (include_annual, 'Annual Leaves', annual_leaves),
            (include_other, 'Other Leaves', other_leaves),
        ]:
            if not show:
                continue
            sheet.write(row, 0, section_title, title)
            row += 1
            leave_columns = ['Employee', 'Leave Type', 'State', 'From', 'To', 'Days']
            for col, col_name in enumerate(leave_columns):
                sheet.write(row, col, col_name, header)
            row += 1
            for leave in leaves:
                sheet.write(row, 0, leave.get('employee_name', ''), cell)
                sheet.write(row, 1, leave.get('leave_type', ''), cell)
                sheet.write(row, 2, leave.get('state', ''), cell)
                sheet.write(row, 3, str(leave.get('date_from', '')), cell)
                sheet.write(row, 4, str(leave.get('date_to', '')), cell)
                sheet.write(row, 5, leave.get('number_of_days', 0), cell)
                row += 1
            row += 1

        if include_metrics:
            row += 1
            sheet.write(row, 0, 'Leave Type Metrics', title)
            row += 1
            metric_columns = ['Leave Type', 'Approved Days', 'Approved', 'Pending', 'Refused']
            for col, col_name in enumerate(metric_columns):
                sheet.write(row, col, col_name, header)
            row += 1
            for metric in leave_type_metrics:
                sheet.write(row, 0, metric.get('leave_type', ''), cell)
                sheet.write(row, 1, metric.get('approved_days', 0), cell)
                sheet.write(row, 2, metric.get('approved_count', 0), cell)
                sheet.write(row, 3, metric.get('pending_count', 0), cell)
                sheet.write(row, 4, metric.get('refused_count', 0), cell)
                row += 1

        if include_availability:
            row += 2
            sheet.write(row, 0, 'Leave Availability', title)
            row += 1
            availability_columns = ['Employee', 'Annual', 'Sick', 'Other', 'Total']
            for col, col_name in enumerate(availability_columns):
                sheet.write(row, col, col_name, header)
            row += 1
            for item in leave_availability:
                sheet.write(row, 0, item.get('employee_name', ''), cell)
                sheet.write(row, 1, item.get('annual_remaining', 0), cell)
                sheet.write(row, 2, item.get('sick_remaining', 0), cell)
                sheet.write(row, 3, item.get('other_remaining', 0), cell)
                sheet.write(row, 4, item.get('total_remaining', 0), cell)
                row += 1
