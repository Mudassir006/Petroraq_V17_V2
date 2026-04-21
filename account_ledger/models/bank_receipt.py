from odoo import api, fields, models, _
from datetime import datetime, date


class AccountBankReceipt(models.Model):
    # region [Initial]
    _inherit = 'pr.account.bank.receipt'
    # endregion [Initial]

    # region [Methods]

    def open_account_id_ledger_report(self):
        for rec in self:
            account_ledger_id = self.env["account.ledger"].sudo().create({
                "date_start": date(2025, 1, 1),
                "date_end": fields.Date.today(),
                "account_id": rec.account_id.id,
                "company_id": self.env.company.id,
            })
            if account_ledger_id:
                account_ledger_id.prepare_account_ids_domain()
                account_ledger_report_xlsx = account_ledger_id.print_xlsx_report()
                return account_ledger_report_xlsx
            else:
                return {
                    'effect': {
                        'fadeout': 'slow',
                        'message': 'There Is Something Wrong, Please Check',
                        'type': 'rainbow_man',
                    }
                }

    # endregion [Methods]