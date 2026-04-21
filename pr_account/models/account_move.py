from odoo import api, fields, models
import requests
import json


class AccountMove(models.Model):
    # region [Initial]
    _inherit = 'account.move'
    # endregion [Initial]

    old_id = fields.Integer(string="Old ID")
    journal_voucher_view = fields.Boolean()
    bpv_id = fields.Many2one(
        "pr.account.bank.payment",
        string="Bank Payment",
        compute="_compute_pr_vouchers",
        store=False,
    )
    cpv_id = fields.Many2one(
        "pr.account.cash.payment",
        string="Cash Payment",
        compute="_compute_pr_vouchers",
        store=False,
    )
    brv_id = fields.Many2one(
        "pr.account.bank.receipt",
        string="Bank Receipt",
        compute="_compute_pr_vouchers",
        store=False,
    )
    crv_id = fields.Many2one(
        "pr.account.cash.receipt",
        string="Cash Receipt",
        compute="_compute_pr_vouchers",
        store=False,
    )
    # jv_id = fields.Many2one(
    #     "pr.account.journal.voucher",
    #     string="Journal Voucher",
    #     compute="_compute_pr_vouchers",
    #     store=False,
    # )

    has_pr_voucher = fields.Boolean(
        string="Has PR Voucher",
        compute="_compute_pr_vouchers",
        store=False,
    )

    def action_open_bpv(self):
        self.ensure_one()
        if not self.bpv_id:
            return
        return {
            "type": "ir.actions.act_window",
            "name": "Bank Payment",
            "res_model": "pr.account.bank.payment",
            "view_mode": "form",
            "res_id": self.bpv_id.id,
        }

    def action_open_cpv(self):
        self.ensure_one()
        if not self.cpv_id:
            return
        return {
            "type": "ir.actions.act_window",
            "name": "Cash Payment",
            "res_model": "pr.account.cash.payment",
            "view_mode": "form",
            "res_id": self.cpv_id.id,
        }

    def action_open_brv(self):
        self.ensure_one()
        if not self.brv_id:
            return
        return {
            "type": "ir.actions.act_window",
            "name": "Bank Receipt",
            "res_model": "pr.account.bank.receipt",
            "view_mode": "form",
            "res_id": self.brv_id.id,
        }

    def action_open_crv(self):
        self.ensure_one()
        if not self.crv_id:
            return
        return {
            "type": "ir.actions.act_window",
            "name": "Cash Receipt",
            "res_model": "pr.account.cash.receipt",
            "view_mode": "form",
            "res_id": self.crv_id.id,
        }

    # def action_open_jjv(self):
    #     self.ensure_one()
    #     if not self.jv_id:
    #         return
    #     return {
    #         "type": "ir.actions.act_window",
    #         "name": "Journal Voucher",
    #         "res_model": "pr.account.journal.voucher",
    #         "view_mode": "form",
    #         "res_id": self.jv_id.id,
    #     }

    def _search_default_journal(self):
        """Keep custom payment/statement shortcuts, but defer default selection to core.

        Odoo core handles move type/context interactions (e.g. vendor bills must use a
        purchase journal). Delegating to ``super()`` avoids selecting an invalid journal
        type during bill creation from Purchase Orders.
        """
        if self.payment_id and self.payment_id.journal_id:
            return self.payment_id.journal_id
        if self.statement_line_id and self.statement_line_id.journal_id:
            return self.statement_line_id.journal_id
        if self.statement_line_ids.statement_id.journal_id:
            return self.statement_line_ids.statement_id.journal_id[:1]

        return super()._search_default_journal()


    @api.model
    def _get_purchase_journal_for_company(self, company_id=None):
        company = self.env["res.company"].browse(company_id) if company_id else (self.company_id or self.env.company)
        return self.env["account.journal"].search([
            ("type", "=", "purchase"),
            ("company_id", "=", company.id),
        ], order="id asc", limit=1)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            move_type = vals.get("move_type") or self._context.get("default_move_type")
            if move_type not in ("in_invoice", "in_refund"):
                continue

            journal_id = vals.get("journal_id")
            company_id = vals.get("company_id") or self._context.get("default_company_id")
            if journal_id:
                journal = self.env["account.journal"].browse(journal_id)
                if journal.type != "purchase":
                    purchase_journal = self._get_purchase_journal_for_company(company_id=company_id)
                    if purchase_journal:
                        vals["journal_id"] = purchase_journal.id
            else:
                purchase_journal = self._get_purchase_journal_for_company(company_id=company_id)
                if purchase_journal:
                    vals["journal_id"] = purchase_journal.id

        return super().create(vals_list)

    def _compute_pr_vouchers(self):
        BankPayment = self.env["pr.account.bank.payment"]
        CashPayment = self.env["pr.account.cash.payment"]
        BankReceipt = self.env["pr.account.bank.receipt"]
        CashReceipt = self.env["pr.account.cash.receipt"]
        # JournalVoucher = self.env["pr.account.journal.voucher"]

        for move in self:
            move.bpv_id = BankPayment.search([("journal_entry_id", "=", move.id)], limit=1)
            move.cpv_id = CashPayment.search([("journal_entry_id", "=", move.id)], limit=1)
            move.brv_id = BankReceipt.search([("journal_entry_id", "=", move.id)], limit=1)
            move.crv_id = CashReceipt.search([("journal_entry_id", "=", move.id)], limit=1)
            # move.jv_id = JournalVoucher.search([("journal_entry_id", "=", move.id)], limit=1)

            move.has_pr_voucher = bool(
                move.bpv_id or move.cpv_id or move.brv_id or move.crv_id
            )

    def get_attachments_data(self):
        for move in self:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            response = requests.request('GET',
                                        url=f"https://shakilkhan8-petroraq-engineering-services.odoo.com/api/journal_entry/attachments",
                                        timeout=60)
            if response.status_code == 200:
                response_json = response.json()
                result = response_json.get("result")
                for k, v in result.items():
                    journal_entry_id = self.env["account.move"].search([("old_id", "=", int(k))], limit=1)
                    if journal_entry_id:
                        attachment_ids = []
                        for attachment_item in v:
                            attachment = {
                                'res_name': attachment_item.get("res_name"),
                                'res_model': 'account.move',
                                'res_id': journal_entry_id.id,
                                'datas': attachment_item.get("datas"),
                                'type': 'binary',
                                'name': attachment_item.get("name"),
                            }
                            attachment_obj = self.env['ir.attachment']
                            att_record = attachment_obj.sudo().create(attachment)
                            attachment_ids.append(att_record.id)
                        if attachment_ids:
                            journal_entry_id.sudo().update({'attachment_ids': [(6, 0, attachment_ids)]})
                            print("success")