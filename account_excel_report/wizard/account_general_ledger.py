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


class AccountGeneralLedgerReport(models.TransientModel):
    _inherit = 'account.report.general.ledger'

    def _get_account_move_entry(self, accounts, init_balance, sortby, display_account):
        """
        :param:
                accounts: the recordset of accounts
                init_balance: boolean value of initial_balance
                sortby: sorting by date or partner and journal
                display_account: type of account(receivable, payable and both)

        Returns a dictionary of accounts with following key and value {
                'code': account code,
                'name': account name,
                'debit': sum of total debit amount,
                'credit': sum of total credit amount,
                'balance': total balance,
                'amount_currency': sum of amount_currency,
                'move_lines': list of move line
        }
        """
        cr = self.env.cr
        MoveLine = self.env['account.move.line']
        move_lines = {x: [] for x in accounts.ids}

        # Prepare initial sql query and Get the initial move lines
        if init_balance:
            init_tables, init_where_clause, init_where_params = MoveLine.with_context(date_from=self.env.context.get('date_from'), date_to=False, initial_bal=True)._query_get()
            init_wheres = [""]
            if init_where_clause.strip():
                init_wheres.append(init_where_clause.strip())
            init_filters = " AND ".join(init_wheres)
            filters = init_filters.replace('account_move_line__move_id', 'm').replace('account_move_line', 'l')
            filters = filters.replace(f"\"analytic_distribution\" IN", f"\"analytic_distribution\" ?&")
            filters = self.remove_all_redundant_parentheses(filters)
            sql = ("""SELECT 0 AS lid, l.account_id AS account_id, '' AS ldate, '' AS lcode, 0.0 AS amount_currency, '' AS lref, 'Initial Balance' AS lname, l.analytic_distribution as analytic_distribution, COALESCE(SUM(l.debit),0.0) AS debit, COALESCE(SUM(l.credit),0.0) AS credit, COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) as balance, '' AS lpartner_id,\
                '' AS move_name, '' AS mmove_id, '' AS currency_code,\
                NULL AS currency_id,\
                '' AS invoice_id, '' AS invoice_type, '' AS invoice_number,\
                '' AS partner_name\
                FROM account_move_line l\
                LEFT JOIN account_move m ON (l.move_id=m.id)\
                LEFT JOIN res_currency c ON (l.currency_id=c.id)\
                LEFT JOIN res_partner p ON (l.partner_id=p.id)\
                JOIN account_journal j ON (l.journal_id=j.id)\
                WHERE l.account_id IN %s""" + filters + ' GROUP BY l.account_id')
            params = (tuple(accounts.ids),) + tuple(init_where_params)
            final_query = self.build_sql(sql, params)
            final_query = final_query.replace("WHERE", "WHERE ")
            final_query = final_query.replace("GROUP", " GROUP")
            # final_query = final_query.replace("analytic_distribution", " analytic_distribution::jsonb")
            cr.execute(final_query)
            data_rows = cr.dictfetchall()
            data_rows = self._filter_analytic_data(data_rows)
            for row in data_rows:
                move_lines[row.pop('account_id')].append(row)

        sql_sort = 'l.date, l.move_id'
        if sortby == 'sort_journal_partner':
            sql_sort = 'l.move_id'

        # Prepare sql query base on selected parameters from wizard
        tables, where_clause, where_params = MoveLine._query_get()
        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())
        filters = " AND ".join(wheres)
        filters = filters.replace('account_move_line__move_id', 'm').replace('account_move_line', 'l')
        filters = filters.replace(f"\"analytic_distribution\" IN", f"\"analytic_distribution\" ?&")
        filters = self.remove_all_redundant_parentheses(filters)
        # Get move lines base on sql query and Calculate the total balance of move lines
        # sql = ('''SELECT l.id AS lid, l.account_id AS account_id, l.date AS ldate, j.code AS lcode, l.currency_id, l.amount_currency, l.ref AS lref, l.name AS lname, COALESCE(l.debit,0) AS debit, COALESCE(l.credit,0) AS credit, COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) AS balance,\
        #     m.name AS move_name, c.symbol AS currency_code, p.name AS partner_name\
        #     FROM account_move_line l\
        #     JOIN account_move m ON (l.move_id=m.id)\
        #     LEFT JOIN res_currency c ON (l.currency_id=c.id)\
        #     LEFT JOIN res_partner p ON (l.partner_id=p.id)\
        #     JOIN account_journal j ON (l.journal_id=j.id)\
        #     JOIN account_account acc ON (l.account_id = acc.id) \
        #     WHERE l.account_id IN %s ''' + filters + ''' GROUP BY l.id, l.account_id, l.date, j.code, l.currency_id, l.amount_currency, l.ref, l.name, m.name, c.symbol, p.name ORDER BY ''' + sql_sort)

        sql = ('''SELECT l.id AS lid, l.account_id AS account_id, l.date AS ldate, l.currency_id, l.amount_currency, l.ref AS lref, l.name AS lname, l.analytic_distribution as analytic_distribution, COALESCE(l.debit,0) AS debit, COALESCE(l.credit,0) AS credit, COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) AS balance,\
                    m.name AS move_name \
                    FROM account_move_line l\
                    JOIN account_move m ON (l.move_id=m.id)\
                    JOIN account_account acc ON (l.account_id = acc.id) \
                    WHERE l.account_id IN %s ''' + filters + ''' GROUP BY l.id, l.account_id, l.date, m.name, l.amount_currency, l.ref, l.name ORDER BY ''' + sql_sort)


        params = (tuple(accounts.ids),) + tuple(where_params)
        final_query = self.build_sql(sql, params)
        final_query = final_query.replace("WHERE", "WHERE ")
        final_query = final_query.replace("GROUP", " GROUP")
        # final_query = final_query.replace("analytic_distribution", " analytic_distribution::jsonb")
        cr.execute(final_query)
        data_rows = cr.dictfetchall()
        data_rows = self._filter_analytic_data(data_rows)
        for row in data_rows:
            balance = 0
            for line in move_lines.get(row['account_id']):
                balance += line['debit'] - line['credit']
            row['balance'] += balance
            move_lines[row.pop('account_id')].append(row)

        # Calculate the debit, credit and balance for Accounts
        account_res = []
        for account in accounts:
            currency = account.currency_id and account.currency_id or account.company_id.currency_id
            res = dict((fn, 0.0) for fn in ['credit', 'debit', 'balance'])
            res['code'] = account.code
            res['name'] = account.name
            res['move_lines'] = move_lines[account.id]
            for line in res.get('move_lines'):
                res['debit'] += line['debit']
                res['credit'] += line['credit']
                res['balance'] = line['balance']
            if display_account == 'all':
                account_res.append(res)
            if display_account == 'movement' and res.get('move_lines'):
                account_res.append(res)
            if display_account == 'not_zero' and not currency.is_zero(res['balance']):
                account_res.append(res)
        return account_res

    def _print_report_excel(self,data):
        self.ensure_one()
        #row_data = self.check_report()
        #docs = self.env[self.model].browse(self.env.context.get('active_ids', []))

        #default company currency
        currency = self.env.ref('base.main_company').currency_id

        #data = row_data.get('data', {})
        data = self.pre_print_report(data)
        data['form'].update(self.read(['initial_balance', 'sortby'])[0])
        if data['form'].get('initial_balance') and not data['form'].get('date_from'):
            raise UserError(_("You must define a Start Date"))
        
        #self.model = self._inherit

        init_balance = data['form'].get('initial_balance', True)
        sortby = data['form'].get('sortby', 'sort_date')
        display_account = data['form']['display_account']
        codes = []
        if data['form'].get('journal_ids', False):
            codes = [journal.code for journal in
                     self.env['account.journal'].search([('id', 'in', data['form']['journal_ids'])])]

        # accounts = self.env['account.account'].search([])
        if data['form'].get('account_ids', False):
            accounts = self.env['account.account'].browse(data['form'].get('account_ids'))
        else:
            accounts = self.env['account.account'].search([])
        accounts_res = self.with_context(data['form'].get('used_context', {}))._get_account_move_entry(accounts,
                                                                                                       init_balance,
                                                                                                       sortby,
                                                                                                       display_account)

        print_journal = codes

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
        
        tilte = "%s : %s" % (company.name, " General Ledger")
        sheet = workbook.add_sheet(tilte)
        sheet.set_panes_frozen(True)
        sheet.set_horz_split_pos(1)
        sheet.row(0).height = 256 * 3

        row_start, col_start = 0, 0
        sheet.write_merge(row_start, row_start, col_start, col_start + 8, tilte, M_header_tstyle)
        row_start += 2
        col_start = 0
        sheet.write_merge(row_start, row_start, col_start, col_start  + 3, _('Journals'), header_tstyle_c)
        col_start += 4
        sheet.write_merge(row_start, row_start, col_start, col_start + 1, _('Display Account'), header_tstyle_c)
        col_start += 2
        sheet.write_merge(row_start, row_start, col_start, col_start + 2, _('Target Moves:'), header_tstyle_c)
        row_start += 1
        col_start = 0
        sheet.write_merge(row_start, row_start, col_start, col_start + 3, ', '.join([lt or '' for lt in print_journal]))
        col_start += 4
        if display_account == 'all':
            sheet.write_merge(row_start, row_start, col_start, col_start + 1, _('All accounts'),other_tstyle_c)
        if display_account == 'movement':
            sheet.write_merge(row_start, row_start, col_start, col_start + 1, _('With movements'),other_tstyle_c)
        if display_account == 'not_zero':
            sheet.write_merge(row_start, row_start, col_start, col_start + 1, _('With balance not equal to zero'),other_tstyle_c)
        col_start += 2
        if data['form']['target_move'] == 'all':
            sheet.write_merge(row_start, row_start, col_start, col_start + 2, _('All Entries'),other_tstyle_c)
        if data['form']['target_move'] == 'posted':
            sheet.write_merge(row_start, row_start, col_start, col_start + 2, _('All Posted Entries'),other_tstyle_c)

        row_start += 2
        col_start = 0
        sheet.write_merge(row_start, row_start, col_start, col_start  + 1, _('Sorted By: '), header_tstyle_c)
        if data['form']['date_from']:
            col_start += 2
            sheet.write_merge(row_start, row_start, col_start, col_start + 1, _('Date From: '), header_tstyle_c)
            col_start += 2
            sheet.write_merge(row_start, row_start, col_start, col_start + 1, str(data['form']['date_from']),other_tstyle_c)
        row_start += 1
        col_start = 0
        if data['form']['sortby'] == 'sort_date':
            sheet.write_merge(row_start, row_start, col_start, col_start + 1, _('Date'),other_tstyle_c)
        if data['form']['sortby'] == 'sort_journal_partner':
            sheet.write_merge(row_start, row_start, col_start, col_start + 1, _('Journal and Partner'),other_tstyle_c)
        if data['form']['date_to']:
            col_start += 2
            sheet.write_merge(row_start, row_start, col_start, col_start + 1, _('Date To: '), header_tstyle_c)
            col_start += 2
            sheet.write_merge(row_start, row_start, col_start, col_start + 1, str(data['form']['date_to']),other_tstyle_c)

        col_start = 0
        row_start += 2
        sheet.col(col_start).width = 256 * 10
        sheet.write(row_start, col_start, _('Date'), header_tstyle_c)
        col_start += 1
        sheet.col(col_start).width = 256 * 10
        sheet.write(row_start, col_start, _('JRNL'), header_tstyle_c)
        col_start += 1
        sheet.col(col_start).width = 256 * 40
        sheet.write(row_start, col_start, _('Partner'), header_tstyle_c)
        col_start += 1
        sheet.col(col_start).width = 256 * 20
        sheet.write(row_start, col_start, _('Ref'), header_tstyle_c)
        col_start += 1
        sheet.col(col_start).width = 256 * 20
        sheet.write(row_start, col_start,  _('Move'), header_tstyle_c)
        col_start += 1
        sheet.col(col_start).width = 256 * 50
        sheet.write(row_start, col_start,  _('Entry Label'), header_tstyle_c)
        col_start += 1
        sheet.col(col_start).width = 256 * 30
        sheet.write(row_start, col_start,  _('Debit'), header_tstyle_c)
        col_start += 1
        sheet.col(col_start).width = 256 * 30
        sheet.write(row_start, col_start,  _('Credit'), header_tstyle_c)
        col_start += 1
        sheet.col(col_start).width = 256 * 30
        sheet.write(row_start, col_start,  _('Balance'), header_tstyle_c)
        col_start += 1
        for acc in accounts_res:
            col_start = 0
            row_start += 1
            sheet.write_merge(row_start, row_start, col_start, col_start + 5, _(acc.get('code') + " " + acc.get('name')), other_tstyle_b)
            col_start += 6
            sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(acc.get('debit')), other_tstyle_b)
            col_start += 1
            sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(acc.get('credit')), other_tstyle_b)
            col_start += 1
            sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(acc.get('balance')), other_tstyle_b)
            for move in acc.get('move_lines'):
                row_start += 1
                col_start = 0
                sheet.write(row_start, col_start, str(move.get('ldate')))
                col_start += 1
                sheet.write(row_start, col_start, move.get('lcode'))
                col_start += 1
                sheet.write(row_start, col_start, move.get('partner_name'))
                col_start += 1
                sheet.write(row_start, col_start, move.get('lref'))
                col_start += 1
                sheet.write(row_start, col_start, move.get('move_name'))
                col_start += 1
                sheet.write(row_start, col_start, move.get('lname'))
                col_start += 1
                sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(move.get('debit')))
                col_start += 1
                sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(move.get('credit')))
                col_start += 1
                sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(move.get('balance')))
            row_start += 1
            col_start = 0
            sheet.write_merge(row_start,row_start, col_start, col_start + 8, "")

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
