from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from hijri_converter import Gregorian
from datetime import date


class HREmployeeIqamaLineAddWizard(models.Model):
    """
    """

    # region [Initial]
    _inherit = 'hr.employee.iqama.line.add.wizard'
    # endregion [Initial]

    # region [Fields]

    # endregion [Fields]

    def action_renew(self):
        iqama_line_id = super().action_renew()
        bank_account_id = self.env["account.account"].sudo().search([("code", "=", "1001.02.00.07")], limit=1)
        account_id = bank_account_id if bank_account_id else self.env["account.account"].sudo().browse(749)
        bank_payment_id = self.env["pr.account.bank.payment"].sudo().create({
            "account_id": account_id.id,
            "description": f"Payment For Iqama of  {self.employee_id.name}",
        })
        if bank_payment_id:
            iqama_line_id.bank_payment_id = bank_payment_id.id
            bank_payment_id.iqama_line_id = iqama_line_id.id
        if iqama_line_id and bank_payment_id:
            iqama_line_id.state = "in_progress"
        return iqama_line_id





