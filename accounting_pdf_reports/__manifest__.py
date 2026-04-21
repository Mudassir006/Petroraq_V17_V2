# -*- coding: utf-8 -*-

{
    'name': 'Odoo 17 Accounting Financial Reports',
    'version': '17.0.2.0.4',
    'category': 'Invoicing Management',
    'description': 'Accounting Reports For Odoo 17, Accounting Financial Reports, '
                   'Odoo 17 Financial Reports',
    'summary': 'Accounting Reports For Odoo 17',
    'sequence': '1',
    'author': 'Odoo Mates, Odoo SA',
    'license': 'LGPL-3',
    'company': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'website': 'https://www.youtube.com/watch?v=yA4NLwOLZms',
    'depends': ['eg_asset_management'],
    'live_test_url': 'https://www.youtube.com/watch?v=yA4NLwOLZms',
    'data': [
        'security/ir.model.access.csv',
        'views/ledger_fix.xml',
        'views/ledger_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': ['static/description/banner.gif'],
}