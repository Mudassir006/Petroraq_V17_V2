# -*- coding: utf-8 -*-

from datetime import datetime

from odoo import api, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
import logging

_logger = logging.getLogger(__name__)


class AccountLedgerReport(models.AbstractModel):
    _name = 'report.account_ledger.account_ledger_rep'

    def _get_valuation_dates(self, start_date, end_date):
        date_start = datetime.strptime(start_date, DATE_FORMAT).date()
        date_end = datetime.strptime(end_date, DATE_FORMAT).date()
        valuation_date = str(date_start) + ' To ' + str(date_end)
        return valuation_date

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = []
        account = data['form']['account']
        date_start = data['form']['date_start']
        date_end = data['form']['date_end']
        company = data['form']['company']
        analytic_ids = []
        str_analytic_ids = []
        # -- Analytic Fields -- #
        department = False
        section = False
        project = False
        employee = False
        asset = False

        if data['form'].get("department"):
            department = data['form']['department']

        if data['form'].get("section"):
            section = data['form']['section']

        if data['form'].get("project"):
            project = data['form']['project']

        if data['form'].get("employee"):
            employee = data['form']['employee']

        if data['form'].get("asset"):
            asset = data['form']['asset']

        if department:
            analytic_ids.append(int(department))
            str_analytic_ids.append(str(department))

        if section:
            analytic_ids.append(int(section))
            str_analytic_ids.append(str(section))

        if project:
            analytic_ids.append(int(project))
            str_analytic_ids.append(str(project))

        if employee:
            analytic_ids.append(int(employee))
            str_analytic_ids.append(str(employee))

        if asset:
            analytic_ids.append(int(asset))
            str_analytic_ids.append(str(asset))

        today = datetime.today()
        report_date = today.strftime("%b-%d-%Y")
        # user_type_receivable_id = self.env['ir.model.data'].xmlid_to_res_id('account.data_account_type_receivable')
        ji_domain = [
            ('company_id', '=', company),
            ('date', '>=', datetime.strptime(date_start, DATE_FORMAT).date()),
            ('date', '<=', datetime.strptime(date_end, DATE_FORMAT).date()),
            ('move_id.state', '=', 'posted'),
        ]

        opening_balance_domain = [
            ('company_id', '=', company),
            ('date', '>=', datetime.strptime(date_start, DATE_FORMAT).date()),
            ('date', '<=', datetime.strptime(date_end, DATE_FORMAT).date()),
            ('move_id.state', '=', 'posted'),
        ]

        if account:
            ji_domain.append(('account_id', 'in', account))
            opening_balance_domain.append(('account_id', 'in', account))
        else:
            return {
                'doc_ids': data['ids'],
                'doc_model': data['model'],
                'valuation_date': self._get_valuation_dates(data['form']['date_start'], data['form']['date_end']),
                # 'account':self.env['account.account'].search([('id', '=', account)]).name,
                'account': " ",
                'report_date': report_date,
                'docs': []
            }
        # if asset:
        #     ji_domain.append(('asset_id','=', asset))

        if analytic_ids:
            opening_balance_domain.append(('analytic_distribution', 'in', analytic_ids))
        if department:
            ji_domain.append(('analytic_distribution', 'in', [int(department)]))

        opening_balance_ids = self.env['account.move.line'].search(opening_balance_domain, order="date asc")
        JournalItems = self.env['account.move.line'].search(ji_domain, order="date asc")
        # JournalAccounts = JournalItems.mapped("account_id.id")
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

        # account_move_line.account_id = {account}
        tuple_account = tuple(account)
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

        # where_statement = f"""
        # account_move_line.account_id in {TupleJournalAccounts}
        # AND
        # account_move_line.date < '{date_start}'"""

        # if asset:
        #     if where_statement:
        #         where_statement += f""" AND
        #         account_move_line.asset_id = {asset}"""
        #     else:
        #         where_statement += f"""
        #                         account_move_line.asset_id = {asset}"""

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
        #         'doc_ids': data['ids'],
        #         'doc_model': data['model'],
        #         'valuation_date': self._get_valuation_dates(data['form']['date_start'], data['form']['date_end']),
        #         # 'account':self.env['account.account'].search([('id', '=', account)]).name,
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
        # raise ValueError(sql)
        self.env.cr.execute(sql)
        result = self.env.cr.fetchone()
        if result and result[0]:
            initial_balance = result[0]
        else:
            initial_balance = 0
        t_debit = 0
        t_credit = 0
        init_balance = initial_balance
        opening_debit = initial_balance if initial_balance > 0 else 0
        opening_credit = abs(initial_balance) if initial_balance < 0 else 0

        docs.append({
            'transaction_ref': 'Opening',
            'date': date_start,
            'description': 'Opening Balance',
            'reference': ' ',
            'journal': ' ',
            'initial_balance': '{:,.2f}'.format(initial_balance),
            'debit': '{:,.2f}'.format(opening_debit),
            'credit': '{:,.2f}'.format(opening_credit),
            'balance': '{:,.2f}'.format(initial_balance)
        })

        for item in JournalItems:
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
                'balance': '{:,.2f}'.format(balance)
            })
            initial_balance = balance
        docs.append({
            'transaction_ref': False,
            'date': ' ',
            'description': ' ',
            'reference': ' ',
            'journal': ' ',
            'initial_balance': '{:,.2f}'.format(init_balance),
            'debit': '{:,.2f}'.format(t_debit),
            'credit': '{:,.2f}'.format(t_credit),
            'balance': '{:,.2f}'.format(init_balance + t_debit - t_credit)
        })
        account_ids = data['form']['account']
        account_names = ", ".join(self.env['account.account'].browse(account_ids).mapped('name'))
        company_name = self.env['res.company'].browse(company).name

        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'valuation_date': self._get_valuation_dates(data['form']['date_start'], data['form']['date_end']),
            # 'account':self.env['account.account'].search([('id', '=', account)]).name,
            'account': f"{company_name} - {account_names}" if account_names else company_name,
            'report_date': report_date,
            'docs': docs
        }
