# -*- coding: utf-8 -*-
from odoo import models, fields, api

class VatLedgerResult(models.TransientModel):
    _name = "vat.ledger.result"
    _description = "VAT Ledger Result Container"

    wizard_id = fields.Many2one("vat.ledger.report.wizard")
    line_ids = fields.One2many("vat.ledger.result.line", "result_id", string="Lines")

    def name_get(self):
        result = []
        for rec in self:
            name = "VAT Ledger Result"
            result.append((rec.id, name))
        return result

    def action_export_pdf(self):
        wizard = self.wizard_id
        return wizard.get_report()

    def action_export_xlsx(self):
        wizard = self.wizard_id
        return wizard.print_xlsx_report()


class VatLedgerResultLine(models.TransientModel):
    _name = "vat.ledger.result.line"
    _description = "VAT Ledger Result Line"

    result_id = fields.Many2one("vat.ledger.result")

    transaction_ref = fields.Char("Transaction Ref")
    reference = fields.Char("Reference")
    date = fields.Date("Date")
    description = fields.Char("Description")
    amount = fields.Float("Amount")
    tax_amount = fields.Float("Tax Amount")
    total_amount = fields.Float("Total Amount")
    is_total = fields.Boolean("Is Total Line")
