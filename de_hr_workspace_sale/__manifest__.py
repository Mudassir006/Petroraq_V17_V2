# -*- coding: utf-8 -*-
{
    'name': "Sales Workspace - Self Service",
    'summary': """
        Self-Service Sales
    """,
    'description': """
         
    """,
    'author': 'Mudassir',
    'website': 'https://www.petroraq.com',
    'version': '0.1',
    'category': 'Human Resources',

    # any module necessary for this one to work correctly
    'depends': ['pr_work_order', 'petroraq_sale_workflow', 'de_hr_workspace', 'pr_hr_account', 'eg_asset_management','pr_custom_purchase'],

    # always loaded
    'data': [
        'views/menus.xml',
        'views/sale_order.xml',
        'views/work_order.xml',
        'views/estimation.xml',
        'views/budget.xml',
        'views/expense_bucket.xml',
        'views/purchase_order.xml',
    ],
    # only loaded in demonstration mode
    # 'demo': [
    #     'demo/demo.xml',
    # ],
    'license': 'LGPL-3',
    'images': ['static/description/banner.jpg'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
