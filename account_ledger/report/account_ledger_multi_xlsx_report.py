from datetime import datetime

from odoo import models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT


class AccountLedgerMultiXlsxReport(models.AbstractModel):
    _name = "report.account_ledger.account_ledger_multi_xlsx_report"
    _inherit = "report.report_xlsx.abstract"

    def _build_account_docs(self, account_id, report_data, analytic_ids, str_analytic_ids):
        date_start = report_data["date_start"]
        date_end = report_data["date_end"]
        company = report_data["company"]
        main_head = report_data.get("main_head")
        department = report_data.get("department")
        section = report_data.get("section")
        project = report_data.get("project")
        employee = report_data.get("employee")
        asset = report_data.get("asset")

        ji_domain = [
            ("company_id", "=", company),
            ("date", ">=", datetime.strptime(str(date_start), DATE_FORMAT).date()),
            ("date", "<=", datetime.strptime(str(date_end), DATE_FORMAT).date()),
            ("move_id.state", "=", "posted"),
            ("account_id", "=", account_id),
        ]
        opening_balance_domain = [
            ("company_id", "=", company),
            ("date", ">=", datetime.strptime(str(date_start), DATE_FORMAT).date()),
            ("date", "<=", datetime.strptime(str(date_end), DATE_FORMAT).date()),
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
        if main_head == "revenue":
            filtered_items = journal_items.filtered(lambda line: line.credit > 0)
        elif main_head == "expense":
            filtered_items = journal_items.filtered(lambda line: line.debit > 0)

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
                    "initial_balance": "{:,.2f}".format(initial_balance),
                    "description": item.name,
                    "reference": item.ref,
                    "journal": item.journal_id.name,
                    "debit": "{:,.2f}".format(item.debit),
                    "credit": "{:,.2f}".format(item.credit),
                    "balance": "{:,.2f}".format(running_balance),
                }
            )

        if not docs:
            docs.append(
                {
                    "transaction_ref": " ",
                    "date": f"{str(date_start)}",
                    "initial_balance": "{:,.2f}".format(initial_balance),
                    "description": "No matching entries",
                    "reference": " ",
                    "journal": " ",
                    "debit": "{:,.2f}".format(0),
                    "credit": "{:,.2f}".format(0),
                    "balance": "{:,.2f}".format(0),
                }
            )

        docs.append(
            {
                "transaction_ref": " ",
                "date": f"{str(datetime.now().date())}",
                "initial_balance": " ",
                "description": "Totals",
                "reference": " ",
                "journal": " ",
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

    def generate_xlsx_report(self, workbook, data, wizard_id):
        report_data = {
            "date_start": wizard_id.date_start,
            "date_end": wizard_id.date_end,
            "account": wizard_id._get_report_account_ids(),
            "company": wizard_id.company_id.id,
            "main_head": wizard_id.main_head,
            "sort_by": wizard_id.sort_by,
            "sort_order": wizard_id.sort_order,
            "department": wizard_id.department_id.id if wizard_id.department_id else False,
            "section": wizard_id.section_id.id if wizard_id.section_id else False,
            "project": wizard_id.project_id.id if wizard_id.project_id else False,
            "employee": wizard_id.employee_id.id if wizard_id.employee_id else False,
            "asset": wizard_id.asset_id.id if wizard_id.asset_id else False,
        }

        analytic_ids = []
        str_analytic_ids = []
        for key in ("department", "section", "project", "employee", "asset"):
            if report_data.get(key):
                analytic_ids.append(int(report_data[key]))
                str_analytic_ids.append(str(report_data[key]))

        worksheet = workbook.add_worksheet("Account Ledger")

        title_format = workbook.add_format(
            {
                "bold": True,
                "font_size": 14,
                "bg_color": "#173b76",
                "color": "#ffffff",
                "border": 1,
                "align": "center",
                "valign": "vcenter",
            }
        )
        header_format = workbook.add_format(
            {
                "bold": True,
                "bg_color": "#173b76",
                "color": "#ffffff",
                "border": 1,
                "align": "center",
                "valign": "vcenter",
            }
        )
        money_format = workbook.add_format({"num_format": "#,##0.00", "border": 1})
        text_format = workbook.add_format({"border": 1})
        date_format = workbook.add_format({"num_format": "yyyy-mm-dd", "border": 1})

        accounts_summary = []
        account_docs = {}
        for account in self.env["account.account"].browse(report_data["account"]):
            docs, totals = self._build_account_docs(account.id, report_data, analytic_ids, str_analytic_ids)
            accounts_summary.append(
                {
                    "account_name": account.display_name,
                    "account_code": account.name,
                    "debit": totals["debit"],
                    "credit": totals["credit"],
                    "balance": totals["balance"],
                }
            )
            account_docs[account.id] = docs

        sort_by = report_data.get("sort_by")
        sort_order = report_data.get("sort_order", "desc")
        if sort_by == "amount":
            reverse = sort_order != "asc"
            if report_data.get("main_head") == "expense":
                sort_key = lambda item: item["debit"]
            elif report_data.get("main_head") == "revenue":
                sort_key = lambda item: item["credit"]
            else:
                sort_key = lambda item: item["balance"]
            accounts_summary.sort(key=sort_key, reverse=reverse)
            ordered_account_ids = [account.id for account in self.env["account.account"].browse(report_data["account"])]
            summary_by_name = {item["account_name"]: item for item in accounts_summary}
            ordered_account_ids.sort(
                key=lambda account_id: sort_key(
                    summary_by_name[self.env["account.account"].browse(account_id).display_name]
                ),
                reverse=reverse,
            )
        else:
            ordered_account_ids = report_data["account"]

        row = 0
        for account in self.env["account.account"].browse(ordered_account_ids):
            docs = account_docs.get(account.id, [])
            worksheet.merge_range(row, 0, row, 6, "Petroraq Engineering & Construction - VAT Number 311428741500003", title_format)
            worksheet.merge_range(row + 1, 0, row + 1, 6, f"{account.display_name} {account.name}", title_format)
            worksheet.merge_range(
                row + 2,
                0,
                row + 2,
                6,
                f"Period: {wizard_id.date_start.strftime('%d-%b-%Y')} to {wizard_id.date_end.strftime('%d-%b-%Y')}",
                title_format,
            )

            headers = ["Transaction Ref", "Date", "Reference", "Description", "Debit", "Credit", "Balance"]
            worksheet.write_row(row + 3, 0, headers, header_format)

            data_row = row + 4
            for entry in docs:
                is_total = entry["description"] == "Totals"
                row_format = header_format if is_total else text_format
                money_row_format = header_format if is_total else money_format
                date_row_format = header_format if is_total else date_format
                worksheet.write(data_row, 0, entry["transaction_ref"], row_format)
                worksheet.write(data_row, 1, entry["date"], date_row_format)
                worksheet.write(data_row, 2, entry["reference"], row_format)
                worksheet.write(data_row, 3, entry["description"], row_format)
                worksheet.write_number(data_row, 4, float(entry["debit"].replace(",", "")), money_row_format)
                worksheet.write_number(data_row, 5, float(entry["credit"].replace(",", "")), money_row_format)
                worksheet.write_number(data_row, 6, float(entry["balance"].replace(",", "")), money_row_format)
                data_row += 1

            row = data_row + 2

        worksheet.merge_range(row, 0, row, 4, "Summary", title_format)
        row += 1
        summary_headers = ["Account Code","Account Name", "Debit", "Credit", "Balance"]
        worksheet.write_row(row, 0, summary_headers, header_format)
        row += 1
        for summary in accounts_summary:
            worksheet.write(row, 0, summary["account_name"], text_format)
            worksheet.write(row, 1, summary["account_code"], text_format)
            worksheet.write_number(row, 2, summary["debit"], money_format)
            worksheet.write_number(row, 3, summary["credit"], money_format)
            worksheet.write_number(row, 4, summary["balance"], money_format)
            row += 1

        worksheet.set_column("A:A", 18)
        worksheet.set_column("B:B", 12)
        worksheet.set_column("C:C", 30)
        worksheet.set_column("D:D", 15)
        worksheet.set_column("E:E", 15)
        worksheet.set_column("F:G", 15)
