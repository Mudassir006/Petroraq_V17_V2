{
    "name": "Purchase Order Prepayments (down payment)",
    "summary": """
            This module extends the functionality of Odoo 17
            to add prepayments (down payments) for the purchase order.
        """,
    "version": "17.0.1.0.1",
    "category": "Purchase",
    "website": "http://petroraq.com",
    "author": "Mudassir",

    "installable": True,
    "depends": [
        "purchase",
        "account",
        "stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/purchase_make_invoice_advance_views.xml",
        "views/purchase_management_views.xml",
        "views/res_config_settings_views.xml",
        "views/account_move_views.xml",
    ],

    "post_init_hook": "_post_init_hook",
    "uninstall_hook": "_uninstall_hook",
}
