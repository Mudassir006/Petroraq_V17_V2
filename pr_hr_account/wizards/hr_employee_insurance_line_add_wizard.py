from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from hijri_converter import Gregorian
from datetime import date


class HREmployeeMedicalInsuranceLineAddWizard(models.Model):
    """
    """

    # region [Initial]
    _inherit = 'hr.employee.medical.insurance.line.add.wizard'
    # endregion [Initial]

    # region [Fields]

    # endregion [Fields]

    def action_renew(self):
        insurance_line_id = super().action_renew()
        bank_account_id = self.env["account.account"].sudo().search([("code", "=", "1001.02.00.07")], limit=1)
        account_id = bank_account_id if bank_account_id else self.env["account.account"].sudo().browse(749)
        bank_payment_id = self.env["pr.account.bank.payment"].sudo().create({
            "account_id": account_id.id,
            "description": f"Payment For Medical Insurance of  {self.employee_id.name}",
        })
        if bank_payment_id:
            insurance_line_id.bank_payment_id = bank_payment_id.id
            bank_payment_id.insurance_line_id = insurance_line_id.id
        if insurance_line_id and bank_payment_id:
            insurance_line_id.state = "in_progress"
        return insurance_line_id





