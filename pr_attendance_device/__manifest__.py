{
    'name': "Biometric Attendance Machines Integration",
    'author': "Guess Who",
    'website': 'mudassir',
    'version': '1.1.8',
    'license': 'LGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['hr_attendance', 'or_base'],

    'external_dependencies': {
        'python': ['setuptools'],
    },
    # always loaded
    'data': [
        'data/scheduler_data.xml',
        'data/attendance_state_data.xml',
        'data/mail_template_data.xml',
        'data/attendance_device_trans_flag_data.xml',
        'security/module_security.xml',
        'security/ir.model.access.csv',
        'views/menu_view.xml',
        'views/attendance_device_views.xml',
        'views/attendance_state_views.xml',
        'views/attendance_device_location.xml',
        'views/device_user_views.xml',
        'views/hr_attendance_views.xml',
        'views/hr_employee_views.xml',
        'views/user_attendance_views.xml',
        'views/attendance_activity_views.xml',
        'views/attendance_command_to_device_view.xml',
        'views/attendance_datalog_from_device_view.xml',
        'views/finger_template_views.xml',
        'wizard/employee_upload_wizard.xml',
        'wizard/device_confirm_wizard.xml',
    ],
    'images': ['static/description/main_screenshot.png'],
    'installable': True,

}
