{
    'name': 'Order Line Sequences/Line Numbers',
    'version': '17.0.1.0.0',
    'category': 'Extra Tools',
    'summary': 'Sequence numbers in order lines of sales,purchase and delivery.',
    'description': """This module will help you to add sequence for order lines
    in sales, purchase and delivery. It will also add line numbers in report lines.""",
    'author': 'Mudassir',
    'company': 'Petroraq',

    'website': "https://webmail.petroraq.com/",
    'depends': ['base', 'sale_management', 'purchase', 'stock'],
    'data': [
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'views/stock_picking_views.xml',
        'views/sale_order_templates.xml',
        'views/stock_picking_templates.xml',
        'views/purchase_order_templates.xml',
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
