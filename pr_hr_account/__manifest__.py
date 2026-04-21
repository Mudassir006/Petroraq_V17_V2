# -*- coding: utf-8 -*-
{
    'name': "Petroraq HR Account",
    'summary': """
        This Module is created to manage HR Accounting""",

    'description': """
        
    """,

    'author': "Mahmoud Salah",
    'company': "Petroraq",
    'website': "https://webmail.petroraq.com/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Accounting/Accounting',
    'version': '17.0.1.0.0',
    "license": "LGPL-3",
    # any module necessary for this one to work correctly
    'depends': ['pr_account'],

    # always loaded
    'data': [
        'views/account_analytic_account.xml',
        'views/account_move.xml',
        'views/account_move_line.xml',
        'views/payment_receipt.xml',
        'views/transaction_payment.xml',
        'views/cash_receipt.xml',
        'views/cash_payment.xml',
        'views/bank_receipt.xml',
        'views/bank_payment.xml',
        'views/hr_employee.xml',
        'views/hr_department.xml',
        'data/analytic_plan_data.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
    'assets': {
    }
}
