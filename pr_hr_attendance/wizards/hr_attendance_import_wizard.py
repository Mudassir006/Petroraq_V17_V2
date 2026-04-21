from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from hijri_converter import Gregorian
from datetime import date
import pandas as pd
import base64
from io import BytesIO
import json


class HRAttendanceImportWizard(models.Model):
    """
    """

    # region [Initial]
    _name = 'hr.attendance.import.wizard'
    _description = 'HR Attendance Import Wizard'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    # endregion [Initial]

    # region [Fields]

    file_attachment = fields.Binary(string='Attendance Sheet', attachment=True, required=True)
    attachment_file_name = fields.Char('File Name', required=False)

    # endregion [Fields]

    def action_import(self):
        for wizard in self:
            attendance_file = wizard.file_attachment
            file_data = base64.b64decode(attendance_file)
            excel_data = BytesIO(file_data)
            data = pd.read_excel(excel_data)
            dict_data = data.to_dict(orient='records')

            # Convert each row to a dictionary

            # Print the result
            for row in dict_data:
                employee_id = self.env["hr.employee"].search([("code", "=", str(row.get("Name")).split())], limit=1)
                if not employee_id:
                    raise ValidationError("Employee Not Exist")
                if isinstance(row.get("Date"), datetime):
                    day_date = row.get("Date").date()
                else:
                    day_date = datetime.strptime(row.get("Date"), '%d/%m/%Y').date()
                    # day_date = datetime.strptime(row.get("Date"), '%Y-%m-%d').date()
                check_in = row.get("Checkin")
                if isinstance(check_in, str):
                    check_in = datetime.strptime(check_in, '%H:%M').time()
                check_in_time = datetime.combine(day_date, check_in)
                check_out = row.get("Checkout")
                if isinstance(check_out, str):
                    check_out = datetime.strptime(check_out, '%H:%M').time()
                    check_out_time = datetime.combine(day_date, check_out)
                elif isinstance(check_out, float):
                    check_out_time = datetime.combine(day_date, datetime.min.time()).replace(hour=17)
                else:
                    if isinstance(check_out, datetime):
                        print("kk")
                    check_out_time = datetime.combine(day_date, check_out)


                # check_out_time = check_out
                # if check_out:
                #     if isinstance(check_out, str):
                #         check_out = datetime.strptime(check_out, '%H:%M').time()
                #         check_out_time = datetime.combine(day_date, check_out)
                #     elif isinstance(check_out, float):
                #
                #         check_out_time = datetime.combine(day_date, datetime.min.time()).replace(hour=17)
                #         # check_out_time = datetime.combine(check_out, datetime.min.time())
                #     else:
                #         check_out_time = check_out
                # else:
                #     check_out_time = datetime.combine(check_out, datetime.min.time()).replace(hour=17)
                attendance_id = self.env["hr.attendance"].create({
                    "employee_id": employee_id.id,
                    "check_in": check_in_time - relativedelta(hours=3),
                    "check_out": check_out_time - relativedelta(hours=3),
                })

    # def action_import(self):
    #     for wizard in self:
    #         account_file = wizard.file_attachment
    #         file_data = base64.b64decode(account_file)
    #         excel_data = BytesIO(file_data)
    #         data = pd.read_excel(excel_data)
    #         dict_data = data.to_dict(orient='records')
    #
    #         # Convert each row to a dictionary
    #
    #         # Print the result
    #         for row in dict_data:
    #             project_id = False
    #             partner_id = False
    #             tax_id = False
    #             debit = 0
    #             credit = 0
    #             account_id = self.env["account.account"].search([("name", "=", str(row.get("Account")).strip())], limit=1)
    #             if not account_id:
    #                 raise ValidationError("Account Not Exist")
    #             # Check for NaN in Debit
    #             if pd.notna(row.get("Debit")):
    #                 debit = float(row.get("Debit"))
    #             else:
    #                 debit = 0
    #
    #             # Check for NaN in Credit
    #             if pd.notna(row.get("Credit")):
    #                 credit = float(row.get("Credit"))
    #             else:
    #                 credit = 0
    #             label = row.get("Label")
    #             move_id = self.env["account.move"].search([("name", "=", str(row.get("move_id")).strip())],
    #                                                             limit=1)
    #             if not move_id:
    #                 raise ValidationError("Account Move Not Exist Not Exist")
    #
    #             journal_id = self.env["account.journal"].search([("name", "=", str(row.get("journal_id")).strip())],
    #                                                       limit=1)
    #             if not journal_id:
    #                 raise ValidationError("Journal Not Exist Not Exist")
    #
    #             if row.get("Project"):
    #                 project_id = self.env["account.analytic.account"].search([("name", "=", str(row.get("Project")).strip())],
    #                                                             limit=1)
    #             if row.get("Partner"):
    #                 partner_id = self.env["res.partner"].search([("name", "=", str(row.get("Partner")).strip())],
    #                                                             limit=1)
    #             if row.get("Taxes"):
    #                 tax_id = self.env["account.tax"].search([("name", "=", str(row.get("Taxes")).strip())],
    #                                                             limit=1)
    #             display_type = str(row.get("Display_Type"))
    #             qty = float(row.get("Quantity"))
    #             if project_id:
    #                 analytic_distribution = {str(project_id.id): 100}
    #             else:
    #                 analytic_distribution = False
    #
    #             vals = {
    #                 "account_id": account_id.id,
    #                 "move_id": move_id.id,
    #                 "partner_id": partner_id.id if partner_id else False,
    #                 "debit": debit,
    #                 "credit": credit,
    #                 "name": label,
    #                 "display_type": display_type,
    #                 "tax_ids": tax_id.ids if tax_id else False,
    #                 "analytic_distribution": analytic_distribution if analytic_distribution else False,
    #             }
    #
    #             journal_item_id = self.env["account.move.line"].with_context(check_move_validity=False, skip_invoice_sync=True).create(vals)
