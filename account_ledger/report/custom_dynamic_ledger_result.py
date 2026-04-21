# -*- coding: utf-8 -*-
from odoo import models, fields


class CustomDynamicLedgerResult(models.TransientModel):
    _name = "custom.dynamic.ledger.result"
    _description = "Custom Dynamic Ledger Result Container"

    wizard_id = fields.Many2one("custom.dynamic.ledger.report.wizard")
    line_ids = fields.One2many("custom.dynamic.ledger.result.line", "result_id", string="Lines")

    def name_get(self):
        result = []
        for rec in self:
            name = "Dynamic Balance Report"
            result.append((rec.id, name))
        return result

    def action_export_pdf(self):
        wizard = self.wizard_id
        return wizard.get_report()

    def action_export_xlsx(self):
        wizard = self.wizard_id
        return wizard.print_xlsx_report()


class CustomDynamicLedgerResultLine(models.TransientModel):
    _name = "custom.dynamic.ledger.result.line"
    _description = "Custom Dynamic Ledger Result Line"
    _order = "sequence, id"

    result_id = fields.Many2one("custom.dynamic.ledger.result", ondelete="cascade", required=True)

    # ✅ hierarchy
    parent_id = fields.Many2one("custom.dynamic.ledger.result.line", ondelete="cascade")
    child_ids = fields.One2many("custom.dynamic.ledger.result.line", "parent_id")
    level = fields.Integer(default=0)
    is_heading = fields.Boolean(default=False)
    sequence = fields.Integer(default=10)

    label = fields.Char("Account")
    initial_debit = fields.Float("Initial Debit")
    initial_credit = fields.Float("Initial Credit")
    period_debit = fields.Float("Period Debit")
    period_credit = fields.Float("Period Credit")
    ending_debit = fields.Float("Ending Debit")
    ending_credit = fields.Float("Ending Credit")
    balance = fields.Float("Balance")
    balance_type = fields.Char("Type")