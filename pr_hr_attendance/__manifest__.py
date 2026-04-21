# -*- coding: utf-8 -*-
{
    'name': "Petroraq HR Attendance",

    'summary': """
        This Module is created to manage attendance""",

    'description': """
    """,

    'author': "Mahmoud Salah",
    'company': "Petroraq",
    'website': "https://webmail.petroraq.com/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Human Resources/Attendance',
    'version': '17.0.1.0.3',
    # any module necessary for this one to work correctly
    'depends': ['pr_hr_contract', 'gs_hr_attendance_sheet'],

    # always loaded
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/hr_attendance_views.xml',
        'views/hr_employee.xml',
        'views/hr_attendance_sheet_batch.xml',
        'views/hr_attendance_sheet.xml',
        'views/hr_payslip.xml',
        'views/attendance_notification_view.xml',
        'views/hr_shortage_request_view.xml',
        'wizards/hr_attendance_import_wizard.xml',
        'data/data.xml',
        'data/ir_sequence.xml',
        'data/attendance_notification_cron.xml',
    ],
    # only loaded in demonstration mode
    'demo': [],
}
