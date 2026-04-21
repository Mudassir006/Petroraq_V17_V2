{
    "name": "Petroraq Retention (Progress Invoice Deduction)",
    "version": "17.0.1.0.0",
    "category": "Sales",
    "summary": "Deduct retention % from each invoice like downpayment deduction.",
    "depends": ["sale", "account"],
    "data": [
        "data/retention_product.xml",
        "views/res_config_settings_views.xml",
        "views/sale_order_views.xml",
        "views/account_move_views.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
}