# -*- coding: utf-8 -*-
{
    'name': "Petroraq HR",
    'summary': """
        This Module is created to manage Human Resources""",

    'description': """
        
    """,

    'author': "Mahmoud Salah",
    'company': "Petroraq",
    'website': "https://webmail.petroraq.com/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Human Resources/Employees',
    'version': '17.0.1.0.2',
    "license": "LGPL-3",
    # any module necessary for this one to work correctly
    'depends': ['hr'],

    # always loaded
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/hr_security.xml',
        'data/data.xml',
        'data/res_country_data.xml',
        'views/menu_items.xml',
        'views/hr_job.xml',
        'views/hr_department.xml',
        'views/hr_employee.xml',
        'views/hr_department_subrule.xml',
        'views/res_country.xml',
        'views/hr_employee_iqama.xml',
        'views/hr_employee_iqama_line.xml',
        'views/hr_employee_medical_insurance.xml',
        'views/hr_employee_medical_insurance_line.xml',
        # 'views/hr_employee_signature.xml',
        'views/res_config_settings.xml',
        'wizards/hr_employee_iqama_expiry_check_wizard.xml',
        'wizards/hr_employee_iqama_line_add_wizard.xml',
        'wizards/hr_employee_insurance_line_add_wizard.xml',

    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
    'assets': {

        }
}
