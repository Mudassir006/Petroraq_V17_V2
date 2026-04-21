# -*- coding: utf-8 -*-
{
    'name': "Employee Attendance - Self Service",
    'summary': """
        Self-Service Attendance Management
    """,
    'description': """
        The Self-Service Attendance Management sub-module within the employee workspace in Odoo empowers users to conveniently mark their own attendance and review their attendance records. Employees can effortlessly log manual attendance entries, making it easy to account for irregular hours or remote work. Furthermore, they can access a detailed attendance history, providing transparency and control over their attendance data. This feature enhances user autonomy and streamlines attendance tracking within the organization.
    """,
    'author': 'Dynexcel',
    'website': 'https://www.dynexcel.com',
    'version': '0.1',
    'category': 'Human Resources',

    'depends': ['de_hr_workspace','pr_hr_attendance'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        'data/ir_cron.xml',
        'views/hr_attendance_views.xml',
        'views/hr_shortage_request.xml',
        'views/hr_approval_dashboard.xml',
        'views/thanks_template.xml',
        'views/shortage_request_template.xml',
        'views/hr_attendance_portal.xml',
        'views/hr_shortage_request_portal.xml',
        'views/hr_shortage_request_approval_portal.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],

    'assets': {
        'web.assets_backend': [
            'de_hr_workspace_attendance/static/src/js/shortage_request_button.js',
            'de_hr_workspace_attendance/static/src/js/approval_dashboard.js',
            'de_hr_workspace_attendance/static/src/xml/request_button.xml',
            'de_hr_workspace_attendance/static/src/xml/approval_dashboard.xml',
            'de_hr_workspace_attendance/static/src/scss/approval_dashboard.scss',
        ],
    },

    'license': 'OPL-1',
    'license': 'LGPL-3',
    'images': ['static/description/banner.jpg'],
    'installable': True,
    'application': False,
    'auto_install': False,
}