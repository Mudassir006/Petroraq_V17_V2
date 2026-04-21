{
    'name': "Customer Inquiry Management",
    'version': '1.0',
    'summary': "Record customer inquiries and convert them into sale quotations. Simple intake form without product lines.",
    'description': """
    Customer Inquiry Management Module
    ==================================

    - Register customer inquiries easily
    - Store contact details, deadline & DOS dates
    - Convert inquiry into Quotation directly
    - Linked Quotation reference inside Inquiry form
    - Clean UI (No Products, No Order Lines)
    - Foundation for advanced Estimation workflow

    
    """,

    'author': "Petroraq Engineering",
    'website': "https://www.petroraq.com",
    'license': 'LGPL-3',
    'category': 'Sales',
    'depends': ['base', 'mail', 'sale','petroraq_sale_workflow'],
    'data': [
        'data/sequence.xml',
        'views/order_inq.xml',
        'views/order_inquiry_extend_deadline_wizard.xml',
        'views/estimation_views.xml',
        'views/order_inquiry_cron.xml',

        'security/ir.model.access.csv',
    ],
    'assets': {},

    'application': True,
    'installable': True,
    'auto_install': False,
}
