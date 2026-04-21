# -*- coding: utf-8 -*-

{
    'name': 'Account Ledger',
    'summary': """Account Ledger""",
    'version': '0.1',
    'description': """This module allows the user to view detailed ledger
            for a specific account and all the journal entries level detailed information
            can be drawn using this report
            """,
    'author': 'Arure Technologies',
    'company': 'Arure Technologies',
    'website': 'http://www.arure.tech/',
    'category': 'Accounting',
    'depends': ['pr_hr_account', 'eg_asset_management'],
    'price': '17.0',
    'license': 'OPL-1',
    'data': [
        'security/ir.model.access.csv',
        # 'views/dynamic_report_template.xml',
        'wizard/account_ledger.xml',
        'wizard/account_ledger_multi.xml',
        'views/account_ledger_result_views.xml',
        'views/custom_dynamic_ledger_result_views.xml',
        'views/vat_ledger_result_views.xml',
        'wizard/vat_ledger_report_wizard.xml',
        'wizard/custom_dynamic_ledger_report_wizard.xml',
        'report/account_ledger_report.xml',
        'report/account_ledger_multi_report.xml',
        'report/vat_ledger_report.xml',
        'report/custom_dynamic_ledger_report.xml',
        'report/account_ledger_xlsx_report.xml',
        'report/account_ledger_multi_xlsx_report.xml',
        'report/vat_ledger_xlsx_report.xml',
        'views/bank_payment.xml',
        'views/bank_receipt.xml',
        'views/cash_payment.xml',
        'views/cash_receipt.xml',

    ],
    'assets': {
            'web.assets_backend': [
                'account_ledger/static/src/js/ledger_hierarchy_field.js',
                'account_ledger/static/src/xml/ledger_hierarchy_field.xml',
            ],
        },
    'qweb': [],
    'images': ['static/description/banner.jpeg'],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,

}
