# -*- coding: utf-8 -*-
#################################################################################
#
#Copyright (c) 2013-Present IctPack Solutions LTD. (<http://ictpack.com>)
#
#################################################################################

import base64
import xlwt
import io
from . import xls_format

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountingReportPartnerLedger(models.TransientModel):
    _inherit = "account.report.partner.ledger"

    def _lines(self, data, partner):
        full_account = []
        currency = self.env['res.currency']
        query_get_data = self.env['account.move.line'].with_context(data['form'].get('used_context', {}))._query_get()
        reconcile_clause = "" if data['form']['reconciled'] else ' AND "account_move_line".full_reconcile_id IS NULL '
        params = [partner.id, tuple(data['computed']['move_state']), tuple(data['computed']['account_ids'])] + query_get_data[2]
        query = """
            SELECT "account_move_line".id, "account_move_line".analytic_distribution as analytic_distribution, "account_move_line".date, j.code, acc.code as a_code, acc.name as a_name, "account_move_line".ref, m.name as move_name, "account_move_line".name, "account_move_line".debit, "account_move_line".credit, "account_move_line".amount_currency,"account_move_line".currency_id, c.symbol AS currency_code
            FROM """ + query_get_data[0] + """
            LEFT JOIN account_journal j ON ("account_move_line".journal_id = j.id)
            LEFT JOIN account_account acc ON ("account_move_line".account_id = acc.id)
            LEFT JOIN res_currency c ON ("account_move_line".currency_id=c.id)
            LEFT JOIN account_move m ON (m.id="account_move_line".move_id)
            WHERE "account_move_line".partner_id = %s
                AND m.state IN %s
                AND "account_move_line".account_id IN %s """ + query_get_data[1] + reconcile_clause + """
                ORDER BY "account_move_line".date"""
        self.env.cr.execute(query, tuple(params))
        res = self.env.cr.dictfetchall()
        res = self._filter_analytic_data(res)
        sum = 0.0
        lang_code = self.env.context.get('lang') or 'en_US'
        lang = self.env['res.lang']
        lang_id = lang._lang_get(lang_code)
        date_format = lang_id.date_format
        for r in res:
            r['date'] = r['date']
            r['displayed_name'] = '-'.join(
                r[field_name] for field_name in ('move_name', 'ref', 'name')
                if r[field_name] not in (None, '', '/')
            )
            sum += r['debit'] - r['credit']
            r['progress'] = sum
            r['currency_id'] = currency.browse(r.get('currency_id'))
            full_account.append(r)
        return full_account

    def _sum_partner(self, data, partner, field):
        if field not in ['debit', 'credit', 'debit - credit']:
            return
        result = 0.0
        query_get_data = self.env['account.move.line'].with_context(data['form'].get('used_context', {}))._query_get()
        reconcile_clause = "" if data['form']['reconciled'] else ' AND "account_move_line".full_reconcile_id IS NULL '
        params = [partner.id, tuple(data['computed']['move_state']), tuple(data['computed']['account_ids'])] + query_get_data[2]
        query = """SELECT sum(""" + field + """)
                FROM """ + query_get_data[0] + """, account_move AS m
                WHERE "account_move_line".partner_id = %s
                    AND m.id = "account_move_line".move_id
                    AND m.state IN %s
                    AND account_id IN %s
                    """ + query_get_data[1] + reconcile_clause
        self.env.cr.execute(query, tuple(params))
        contemp = self.env.cr.fetchone()
        if contemp is not None:
            result = contemp[0] or 0.0
        return result

    def _print_report_excel(self,data):
        self.ensure_one()
        company = self.env.user.company_id
        #row_data = self.check_report()

        #default company currency
        currency = self.env.ref('base.main_company').currency_id

        #data = row_data.get('data', {})
        data = self.pre_print_report(data)
        data['form'].update({'reconciled': self.reconciled,
                             'amount_currency': self.amount_currency})
        data['computed'] = {}
        #self.model = self._inherit
        if not data.get('form'):
            raise UserError(_("Form content is missing, this report cannot be printed."))

        data['computed'] = {}
        obj_partner = self.env['res.partner']
        query_get_data = self.env['account.move.line'].with_context(data['form'].get('used_context', {}))._query_get()
        data['computed']['move_state'] = ['draft', 'posted']
        if data['form'].get('target_move', 'all') == 'posted':
            data['computed']['move_state'] = ['posted']
        result_selection = data['form'].get('result_selection', 'customer')
        if result_selection == 'supplier':
            data['computed']['ACCOUNT_TYPE'] = ['liability_payable']
        elif result_selection == 'customer':
            data['computed']['ACCOUNT_TYPE'] = ['asset_receivable']
        else:
            data['computed']['ACCOUNT_TYPE'] = ['asset_receivable', 'liability_payable']

        self.env.cr.execute("""
            SELECT a.id
            FROM account_account a
            WHERE a.account_type IN %s
            AND NOT a.deprecated""", (tuple(data['computed']['ACCOUNT_TYPE']),))
        data['computed']['account_ids'] = [a for (a,) in self.env.cr.fetchall()]
        params = [tuple(data['computed']['move_state']), tuple(data['computed']['account_ids'])] + query_get_data[2]
        reconcile_clause = "" if data['form']['reconciled'] else ' AND "account_move_line".full_reconcile_id IS NULL '
        query = """
            SELECT DISTINCT "account_move_line".partner_id, "account_move_line".analytic_distribution as analytic_distribution
            FROM """ + query_get_data[0] + """, account_account AS account, account_move AS am
            WHERE "account_move_line".partner_id IS NOT NULL
                AND "account_move_line".account_id = account.id
                AND am.id = "account_move_line".move_id
                AND am.state IN %s
                AND "account_move_line".account_id IN %s
                AND NOT account.deprecated
                """ + query_get_data[1] + reconcile_clause
        self.env.cr.execute(query, tuple(params))
        data_rows = self.env.cr.dictfetchall()
        data_rows = self._filter_analytic_data(data_rows)
        # partner_ids = [res['partner_id'] for res in self.env.cr.dictfetchall()]
        partner_ids = [res['partner_id'] for res in data_rows]
        partners = obj_partner.browse(partner_ids)
        partners = sorted(partners, key=lambda x: (x.ref or '', x.name or ''))
            
        
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
                                              #border=1,
                                              fontos='black',
                                              font_height=180,
                                              color='yellow'
                                              )
        header_tstyle_c = xls_format.font_style(position='center',
                                                bold=1,
                                                #border=1,
                                                fontos='black',
                                                font_height=180,
                                                color='grey')
        header_tstyle_r = xls_format.font_style(position='right',
                                                bold=1,
                                                #border=1,
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
                                               #border=1,
                                               font_height=180,
                                               )
        other_tstyle_b = xls_format.font_style(position='left',
                                                bold=1,
                                                #border=1,
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
        
        sheet = workbook.add_sheet('Partner Ledger')
        tilte = "Partner Ledger"
        sheet.row(0).height = 256 * 2
        sheet.write_merge(0, 0, 0, 6, tilte, M_header_tstyle)
        row_start = 1
        for partner in partners:
            col_start =0
            sheet.col(col_start).width = 256 * 20
            sheet.write_merge(row_start, row_start, col_start, col_start + 1, _('Company:'), header_tstyle_c)
            col_start += 2
            if data['form']['date_from']:
                sheet.col(col_start).width = 256 * 20
                sheet.write_merge(row_start, row_start, col_start, col_start + 1, _('Date From:'), header_tstyle_c)
                col_start += 2
                sheet.col(col_start).width = 256 * 20
                sheet.write_merge(row_start, row_start, col_start, col_start + 1, data['form']['date_from'], other_tstyle_c)
                col_start += 2
            sheet.col(col_start).width = 256 * 20
            sheet.write_merge(row_start, row_start, col_start, col_start + 1, _('Target Moves:'), header_tstyle_c)
            row_start += 1
            col_start = 0
            sheet.col(col_start).width = 256 * 20
            sheet.write_merge(row_start, row_start, col_start, col_start + 1, company.name,other_tstyle_c)
            col_start += 2
            if data['form']['date_to']:
                sheet.col(col_start).width = 256 * 20
                sheet.write_merge(row_start, row_start, col_start, col_start + 1, _('Date To:'),header_tstyle_c)
                col_start += 2
                sheet.col(col_start).width = 256 * 20
                sheet.write_merge(row_start, row_start, col_start, col_start + 1, data['form']['date_to'],other_tstyle_c)
                col_start += 2
            if data['form']['target_move'] == 'all':
                sheet.col(col_start).width = 256 * 20
                sheet.write(row_start, row_start, col_start, col_start + 1, _('All Entries'),other_tstyle_c)
            if data['form']['target_move'] == 'posted':
                sheet.col(col_start).width = 256 * 20
                sheet.write_merge(row_start, row_start, col_start, col_start + 1, _('All Posted Entries'),other_tstyle_c)
                
            col_start = 0
            row_start += 1
            sheet.col(col_start).width = 256 * 20
            sheet.write(row_start, col_start,  _('Date'), other_tstyle_b)
            col_start += 1
            sheet.col(col_start).width = 256 * 20
            sheet.write(row_start, col_start,  _('JRNL'), other_tstyle_b)        
            col_start += 1
            sheet.col(col_start).width = 256 * 20
            sheet.write(row_start, col_start,  _('Account'), other_tstyle_b)  
            col_start += 1
            sheet.col(col_start).width = 256 * 30
            sheet.write(row_start, col_start,  _('Ref'), other_tstyle_b)
            col_start += 1
            sheet.col(col_start).width = 256 * 20
            sheet.write(row_start, col_start,  _('Debit'), other_tstyle_b)
            col_start += 1
            sheet.col(col_start).width = 256 * 20
            sheet.write(row_start, col_start,  _('Credit'), other_tstyle_b)
            col_start += 1
            sheet.col(col_start).width = 256 * 20
            sheet.write(row_start, col_start,  _('Balance'), other_tstyle_b) 
            if data['form']['amount_currency']:
                col_start += 1
                sheet.col(col_start).width = 256 * 10
                sheet.write(row_start, col_start,  _('Currency'), other_tstyle_b)

            row_start += 1
            col_start = 0
            sheet.col(col_start).width = 256 * 20
            sheet.write_merge(row_start, row_start, col_start, col_start + 3, '--'+partner.name,other_tstyle_b)
            col_start += 4
            sheet.col(col_start).width = 256 * 20
            sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(self._sum_partner(data,partner,'debit')),other_tstyle_r)
            col_start += 1
            sheet.col(col_start).width = 256 * 20
            sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(self._sum_partner(data,partner,'credit')),other_tstyle_r)
            col_start += 1
            sheet.col(col_start).width = 256 * 20
            sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(self._sum_partner(data,partner,'debit - credit')),other_tstyle_r)

            lines = self._lines(data, partner)
            
            for line in lines:
                row_start += 1
                col_start = 0
                sheet.col(col_start).width = 256 * 20
                sheet.write(row_start, col_start, str(line.get('date')),other_tstyle)
                col_start += 1
                sheet.col(col_start).width = 256 * 20
                sheet.write(row_start, col_start, line.get('code'),other_tstyle)
                col_start += 1
                sheet.col(col_start).width = 256 * 20
                sheet.write(row_start, col_start, line.get('a_code'),other_tstyle)
                col_start += 1
                sheet.col(col_start).width = 256 * 30
                sheet.write(row_start, col_start, line.get('displayed_name'),other_tstyle)
                col_start += 1
                sheet.col(col_start).width = 256 * 20
                sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(line.get('debit')),other_tstyle_r)
                col_start += 1
                sheet.col(col_start).width = 256 * 20
                sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(line.get('credit')),other_tstyle_r)
                col_start += 1
                sheet.col(col_start).width = 256 * 20
                sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(line.get('progress')),other_tstyle_r)              
                if data['form']['amount_currency'] and line.get('currency_id'):
                    col_start += 1
                    sheet.col(col_start).width = 256 * 10
                    sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(line.get('amount_currency')),other_tstyle_c)
                    
            row_start += 2
                
        stream = io.BytesIO()
        workbook.save(stream)

        export_obj = self.env['single.click.download.xls']
        self._cr.execute(""" DELETE FROM single_click_download_xls""")
        res_id = export_obj.create({
                                'file': base64.encodebytes(stream.getvalue()),
                                'fname': "Partner Ledger.xls"
                                })
        return {
             'type': 'ir.actions.act_url',
             'url': '/web/binary/download_document?model=single.click.download.xls&field=file&id=%s&filename=Partner Ledger.xls'%(res_id.id),
             'target': 'new',
             }
