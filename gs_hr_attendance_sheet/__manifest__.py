# -*- coding: utf-8 -*-
{
    'name': "HR Attendance Sheet And Policies",

    'summary': """Managing  Attendance Sheets for Employees""",
    'description': """Employees Attendance Sheet Management """,
    'author': 'info@odooclinic.com',
    "website": "Www.odooclinic.com",
    'category': 'hr',
    'version': '17.0.1.2',
    'images': ['static/description/bannar.jpg'],
    'depends': ['base',
                'hr',
                # 'hr_payroll',
                'pr_hr_contract',
                'hr_holidays',
                'hr_work_entry_contract',
                'hr_attendance'
                ],
    'data': [
        'data/ir_sequence.xml',
        'data/data2.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/remove_transient_acl.xml',
        'wizard/change_att_data_view.xml',
        'views/hr_employee.xml',
        'views/hr_attendance_sheet_view.xml',
        'views/hr_attendance_policy_view.xml',
        'views/hr_contract_view.xml',
        'views/hr_public_holiday_view.xml',
        'views/attendance_sheet_batch_view.xml',


    ],

    'license': 'OPL-1',
    'demo': [
        'demo/demo.xml',
    ],
}
