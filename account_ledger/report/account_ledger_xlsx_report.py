from dataclasses import fields

from odoo import models, fields, api
import io
import base64
import xlsxwriter
from odoo import models, api
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT


class CustomDynamicLedgerReport(models.AbstractModel):
    _name = 'report.account_ledger.account_ledger_xlsx_report'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, wizard_id):
        report_data = {
            'date_start': wizard_id.date_start,
            'date_end': wizard_id.date_end,
            'account': wizard_id.account_ids.ids,
            'company': wizard_id.company_id.id,
            'department': wizard_id.department_id.id if wizard_id.department_id else False,
            'section': wizard_id.section_id.id if wizard_id.section_id else False,
            'project': wizard_id.project_id.id if wizard_id.project_id else False,
            'employee': wizard_id.employee_id.id if wizard_id.employee_id else False,
            'asset': wizard_id.asset_id.id if wizard_id.asset_id else False,
        }

        data_in_dictionary = self._get_report_values(report_data, wizard_id)
        docs = data_in_dictionary.get("docs", [])

        worksheet = workbook.add_worksheet("Account Ledger")

        # === Formats ===
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'bg_color': '#173b76',
            'color': '#ffffff',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })

        subtitle_format = workbook.add_format({
            'bold': True,
            'font_size': 12,
            'align': 'left',
            'valign': 'vcenter'
        })

        info_format = workbook.add_format({
            'font_size': 11,
            'italic': True,
            'align': 'left',
            'valign': 'vcenter'
        })

        header_format = workbook.add_format({
            'bold': True,
            # 'bg_color': '#D9E1F2',
            'bg_color': '#173b76',
            'color': '#ffffff',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })

        money_format = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
        text_format = workbook.add_format({'border': 1})
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd', 'border': 1})

        # === First 4 Rows (Title, Info, etc.) ===
        worksheet.merge_range('A1:G1', 'Petroraq Engineering & Construction - VAT Number 311428741500003', title_format)
        worksheet.merge_range('A2:G2', f'{data_in_dictionary["account"]}', title_format)
        worksheet.merge_range('A3:G3',
                              f'Period: {wizard_id.date_start.strftime("%d-%b-%Y")} to {wizard_id.date_end.strftime("%d-%b-%Y")}',
                              title_format)
        # worksheet.merge_range('A4:I4', '', info_format)  # Optional empty/info row

        # === Column Headers ===
        headers = [
            'Transaction Ref', 'Date', 'Reference', 'Description', 'Debit', 'Credit', 'Balance'
        ]
        worksheet.write_row('A4', headers, header_format)

        # === Data Rows ===
        row = 4  # Data starts from Excel row 6
        for entry in docs:
            worksheet.write(row, 0, entry['transaction_ref'],
                            text_format if entry["description"] != "Totals" else header_format)
            worksheet.write(row, 1, entry['date'], date_format if entry["description"] != "Totals" else header_format)
            worksheet.write(row, 2, entry['reference'],
                            text_format if entry["description"] != "Totals" else header_format)
            worksheet.write(row, 3, entry['description'],
                            text_format if entry["description"] != "Totals" else header_format)
            worksheet.write_number(row, 4, float(entry['debit'].replace(',', '')),
                                   money_format if entry["description"] != "Totals" else header_format)
            worksheet.write_number(row, 5, float(entry['credit'].replace(',', '')),
                                   money_format if entry["description"] != "Totals" else header_format)
            worksheet.write_number(row, 6, float(entry['balance'].replace(',', '')),
                                   money_format if entry["description"] != "Totals" else header_format)
            row += 1

        # Column widths
        worksheet.set_column('A:A', 18)
        worksheet.set_column('B:B', 12)
        worksheet.set_column('C:C', 30)
        worksheet.set_column('D:D', 15)
        worksheet.set_column('E:E', 15)
        worksheet.set_column('F:I', 15)

    def _get_report_values(self, report_data, wizard_id):
        docs = []
        account_name = f"Statement of Account Ledger: {wizard_id.account_id.name}" if wizard_id.account_id else "Statement of Account Ledger"
        main_head_in_report = wizard_id.main_head
        if main_head_in_report:
            main_head_in_report = str(main_head_in_report).capitalize()
            account_name += f"\nType: {main_head_in_report}"
        account = report_data['account']
        date_start = report_data['date_start']
        date_end = report_data['date_end']
        company = report_data['company']
        analytic_ids = []
        str_analytic_ids = []
        # -- Analytic Fields -- #
        department = False
        section = False
        project = False
        employee = False
        asset = False

        if report_data.get("department"):
            department = report_data['department']

        if report_data.get("section"):
            section = report_data['section']

        if report_data.get("project"):
            project = report_data['project']

        if report_data.get("employee"):
            employee = report_data['employee']

        if report_data.get("asset"):
            asset = report_data['asset']

        if department:
            analytic_ids.append(int(department))
            str_analytic_ids.append(str(department))
            department_id_obj = self.env["account.analytic.account"].sudo().browse(int(department))
            account_name += f"\nDepartment: {department_id_obj.name}"

        if section:
            analytic_ids.append(int(section))
            str_analytic_ids.append(str(section))
            section_id_obj = self.env["account.analytic.account"].sudo().browse(int(section))
            account_name += f"\nSection: {section_id_obj.name}"

        if project:
            analytic_ids.append(int(project))
            str_analytic_ids.append(str(project))
            project_id_obj = self.env["account.analytic.account"].sudo().browse(int(project))
            account_name += f"\nProject: {project_id_obj.name}"

        if employee:
            analytic_ids.append(int(employee))
            str_analytic_ids.append(str(employee))
            employee_id_obj = self.env["account.analytic.account"].sudo().browse(int(employee))
            account_name += f"\nEmployee: {employee_id_obj.name}"

        if asset:
            analytic_ids.append(int(asset))
            str_analytic_ids.append(str(asset))
            asset_id_obj = self.env["account.analytic.account"].sudo().browse(int(asset))
            account_name += f"\nAsset: {asset_id_obj.name}"

        today = datetime.today()
        report_date = today.strftime("%b-%d-%Y")
        ji_domain = [
            ('company_id', '=', company),
            ('date', '>=', datetime.strptime(str(date_start), DATE_FORMAT).date()),
            ('date', '<=', datetime.strptime(str(date_end), DATE_FORMAT).date()),
            ('move_id.state', '=', 'posted'),
        ]

        opening_balance_domain = [
            ('company_id', '=', company),
            ('date', '>=', datetime.strptime(str(date_start), DATE_FORMAT).date()),
            ('date', '<=', datetime.strptime(str(date_end), DATE_FORMAT).date()),
            ('move_id.state', '=', 'posted'),
        ]

        if account:
            ji_domain.append(('account_id', 'in', account))
            opening_balance_domain.append(('account_id', 'in', account))
        else:
            return {
                'account': " ",
                'report_date': report_date,
                'docs': []
            }

        if analytic_ids:
            opening_balance_domain.append(('analytic_distribution', 'in', analytic_ids))
        if department:
            ji_domain.append(('analytic_distribution', 'in', [int(department)]))

        opening_balance_ids = self.env['account.move.line'].search(opening_balance_domain, order="date asc")
        JournalItems = self.env['account.move.line'].search(ji_domain, order="date asc")
        JournalAccounts = account
        TupleJournalAccounts = tuple(JournalAccounts)

        if JournalItems and section:
            JournalItems = self.env['account.move.line'].search(
                [("id", "in", JournalItems.ids), ("analytic_distribution", "in", [int(section)])], order="date asc")
        if JournalItems and project:
            JournalItems = self.env['account.move.line'].search(
                [("id", "in", JournalItems.ids), ("analytic_distribution", "in", [int(project)])], order="date asc")
        if JournalItems and employee:
            JournalItems = self.env['account.move.line'].search(
                [("id", "in", JournalItems.ids), ("analytic_distribution", "in", [int(employee)])], order="date asc")
        if JournalItems and asset:
            JournalItems = self.env['account.move.line'].search(
                [("id", "in", JournalItems.ids), ("analytic_distribution", "in", [int(asset)])], order="date asc")

        if len(JournalAccounts) == 1:
            where_statement = f"""
                WHERE aml.account_id = {JournalAccounts[0]} 
                AND 
                aml.date < '{date_start}'
                AND am.state = 'posted'"""
        elif len(JournalAccounts) > 1:
            where_statement = f"""
                WHERE aml.account_id in {TupleJournalAccounts} 
                AND 
                aml.date < '{date_start}'
                AND am.state = 'posted'"""
        else:
            where_statement = ""

        if analytic_ids:
            if where_statement:
                if "WHERE" in where_statement:
                    where_statement += f""" AND 
                    analytic_distribution ?& array{str_analytic_ids}"""
                else:
                    where_statement += f""" WHERE 
                                        analytic_distribution ?& array{str_analytic_ids}"""
            else:
                where_statement += f""" 
                                WHERE analytic_distribution ?& array{str_analytic_ids}"""

        # if not where_statement:
        #     return {
        #         'account': " ",
        #         'report_date': report_date,
        #         'docs': []
        #     }
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
        if result:
            initial_balance = result[0]
        else:
            initial_balance = 0

        if initial_balance >= 0:
            initial_debit = initial_balance
            initial_credit = 0
        else:
            initial_debit = 0
            initial_credit = abs(initial_balance)

        t_debit = 0 + initial_debit
        t_credit = 0 + initial_credit
        init_balance = initial_balance
        docs.append({
            'transaction_ref': ' ',
            'date': f'{str(date_start)}',
            'initial_balance': '{:,.2f}'.format(init_balance),
            'description': 'Opening Balance',
            'reference': ' ',
            'journal': ' ',
            'debit': '{:,.2f}'.format(initial_debit),
            'credit': '{:,.2f}'.format(initial_credit),
            'balance': '{:,.2f}'.format(init_balance)
        })
        for item in JournalItems:
            balance = initial_balance + (item.debit - item.credit)
            t_debit += item.debit
            t_credit += item.credit
            docs.append({
                'transaction_ref': item.move_id.name,
                'date': item.date,
                'initial_balance': '{:,.2f}'.format(initial_balance),
                'description': item.name,
                'reference': item.ref,
                'journal': item.journal_id.name,
                'debit': '{:,.2f}'.format(item.debit),
                'credit': '{:,.2f}'.format(item.credit),
                'balance': '{:,.2f}'.format(balance)
            })
            initial_balance = balance
        docs.append({
            'transaction_ref': ' ',
            'date': f'{str(datetime.now().date())}',
            'initial_balance': ' ',
            'description': 'Totals',
            'reference': ' ',
            'journal': ' ',
            'debit': '{:,.2f}'.format(t_debit),
            'credit': '{:,.2f}'.format(t_credit),
            'balance': '{:,.2f}'.format(t_debit - t_credit)
        })
        return {
            'account': account_name,
            'report_date': report_date,
            'docs': docs
        }
