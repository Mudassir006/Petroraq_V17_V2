# -*- coding: utf-8 -*-
{
    'name': "Time Off Workspace - Self Service",
    'summary': """
        Self-Service Time Off and Holiday Requests
    """,
    'description': """
        The Self-Service Time Off and Holiday Requests sub-module within the employee workspace in Odoo allows users to autonomously request time off or holidays. Employees can conveniently submit requests for annual leave, sick leave, or any other types of time off. Additionally, they can review the status of their requests and access a comprehensive history of their time-off approvals. This feature puts control in the hands of employees, simplifying the process of managing time off and ensuring transparency in leave management within the organization.
    """,
    'author': 'Dynexcel',
    'website': 'https://www.dynexcel.com',
    'version': '0.1.1',
    'category': 'Human Resources',

    # any module necessary for this one to work correctly
    'depends': ['de_hr_workspace','pr_hr_holidays'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        'views/hr_holidays_views.xml',
        'views/hr_leave_request.xml',
        'views/public_holiday_approvals.xml',
        'views/leave_request_template.xml',
        'views/thanks_template.xml',
        'views/hr_leave_employee_portal.xml',
        'views/hr_leave_request_employee_portal.xml',
        'views/hr_leave_dashboard_employee_portal.xml',
        'views/hr_leave_request_approval_portal.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'assets': {
            'web.assets_backend': [
                'de_hr_workspace_timeoff/static/src/js/leave_request_button.js',
                'de_hr_workspace_timeoff/static/src/xml/leave_request_button.xml',
                'de_hr_workspace_timeoff/static/src/js/leave_dashboard.js',
                'de_hr_workspace_timeoff/static/src/xml/leave_dashboard.xml',
                'https://cdn.jsdelivr.net/npm/chart.js',
            ],
        },
    'license': 'LGPL-3',
    'images': ['static/description/banner.jpg'],
    'installable': True,
    'application': False,
    'auto_install': False,
}