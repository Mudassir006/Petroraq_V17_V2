# -*- coding: utf-8 -*-

from datetime import datetime

from odoo import api, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
import logging

_logger = logging.getLogger(__name__)


class AccountLedgerReport(models.AbstractModel):
    _name = 'report.account_ledger.vat_ledger_rep'

    def _get_valuation_dates(self, start_date, end_date):
        date_start = datetime.strptime(start_date, DATE_FORMAT).date()
        date_end = datetime.strptime(end_date, DATE_FORMAT).date()
        valuation_date = str(date_start) + ' To ' + str(date_end)
        return valuation_date

    @api.model
    def _get_report_values(self, docids, data=None):
        # self.ensure_one()
        docs = []
        account = data['form']['account']
        date_start = data['form']['date_start']
        date_end = data['form']['date_end']
        company = data['form']['company']
        vat_option = data['form']['vat_option']
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
            ('move_id.state', '=', 'posted'),  # <-- FIX 1
        ]

        if account:
            ji_domain.append(('account_id', 'in', account))
        else:
            return {
                'doc_ids': data['ids'],
                'doc_model': data['model'],
                'valuation_date': self._get_valuation_dates(data['form']['date_start'], data['form']['date_end']),
                'account': " ",
                'report_date': report_date,
                'docs': []
            }

        if analytic_ids:
            ji_domain.append(('analytic_distribution', 'in', analytic_ids))

        JournalItems = self.env['account.move.line'].search(ji_domain, order="date asc")
        JournalAccounts = JournalItems.mapped("account_id.id")
        TupleJournalAccounts = tuple(JournalAccounts)

        # account_move_line.account_id = {account}
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
            where_statement = "1 = 1"
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
            'transaction_ref': False,
            'date': ' ',
            'description': ' ',
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
        account_names = ", ".join(self.env['account.account'].browse(account).mapped('name'))

        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'valuation_date': self._get_valuation_dates(data['form']['date_start'], data['form']['date_end']),
            'account': account_names or "All",
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
