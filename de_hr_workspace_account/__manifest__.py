# -*- coding: utf-8 -*-
{
    'name': "HR Accounting Workspace - Self Service",
    'summary': """
        Self-Service HR Accounting
    """,
    'description': """
        The Self-Service HR Accounting Requests 
    """,
    'author': 'Dynexcel',
    'website': 'https://www.dynexcel.com',
    'version': '0.1',
    'category': 'Human Resources',

    # any module necessary for this one to work correctly
    'depends': ['de_hr_workspace','pr_hr_account', 'eg_asset_management'],

    # always loaded
    'data': [
        'views/menu.xml',
        'views/cash_payment.xml',
        'views/bank_payment.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'license': 'LGPL-3',
    'images': ['static/description/banner.jpg'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
