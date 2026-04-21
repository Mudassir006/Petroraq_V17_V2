# -*- coding: utf-8 -*-
{
    'name': "Petroraq Pr_Account",
    'summary': """
        This Module is created to manage Accounting""",

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
    'depends': ['account_accountant', 'account_reports'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/groups.xml',
        'security/hr_security.xml',
        'data/journal_voucher.xml',
        'views/menu_items.xml',
        'views/account_account.xml',
        'views/account_analytic_plan.xml',
        'views/account_analytic_account.xml',
        'views/account_move.xml',
        'views/account_move_line.xml',
        'views/payment_receipt.xml',
        'views/reject_reason_wizard.xml',
        'views/bank_payment_reject_reason_wizard.xml',
        'views/transaction_payment.xml',
        'views/cash_receipt.xml',
        'views/cash_payment.xml',
        'views/bank_receipt.xml',
        'views/bank_payment.xml',
        # "views/account_payment_register_view.xml",

        # 'views/journal_voucher_view.xml',
        'data/ir_sequence.xml',
        'data/analytic_plan_data.xml',

        'data/journal_voucher.xml',

    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'pr_account/static/src/js/list_renderer_bottom_pager.js',
            'pr_account/static/src/xml/list_renderer_extend.xml',
            'pr_account/static/src/scss/list_renderer_bottom_pager.scss',
            'pr_account/static/src/css/custom.css',
        ]
    }
}
