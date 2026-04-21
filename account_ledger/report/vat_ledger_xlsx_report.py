from dataclasses import fields

from odoo import models, fields, api
import io
import base64
import xlsxwriter
from odoo import models, api
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT


class VatLedgerXlsxReport(models.AbstractModel):
    _name = 'report.account_ledger.vat_ledger_xlsx_report'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, wizard_id):
        report_data = {
            'date_start': wizard_id.date_start,
            'date_end': wizard_id.date_end,
            'account': wizard_id.account_ids.ids,
            'company': wizard_id.company_id.id,
            'vat_option': wizard_id.vat_option,
            'department': wizard_id.department_id.id if wizard_id.department_id else False,
            'section': wizard_id.section_id.id if wizard_id.section_id else False,
            'project': wizard_id.project_id.id if wizard_id.project_id else False,
            'employee': wizard_id.employee_id.id if wizard_id.employee_id else False,
            'asset': wizard_id.asset_id.id if wizard_id.asset_id else False,
        }

        data_in_dictionary = self._get_report_values(report_data, wizard_id)
        docs = data_in_dictionary.get("docs", [])

        worksheet = workbook.add_worksheet("VAT Report")

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
            'Transaction Ref', 'Reference', 'Date', 'Description', 'Amount', 'TAX Amount', 'Total Amount'
        ]
        worksheet.write_row('A4', headers, header_format)

        # === Data Rows ===
        row = 4  # Data starts from Excel row 6
        for entry in docs:
            worksheet.write(row, 0, entry['transaction_ref'],
                            text_format if entry["description"] != "Totals" else header_format)
            worksheet.write(row, 1, entry['reference'],
                            text_format if entry["description"] != "Totals" else header_format)
            worksheet.write(row, 2, entry['date'], date_format if entry["description"] != "Totals" else header_format)
            worksheet.write(row, 3, entry['description'],
                            text_format if entry["description"] != "Totals" else header_format)
            worksheet.write_number(row, 4, float(
                entry['amount'].replace(',', '') if not entry.get('tot_amount') else entry['tot_amount'].replace(',',
                                                                                                                 '')),
                                   money_format if entry["description"] != "Totals" else header_format)
            worksheet.write_number(row, 5, float(
                entry['tax_amount'].replace(',', '') if not entry.get('tot_tax_amount') else entry[
                    'tot_tax_amount'].replace(',', '')),
                                   money_format if entry["description"] != "Totals" else header_format)
            worksheet.write_number(row, 6, float(
                entry['total_amount'].replace(',', '') if not entry.get('tot_total_amount') else entry[
                    'tot_total_amount'].replace(',', '')),
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
        account_name = f"Statement of Vat Report: {wizard_id.account_id.name}" if wizard_id.account_id else "Statement of Vat Report"
        account = report_data['account']
        date_start = report_data['date_start']
        date_end = report_data['date_end']
        company = report_data['company']
        vat_option = report_data['vat_option']
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
        if account:
            ji_domain.append(('account_id', 'in', account))
        else:
            return {
                'account': " ",
                'report_date': report_date,
                'docs': []
            }

        # if analytic_ids:
        #     ji_domain.append(('analytic_distribution', 'in', analytic_ids))

        if department:
            ji_domain.append(('analytic_distribution', 'in', [int(department)]))

        JournalItems = self.env['account.move.line'].search(ji_domain, order="date asc")
        JournalAccounts = JournalItems.mapped("account_id.id")
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

        tuple_account = tuple(account)
        if len(JournalAccounts) == 1:
            where_statement = f"""
                        account_move_line.account_id = {JournalAccounts[0]} 
                        AND 
                        account_move_line.date < '{date_start}'"""
        elif len(JournalAccounts) > 1:
            where_statement = f"""
                        account_move_line.account_id in {TupleJournalAccounts} 
                        AND 
                        account_move_line.date < '{date_start}'"""
        else:
            where_statement = f""""""
        if analytic_ids:
            if where_statement:
                where_statement += f""" AND 
                        analytic_distribution ?& array{str_analytic_ids}"""
            else:
                where_statement += f""" 
                                        analytic_distribution ?& array{str_analytic_ids}"""

        sql = f"""
                            SELECT 
                                SUM(balance)
                            FROM
                                account_move_line
                            WHERE
                            {where_statement}    
                            GROUP By account_move_line.account_id
                        """
        self.env.cr.execute(sql)
        result = self.env.cr.fetchone()
        if result and result[0]:
            initial_balance = result[0]
        else:
            initial_balance = 0
        t_debit = 0
        t_credit = 0
        init_balance = initial_balance
        amount = 0
        tax_amount = 0
        total_amount = 0
        tot_amount = 0
        tot_tax_amount = 0
        tot_total_amount = 0
        if vat_option == "including_vat":
            FilteredJournalItems = JournalItems.filtered(lambda l: l.tax_ids)
        elif vat_option == "excluding_vat":
            FilteredJournalItems = JournalItems.filtered(
                lambda l: (
                        not l.tax_ids
                        and not l.tax_line_id
                        and not l.tax_tag_ids
                        and l.account_id.account_type in ("expense", "cost_of_revenue")  # <-- FIX 2
                )
            )
        else:
            FilteredJournalItems = JournalItems

        # for item in JournalItems:
        for item in FilteredJournalItems:
            if item.tax_ids:
                tax_amount_dict = self._get_tax_amount(item)
                tax_amount = round(tax_amount_dict.get("amount_tax"), 2)
            else:
                tax_amount = 0

            amount = item.amount_currency
            total_amount = amount + tax_amount

            tot_amount += amount
            tot_tax_amount += tax_amount
            tot_total_amount += total_amount

            balance = initial_balance + (item.debit - item.credit)
            t_debit += item.debit
            t_credit += item.credit
            docs.append({
                'transaction_ref': item.move_id.name,
                'date': item.date,
                'description': item.name,
                'reference': item.ref,
                'journal': item.journal_id.name,
                'initial_balance': '{:,.2f}'.format(initial_balance),
                'debit': '{:,.2f}'.format(item.debit),
                'credit': '{:,.2f}'.format(item.credit),
                'balance': '{:,.2f}'.format(item.balance),
                'amount': '{:,.2f}'.format(amount),
                'tax_amount': '{:,.2f}'.format(tax_amount),
                'total_amount': '{:,.2f}'.format(total_amount)
            })
            initial_balance = balance
        docs.append({
            'transaction_ref': '',
            'date': ' ',
            'description': 'Total',
            'reference': ' ',
            'journal': ' ',
            'initial_balance': '{:,.2f}'.format(init_balance),
            'debit': '{:,.2f}'.format(t_debit),
            'credit': '{:,.2f}'.format(t_credit),
            'balance': '{:,.2f}'.format(init_balance + t_debit - t_credit),
            'tot_amount': '{:,.2f}'.format(tot_amount),
            'tot_tax_amount': '{:,.2f}'.format(tot_tax_amount),
            'tot_total_amount': '{:,.2f}'.format(tot_total_amount)
        })
        return {
            'account': account_name,
            'report_date': report_date,
            'docs': docs
        }

    def _get_tax_amount(self, JILine):
        """
        Compute the amounts of the SO line.
        """
        # self.ensure_one()
        tax_results = self.env['account.tax']._compute_taxes([
            self._convert_to_tax_base_line_dict(JILine)
        ])
        totals = list(tax_results['totals'].values())[0]
        amount_untaxed = totals['amount_untaxed']
        amount_tax = totals['amount_tax']
        return {"amount_untaxed": amount_untaxed, "amount_tax": amount_tax}

    def _convert_to_tax_base_line_dict(self, JILine):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        # self.ensure_one()
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            partner=False,
            currency=JILine.currency_id,
            product=False,
            taxes=JILine.tax_ids,
            price_unit=JILine.amount_currency,
            quantity=1,
            discount=0,
            price_subtotal=JILine.amount_currency,
        )
