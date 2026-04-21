# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountLedgerMulti(models.TransientModel):
    _name = "account.ledger.multi"
    _description = "Account Ledger (Multi Accounts)"

    def _default_date_start(self):
        today = fields.Date.context_today(self)
        return today.replace(day=1)

    date_start = fields.Date(
        string="Start Date",
        required=True,
        default=_default_date_start,
    )
    date_end = fields.Date(string="End Date", required=True, default=fields.Date.today)
    account_ids = fields.Many2many("account.account", string="Accounts")
    account_domain = fields.Char(compute="_compute_account_domain")
    main_head = fields.Selection(
        [
            ("revenue", "Revenue"),
            ("expense", "Expense"),
        ],
        string="Main Head",
    )
    sort_by = fields.Selection(
        [
            ("amount", "Amount"),
        ],
        string="Sort By",
        default="amount",
    )
    sort_order = fields.Selection(
        [
            ("desc", "Highest First"),
            ("asc", "Lowest First"),
        ],
        string="Sort Order",
        default="desc",
    )
    company_id = fields.Many2one("res.company", required=True, string="Company", default=lambda self: self.env.company)
    department_id = fields.Many2one(
        "account.analytic.account",
        string="Department",
        domain="[('analytic_plan_type', '=', 'department')]",
    )
    section_id = fields.Many2one(
        "account.analytic.account",
        string="Section",
        domain="[('analytic_plan_type', '=', 'section')]",
    )
    project_id = fields.Many2one(
        "account.analytic.account",
        string="Project",
        domain="[('analytic_plan_type', '=', 'project')]",
    )
    employee_id = fields.Many2one(
        "account.analytic.account",
        string="Employee",
        domain="[('analytic_plan_type', '=', 'employee')]",
    )
    asset_id = fields.Many2one(
        "account.analytic.account",
        string="Asset",
        domain="[('analytic_plan_type', '=', 'asset')]",
    )

    @api.depends("date_start", "date_end")
    def _compute_account_domain(self):
        for rec in self:
            if self.env.user.has_group("account.group_account_manager") or self.env.user.has_group(
                "pr_account.custom_group_accounting_manager"
            ):
                rec.account_domain = "[('deprecated','=',False)]"
            else:
                rec.account_domain = "[('deprecated','=',False), ('id', 'not in', [748, 749, 1132])]"

    def _get_report_account_ids(self):
        self.ensure_one()
        if self.account_ids:
            return self.account_ids.ids
        if self.main_head == "revenue":
            return self.env["account.account"].search([("account_type", "in", ["income", "other_income"])]).ids
        if self.main_head == "expense":
            return self.env["account.account"].search(
                [("account_type", "in", ["expense", "cost_of_revenue"])]
            ).ids
        return []

    def get_report(self):
        account_ids = self._get_report_account_ids()
        data = {
            "ids": self.ids,
            "model": self._name,
            "form": {
                "date_start": self.date_start.strftime("%Y-%m-%d"),
                "date_end": self.date_end.strftime("%Y-%m-%d"),
                "account": account_ids,
                "company": self.company_id.id,
                "main_head": self.main_head,
                "sort_by": self.sort_by,
                "sort_order": self.sort_order,
                "department": self.department_id.id if self.department_id else False,
                "section": self.section_id.id if self.section_id else False,
                "project": self.project_id.id if self.project_id else False,
                "employee": self.employee_id.id if self.employee_id else False,
                "asset": self.asset_id.id if self.asset_id else False,
            },
        }
        return self.env.ref("account_ledger.acc_leg_multi_report").report_action(self, data=data)

    def print_xlsx_report(self):
        return self.env.ref("account_ledger.account_ledger_multi_xlsx_report_view_xlsx").report_action(
            self, data=None
        )