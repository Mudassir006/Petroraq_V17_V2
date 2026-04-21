# -*- coding: utf-8 -*-
#################################################################################
#
#Copyright (c) 2013-Present IctPack Solutions LTD. (<http://ictpack.com>)
#
#################################################################################

import pytz
import xlwt
import io
import base64
from . import xls_format

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountBalanceReport(models.TransientModel):
    _inherit = 'account.balance.report'

    def _get_accounts(self, accounts, display_account):
        """ compute the balance, debit and credit for the provided accounts
            :Arguments:
                `accounts`: list of accounts record,
                `display_account`: it's used to display either all accounts or those accounts which balance is > 0
            :Returns a list of dictionary of Accounts with following key and value
                `name`: Account name,
                `code`: Account code,
                `credit`: total amount of credit,
                `debit`: total amount of debit,
                `balance`: total amount of balance,
        """

        account_result = {}
        # Prepare sql query base on selected parameters from wizard
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        tables = tables.replace('"','')
        if not tables:
            tables = 'account_move_line'
        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())
        filters = " AND ".join(wheres)


        # compute the balance, debit and credit for the provided accounts
        request = ("SELECT account_id AS id, analytic_distribution AS analytic_distribution, SUM(debit) AS debit, SUM(credit) AS credit, (SUM(debit) - SUM(credit)) AS balance" +\
                   " FROM " + tables + " WHERE account_id IN %s " + filters + " GROUP BY account_id, analytic_distribution")
        params = (tuple(accounts.ids),) + tuple(where_params)
        self.env.cr.execute(request, params)
        results = self.env.cr.dictfetchall()
        results = self._filter_analytic_data(results)
        # for row in self.env.cr.dictfetchall():
        for row in results:
            account_result[row.pop('id')] = row

        account_res = []
        for account in accounts:
            res = dict((fn, 0.0) for fn in ['credit', 'debit', 'balance'])
            currency = account.currency_id and account.currency_id or account.company_id.currency_id
            res['code'] = account.code
            res['name'] = account.name
            if account.id in account_result:
                res['debit'] = account_result[account.id].get('debit')
                res['credit'] = account_result[account.id].get('credit')
                res['balance'] = account_result[account.id].get('balance')
            if display_account == 'all':
                account_res.append(res)
            if display_account == 'not_zero' and not currency.is_zero(res['balance']):
                account_res.append(res)
            if display_account == 'movement' and (not currency.is_zero(res['debit']) or not currency.is_zero(res['credit'])):
                account_res.append(res)
        return account_res

    def _print_report_excel(self,data):
        self.ensure_one()
        #row_data = self.check_report()
        #data = row_data.get('data', {})
        data = self.pre_print_report(data)
        display_account = data['form']['display_account']

        #default company currency
        currency = self.env.ref('base.main_company').currency_id

        # if not data['form'].get('date_from'):
        #     raise UserError(_("You must define a Start Date"))
        #self.model = self._inherit

        accounts = self.env['account.account'].search([])
        accounts_res = self.with_context(
            data['form'].get('used_context', {}))._get_accounts(
                accounts, display_account)

        company = self.env.user.company_id
        workbook = xlwt.Workbook()
        style_string = "font: bold on; ; font: name Times New Roman, font: color purple_ega;"
        blue_style = xlwt.easyxf(style_string)
 
        M_header_tstyle = xls_format.font_style(position='center',
                                                bold=1,
                                                border=1,
                                                fontos='black',
                                                font_height=400,
                                                color='grey'
                                                )
        header_tstyle = xls_format.font_style(position='left',
                                              bold=1,
                                              border=1,
                                              fontos='black',
                                              font_height=180,
                                              color='yellow'
                                              )
        header_tstyle_c = xls_format.font_style(position='center',
                                                bold=1,
                                                border=1,
                                                fontos='black',
                                                font_height=180,
                                                color='grey')
        header_tstyle_r = xls_format.font_style(position='right',
                                                bold=1,
                                                border=1,
                                                fontos='black',
                                                font_height=180,
                                                color='yellow')
        view_tstyle = xls_format.font_style(position='left',
                                            bold=1,
                                            fontos='black',
                                            font_height=180)
        view_tstyle_r = xls_format.font_style(position='right',
                                              bold=1,
                                              fontos='black',
                                              font_height=180)
        other_tstyle = xls_format.font_style(position='left',
                                             fontos='black',
                                             font_height=180)
        other_tstyle_c = xls_format.font_style(position='center',
                                               fontos='black',
                                               border=1,
                                               font_height=180,
                                               )
        other_tstyle_b = xls_format.font_style(position='center',
                                                bold=1,
                                                border=1,
                                                fontos='black',
                                                font_height=180,
                                                )
        other_tstyle_r = xls_format.font_style(position='right',
                                               fontos='purple_ega',
                                               bold=1,
                                               border=1,
                                               font_height=180,
                                               color='grey')
        other_tstyle_rb = xls_format.font_style(position='right',
                                               fontos='black',
                                               bold=1,
                                               border=1,
                                               font_height=200,
                                               color='grey')
        
        tilte = "%s : %s" % (company.name, " Trial Balance")
        sheet = workbook.add_sheet(tilte)
        sheet.set_panes_frozen(True)
        sheet.set_horz_split_pos(1)
        sheet.row(0).height = 256 * 3
        
        row_start, col_start = 0, 0
        sheet.write_merge(row_start, row_start, col_start, col_start + 4, tilte, M_header_tstyle)
        row_start += 2
        col_start = 0
        sheet.write(row_start, col_start, _('Display Account'), other_tstyle_b)
        if data['form'].get('date_from'):
            col_start += 1
            sheet.write(row_start, col_start, _('Date from'), other_tstyle_b)
            col_start += 1
            sheet.write(row_start, col_start, str(data['form'].get('date_from')),other_tstyle_c)
        col_start += 1
        sheet.write_merge(row_start, row_start, col_start, col_start  + 1, _('Target Moves:'), other_tstyle_b)
        row_start += 1
        col_start = 0
        if display_account == 'all':
            sheet.write(row_start, col_start, _('All accounts'),other_tstyle_c)
        if display_account == 'movement':
            sheet.write(row_start, col_start, _('With movements'),other_tstyle_c)
        if display_account == 'not_zero':
            sheet.write(row_start, col_start, _('With balance not equal to zero'),other_tstyle_c)

        if data['form'].get('date_to'):
            col_start += 1
            sheet.write(row_start, col_start, _('Date to'), other_tstyle_b)
            col_start += 1
            sheet.write(row_start, col_start, str(data['form'].get('date_to')),other_tstyle_c)
        col_start += 1
        if data['form']['target_move'] == 'all':
            sheet.write_merge(row_start, row_start, col_start, col_start + 1, _('All Entries'),other_tstyle_c)
        if data['form']['target_move'] == 'posted':
            sheet.write_merge(row_start, row_start, col_start, col_start + 1, _('All Posted Entries'),other_tstyle_c)

        col_start = 0
        row_start += 2
        sheet.col(col_start).width = 256 * 20
        sheet.write(row_start, col_start, _('Code'), header_tstyle_c)
        col_start += 1
        sheet.col(col_start).width = 256 * 50
        sheet.write(row_start, col_start, _('Account'), header_tstyle_c)
        col_start += 1
        sheet.col(col_start).width = 256 * 30
        sheet.write(row_start, col_start, _('Debit'), header_tstyle_c)
        col_start += 1
        sheet.col(col_start).width = 256 * 30
        sheet.write(row_start, col_start, _('Credit'), header_tstyle_c)
        col_start += 1
        sheet.col(col_start).width = 256 * 30
        sheet.write(row_start, col_start, _('Balance'), header_tstyle_c)

        for acc in accounts_res:
            col_start = 0
            row_start += 1
            sheet.write(row_start, col_start, acc.get('code'),other_tstyle)
            col_start += 1
            sheet.write(row_start, col_start, acc.get('name'),other_tstyle)
            col_start += 1
            sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(acc.get('debit')),other_tstyle_r)
            col_start += 1
            sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(acc.get('credit')),other_tstyle_r)
            col_start += 1
            sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(acc.get('balance')),other_tstyle_r)
            col_start += 1
            
        stream = io.BytesIO()
        workbook.save(stream)

        export_obj = self.env['single.click.download.xls']
        self._cr.execute(""" DELETE FROM single_click_download_xls""")
        res_id = export_obj.create({
                                'file': base64.encodebytes(stream.getvalue()),
                                'fname': tilte+".xls"
                                })
        return {
             'type': 'ir.actions.act_url',
             'url': '/web/binary/download_document?model=single.click.download.xls&field=file&id=%s&filename=%s.xls'%(res_id.id,tilte),
             'target': 'new',
             }
