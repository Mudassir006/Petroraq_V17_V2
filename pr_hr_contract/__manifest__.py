# -*- coding: utf-8 -*-
{
    'name': "Petroraq HR Contract",

    'summary': """
        This Module is created to manage Employee Contract""",

    'description': """
    """,

    'author': "Mahmoud Salah",
    'company': "Petroraq",
    'website': "https://webmail.petroraq.com/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Human Resources/Employees/contract',
    'version': '17.0.1.0.0',
    # any module necessary for this one to work correctly
    'depends': ['pr_hr', 'hr_contract', 'hr_payroll'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/menu_items.xml',
        'views/hr_employee.xml',
        'views/hr_contract.xml',
        'views/hr_contract_salary_rule.xml',
        'views/hr_contract_gosi.xml',
        # 'views/res_bank.xml',
        # 'queries/contract_salary_rule_query.xml',
        'data/gosi_configuration_data.xml',
        'data/salary_rule_data.xml',
        'data/ir_cron.xml',
    ],
    # only loaded in demonstration mode
    'demo': [],
    # 'assets': {
    #     'web.assets_backend': [
    #         'bof_hr/static/src/css/custom.css']}
}
