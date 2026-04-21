from odoo import _, fields, models
from odoo.exceptions import UserError


class RFQComparisonSelectionWizard(models.TransientModel):
    _name = "rfq.comparison.selection.wizard"
    _description = "RFQ Comparison Selection"

    requisition_id = fields.Many2one(
        "purchase.requisition",
        string="Purchase Requisition",
        required=True,
        domain=[("rfq_count", ">", 0)],
    )

    def action_view_comparison(self):
        self.ensure_one()
        requisition = self.requisition_id
        if not requisition:
            raise UserError(_("Please select a purchase requisition."))

        wizard = self.env["rfq.comparison.wizard"].create_for_requisition(requisition)
        return {
            "type": "ir.actions.act_window",
            "name": _("RFQ Comparison"),
            "res_model": "rfq.comparison.wizard",
            "view_mode": "form",
            "target": "current",
            "res_id": wizard.id,
            "context": {"form_view_initial_mode": "edit"},
        }