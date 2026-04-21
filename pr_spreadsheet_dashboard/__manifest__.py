# -*- coding: utf-8 -*-
{
    'name': "Petroraq Spreadshet Dashboard",

    'summary': """
        Manage custom development on Odoo Spreadshet Dashboard""",

    'description': """
        
    """,

    'author': "Mahmoud Salah",
    'company': "Petroraq",
    'website': "https://webmail.petroraq.com/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'dashboard',
    'version': '17.0.0.0.0',

    # any module necessary for this one to work correctly
    'depends': ['spreadsheet_dashboard'],

    # always loaded
    'data': [
        'views/menus.xml',
    ],
    # only loaded in demonstration mode
    'demo': [],
    'assets': {}
}
