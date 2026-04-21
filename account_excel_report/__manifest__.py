# -*- coding: utf-8 -*-
#################################################################################
#
#Copyright (c) 2013-Present IctPack Solutions LTD. (<http://ictpack.com>)
#
#################################################################################
{
    'name': "Accounting Reports to Excel",

    'summary': """
        Generate Account ledger, trial balance, financial report, balance sheet Excel Report""",

    'description': """
        Generate Account ledger, trial balance, financial report, balance sheet Excel Report
    """,
    "version": '17.0.1.0',
    "author": "IctPack Solutions LTD",
    'website': "https://ictpack.com",
    'category': 'Accounting',
    'license': 'OPL-1',
    'support': 'projects@ictpack.com',
    'price': 39,
    'currency':'EUR',
   

    # any module necessary for this one to work correctly
    'depends': ['accounting_pdf_reports'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        # 'views/account_reports.xml',
        'wizard/aged_partner.xml',
        'wizard/journal_audit.xml',
        'wizard/partner_ledger.xml',
        'wizard/general_ledger.xml',
        'wizard/trial_balance.xml',
        'wizard/account_financial.xml',
        'wizard/account_tax.xml',
        'wizard/account_common_report.xml',
    ],
    # only loaded in demonstration mode
    'demo': [

    ],

    'images': [
        'static/description/banner.png'
    ],
}
