

from . import models
from . import wizard

def _post_init_hook(env):
    """Deactivate the server action 'Create Vendor Bills' once this app is installed"""
    vendor_bill_server_action = env.ref("purchase.action_purchase_batch_bills")
    if vendor_bill_server_action:
        vendor_bill_server_action.write({"binding_model_id": ""})


def _uninstall_hook(env):
    """Activate the server action 'Create Vendor Bills' once this app is uninstalled"""
    model = env["ir.model"].search([("model", "=", "purchase.order")])
    vendor_bill_server_action = env.ref("purchase.action_purchase_batch_bills")

    if vendor_bill_server_action:
        vendor_bill_server_action.write({"binding_model_id": model.id})
