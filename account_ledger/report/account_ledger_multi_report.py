# -*- coding: utf-8 -*-

from datetime import datetime

from odoo import api, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT


class AccountLedgerMultiReport(models.AbstractModel):
    _name = "report.account_ledger.account_ledger_multi_rep"

    def _get_valuation_dates(self, start_date, end_date):
        date_start = datetime.strptime(start_date, DATE_FORMAT).date()
        date_end = datetime.strptime(end_date, DATE_FORMAT).date()
        return f"{date_start} To {date_end}"

    def _build_account_docs(self, account_id, data, analytic_ids, str_analytic_ids):
        date_start = data["form"]["date_start"]
        date_end = data["form"]["date_end"]
        company = data["form"]["company"]
        main_head = data["form"].get("main_head")
        department = data["form"].get("department")
        section = data["form"].get("section")
        project = data["form"].get("project")
        employee = data["form"].get("employee")
        asset = data["form"].get("asset")

        date_start_value = datetime.strptime(date_start, DATE_FORMAT).date()
        date_end_value = datetime.strptime(date_end, DATE_FORMAT).date()
        ji_domain = [
            ("company_id", "=", company),
            ("date", ">=", date_start_value),
            ("date", "<=", date_end_value),
            ("move_id.state", "=", "posted"),
            ("account_id", "=", account_id),
        ]
        opening_balance_domain = [
            ("company_id", "=", company),
            ("date", ">=", date_start_value),
            ("date", "<=", date_end_value),
            ("move_id.state", "=", "posted"),
            ("account_id", "=", account_id),
        ]

        if analytic_ids:
            opening_balance_domain.append(("analytic_distribution", "in", analytic_ids))
        if department:
            ji_domain.append(("analytic_distribution", "in", [int(department)]))

        journal_items = self.env["account.move.line"].search(ji_domain, order="date asc")

        if journal_items and section:
            journal_items = self.env["account.move.line"].search(
                [("id", "in", journal_items.ids), ("analytic_distribution", "in", [int(section)])], order="date asc"
            )
        if journal_items and project:
            journal_items = self.env["account.move.line"].search(
                [("id", "in", journal_items.ids), ("analytic_distribution", "in", [int(project)])], order="date asc"
            )
        if journal_items and employee:
            journal_items = self.env["account.move.line"].search(
                [("id", "in", journal_items.ids), ("analytic_distribution", "in", [int(employee)])], order="date asc"
            )
        if journal_items and asset:
            journal_items = self.env["account.move.line"].search(
                [("id", "in", journal_items.ids), ("analytic_distribution", "in", [int(asset)])], order="date asc"
            )

        initial_balance = 0
        if main_head not in ("revenue", "expense"):
            where_statement = f"""
                WHERE aml.account_id = {account_id}
                AND
                aml.date < '{date_start}'
                AND am.state = 'posted'"""

            if analytic_ids:
                if "WHERE" in where_statement:
                    where_statement += f""" AND
                        analytic_distribution ?& array{str_analytic_ids}"""
                else:
                    where_statement += f""" WHERE
                        analytic_distribution ?& array{str_analytic_ids}"""

            sql = f"""
                SELECT
                    SUM(aml.balance)
                FROM
                    account_move_line aml
                JOIN
                    account_move am ON aml.move_id = am.id
                {where_statement}
                GROUP BY aml.account_id
            """
            self.env.cr.execute(sql)
            result = self.env.cr.fetchone()
            initial_balance = result[0] if result and result[0] else 0

        filtered_items = journal_items
        if main_head in ("revenue", "expense"):
            move_ids = journal_items.mapped("move_id").ids
            account_types = (
                ("income", "other_income") if main_head == "revenue" else ("expense", "cost_of_revenue")
            )
            filtered_items = self.env["account.move.line"].search(
                [
                    ("move_id", "in", move_ids),
                    ("account_id.account_type", "in", account_types),
                    ("company_id", "=", company),
                    ("date", ">=", date_start_value),
                    ("date", "<=", date_end_value),
                    ("move_id.state", "=", "posted"),
                ],
                order="date asc",
            )

        t_debit = 0
        t_credit = 0
        running_balance = 0
        docs = []

        for item in filtered_items:
            running_balance += item.credit - item.debit
            t_debit += item.debit
            t_credit += item.credit
            docs.append(
                {
                    "transaction_ref": item.move_id.name,
                    "date": item.date,
                    "description": item.name,
                    "reference": item.ref,
                    "journal": item.journal_id.name,
                    "initial_balance": "{:,.2f}".format(initial_balance),
                    "debit": "{:,.2f}".format(item.debit),
                    "credit": "{:,.2f}".format(item.credit),
                    "balance": "{:,.2f}".format(running_balance),
                }
            )

        if not docs:
            docs.append(
                {
                    "transaction_ref": " ",
                    "date": date_start,
                    "description": "No matching entries",
                    "reference": " ",
                    "journal": " ",
                    "initial_balance": "{:,.2f}".format(initial_balance),
                    "debit": "{:,.2f}".format(0),
                    "credit": "{:,.2f}".format(0),
                    "balance": "{:,.2f}".format(0),
                }
            )

        docs.append(
            {
                "transaction_ref": False,
                "date": " ",
                "description": " ",
                "reference": " ",
                "journal": " ",
                "initial_balance": "{:,.2f}".format(initial_balance),
                "debit": "{:,.2f}".format(t_debit),
                "credit": "{:,.2f}".format(t_credit),
                "balance": "{:,.2f}".format(running_balance),
            }
        )

        totals = {
            "debit": t_debit,
            "credit": t_credit,
            "balance": running_balance,
        }

        return docs, totals

    @api.model
    def _get_report_values(self, docids, data=None):
        account_ids = data["form"]["account"]
        date_start = data["form"]["date_start"]
        date_end = data["form"]["date_end"]
        company = data["form"]["company"]
        main_head = data["form"].get("main_head")
        sort_by = data["form"].get("sort_by")
        sort_order = data["form"].get("sort_order", "desc")
        wizard = self.env[data["model"]].browse(data["ids"]) if data.get("ids") else self.env[data["model"]]
        if not account_ids and wizard:
            account_ids = wizard._get_report_account_ids()
            data["form"]["account"] = account_ids

        analytic_ids = []
        str_analytic_ids = []
        for key in ("department", "section", "project", "employee", "asset"):
            if data["form"].get(key):
                analytic_ids.append(int(data["form"][key]))
                str_analytic_ids.append(str(data["form"][key]))

        report_date = datetime.today().strftime("%b-%d-%Y")
        company_name = self.env["res.company"].browse(company).name
        account_names = ", ".join(self.env["account.account"].browse(account_ids).mapped("name"))

        accounts = []
        accounts_summary = []
        for account_id in account_ids:
            account = self.env["account.account"].browse(account_id)
            docs, totals = self._build_account_docs(account_id, data, analytic_ids, str_analytic_ids)
            accounts_summary.append(
                {
                    "account_name": account.display_name,
                    "debit": totals["debit"],
                    "credit": totals["credit"],
                    "balance": totals["balance"],
                }
            )
            accounts.append(
                {
                    "account_name": account.display_name,
                    "docs": docs,
                    "main_head": main_head,
                }
            )

        if sort_by == "amount":
            reverse = sort_order != "asc"
            if main_head == "expense":
                sort_key = lambda item: item["debit"]
            elif main_head == "revenue":
                sort_key = lambda item: item["credit"]
            else:
                sort_key = lambda item: item["balance"]
            accounts_summary.sort(key=sort_key, reverse=reverse)
            summary_by_name = {item["account_name"]: item for item in accounts_summary}
            accounts.sort(key=lambda item: sort_key(summary_by_name[item["account_name"]]), reverse=reverse)

        return {
            "doc_ids": data["ids"],
            "doc_model": data["model"],
            "valuation_date": self._get_valuation_dates(date_start, date_end),
            "account": f"{company_name} - {account_names}" if account_names else company_name,
            "report_date": report_date,
            "accounts": accounts,
            "accounts_summary": accounts_summary,
        }