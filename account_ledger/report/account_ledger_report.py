# -*- coding: utf-8 -*-

from datetime import datetime

from odoo import api, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
import logging

from .ledger_partner_utils import as_date, get_ledger_move_lines, get_opening_balance

_logger = logging.getLogger(__name__)


class AccountLedgerReport(models.AbstractModel):
    _name = 'report.account_ledger.account_ledger_rep'

    def _get_valuation_dates(self, start_date, end_date):
        date_start = as_date(start_date)
        date_end = as_date(end_date)
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
        if not account:
            return {
                'doc_ids': data['ids'],
                'doc_model': data['model'],
                'valuation_date': self._get_valuation_dates(data['form']['date_start'], data['form']['date_end']),
                'account': " ",
                'report_date': report_date,
                'docs': []
            }

        selected_analytic_ids = []
        if department:
            selected_analytic_ids.append(int(department))
        if section:
            selected_analytic_ids.append(int(section))
        if project:
            selected_analytic_ids.append(int(project))
        if employee:
            selected_analytic_ids.append(int(employee))
        if asset:
            selected_analytic_ids.append(int(asset))

        JournalItems = get_ledger_move_lines(
            self.env,
            company,
            account,
            date_start,
            date_end,
            analytic_ids=selected_analytic_ids,
        )
        initial_balance = get_opening_balance(
            self.env,
            company,
            account,
            date_start,
            analytic_ids=selected_analytic_ids,
        )
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
