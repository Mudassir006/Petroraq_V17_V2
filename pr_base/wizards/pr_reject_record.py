
from odoo import models, fields, api


class PrRejectRecord(models.TransientModel):
    _name = "pr.reject.record.wizard"
    _description = "Reject Record"

    # region [Fields]

    record_id = fields.Reference(selection='_select_target_model', string='Record', required=True)
    reject_reason = fields.Text(string="Reject Reason")

    # endregion [Fields]

    @api.model
    def _select_target_model(self):
        models = self.env['ir.model'].search([])
        return [(model.model, model.name) for model in models]

    def action_reject(self):
        for wizard in self:
            wizard.record_id.sudo().write({"reject_reason": wizard.reject_reason, "state": "reject"})
            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': 'Rejected Successfully',
                    'type': 'rainbow_man',
                }
            }
