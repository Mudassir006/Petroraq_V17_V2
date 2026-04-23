{
    'name': 'Custom Attendance Report',
    'version': '17.0.1.0.0',
    'summary': 'Advanced Attendance Reporting with Detailed Insights',
    'description': """
Custom Attendance Report
========================

This module allows HR managers and administrators to generate detailed attendance reports for employees, including:

- Daily attendance breakdown by hours
- Highlights for check-in/check-out times
- Overtime, lateness, and absence tracking
- Holidays, leaves, and working day analysis
- PDF export with stylish formatting and colors
- Filters by employee, department, and date range
- Monthly or custom date range reporting
- Support for leave days and remaining leaves

Perfect for organizations needing a reliable and professional way to analyze employee attendance records and produce well-formatted reports.
""",

    'category': 'Human Resources',
    'author': 'Mudassir Amin',
    'website': 'mudassir.odoo@gmail.com',
    'license': 'LGPL-3',
    'depends': [
        'hr_attendance',
        'hr_holidays',
        'hr',
        'mail',
        'calendar',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/paper_format.xml',
        'report/attendance_report_action.xml',
        'views/attendance_menu.xml',
        'views/attendance_report_wizard_view.xml',
        'report/attendance_report_template.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}