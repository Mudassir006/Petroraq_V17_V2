# -*- coding: utf-8 -*-
{
    'name': "Petroraq HR Org Chart",
    'summary': """
        This Module is created to manage Human Resources Org Chart""",

    'description': """
        
    """,

    'author': "Mahmoud Salah",
    'company': "Petroraq",
    'website': "https://webmail.petroraq.com/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Human Resources/Employees',
    'version': '17.0.1.0.0',
    "license": "LGPL-3",
    # any module necessary for this one to work correctly
    'depends': ['hr_org_chart', 'pr_hr'],

    # always loaded
    'data': [
        'views/hr_department_subrule.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
    'assets': {

        }
}
