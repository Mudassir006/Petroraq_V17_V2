# -*- coding: utf-8 -*-
{
    "name": "Service Receipt Note",
    "version": "17.0.1.0.0",
    "summary": "Service Receipt Note for Purchase Orders",
    "description": """
Service Receipt Note for Odoo 17

Features:
- Create Service Receipt Note from Purchase Order
- Only service products are included
- Partial receipt supported
- Auto backorder for remaining quantity
- Smart button on Purchase Order
- SRN menus in Purchase and Inventory
    """,
    "category": "Purchase",
    "author": "Custom Clean-Room Implementation",
    "license": "LGPL-3",
    "depends": ["purchase", "stock", "mail", "account", "pr_custom_purchase", "pr_work_order"],
    "data": [
        "security/ir.model.access.csv",
        "data/service_receipt_sequence.xml",
        "views/service_receipt_views.xml",
        "views/purchase_order_views.xml",
        "views/work_order_views.xml",
    ],
    "application": False,
    "installable": True,
}
