# -*- coding: utf-8 -*-
{
    'name': "Petroraq Base",

    'summary': """
        Manage custom development on Odoo Base Module""",

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
    'depends': ['base', 'contacts', 'product'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/menus.xml',
        'views/res_partner.xml',
        'views/product_template.xml',
        'data/product_sequence.xml',
        'wizards/pr_reject_record.xml',
    ],
    # only loaded in demonstration mode
    'demo': [],
    'assets': {}
}
