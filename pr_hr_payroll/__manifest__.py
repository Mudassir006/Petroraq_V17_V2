# -*- coding: utf-8 -*-
{
    'name': "Petroraq HR Payroll",

    'summary': """
        This Module is created to manage payroll""",

    'description': """
    """,

    'author': "Mahmoud Salah",
    'company': "Petroraq",
    'website': "https://webmail.petroraq.com/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Human Resources/Payroll',
    'version': '17.0.1.0.0',
    # any module necessary for this one to work correctly
    'depends': ['pr_hr_contract'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/hr_contract.xml',
        'views/hr_salary_rule.xml',
        'views/hr_salary_attachment_type.xml',
        'views/hr_payslip_hold_views.xml',
        'views/hr_salary_attachment.xml',
        'views/bank_payment.xml',
        'views/hr_payslip_run.xml',
        'views/hr_payslip.xml',
        'wizards/hr_salary_attachment_pay_wizard.xml',

        'data/data.xml',
    ],
    "assets": {
        "web.assets_backend": [
            "pr_hr_payroll/static/src/components/payroll_batch_xlsx_report/payroll_batch_xlsx_report.js",
            "pr_hr_payroll/static/src/components/payroll_batch_xlsx_report/payroll_batch_xlsx_report.xml",
            "pr_hr_payroll/static/src/components/payroll_batch_xlsx_report/payroll_batch_xlsx_report.css",
        ],
    },
    # only loaded in demonstration mode
    'demo': [],
}
