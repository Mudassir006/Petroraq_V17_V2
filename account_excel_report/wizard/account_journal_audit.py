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

class AccountingJournalReport(models.TransientModel):
    _inherit = "account.print.journal"

    def lines(self, target_move, journal_ids, sort_selection, data):
        if isinstance(journal_ids, int):
            journal_ids = [journal_ids]

        move_state = ['draft', 'posted']
        if target_move == 'posted':
            move_state = ['posted']

        query_get_clause = self._get_query_get_clause(data)
        params = [tuple(move_state), tuple(journal_ids)] + query_get_clause[2]
        query = 'SELECT "account_move_line".id, "account_move_line". as analytic_distribution FROM ' + query_get_clause[0] + ', account_move am, account_account acc WHERE "account_move_line".account_id = acc.id AND "account_move_line".move_id=am.id AND am.state IN %s AND "account_move_line".journal_id IN %s AND ' + query_get_clause[1] + ' ORDER BY '
        if sort_selection == 'date':
            query += '"account_move_line".date'
        else:
            query += 'am.name'
        query += ', "account_move_line".move_id, acc.code'
        self.env.cr.execute(query, tuple(params))
        ids = (x[0] for x in self.env.cr.fetchall())
        return self.env['account.move.line'].browse(ids)

    def _sum_debit(self, data, journal_id):
        move_state = ['draft', 'posted']
        if data['form'].get('target_move', 'all') == 'posted':
            move_state = ['posted']

        query_get_clause = self._get_query_get_clause(data)
        params = [tuple(move_state), tuple(journal_id.ids)] + query_get_clause[2]
        self.env.cr.execute('SELECT SUM(debit) FROM ' + query_get_clause[0] + ', account_move am '
                        'WHERE "account_move_line".move_id=am.id AND am.state IN %s AND "account_move_line".journal_id IN %s AND ' + query_get_clause[1] + ' ',
                        tuple(params))
        return self.env.cr.fetchone()[0] or 0.0

    def _sum_credit(self, data, journal_id):
        move_state = ['draft', 'posted']
        if data['form'].get('target_move', 'all') == 'posted':
            move_state = ['posted']

        query_get_clause = self._get_query_get_clause(data)
        params = [tuple(move_state), tuple(journal_id.ids)] + query_get_clause[2]
        self.env.cr.execute('SELECT SUM(credit) FROM ' + query_get_clause[0] + ', account_move am '
                        'WHERE "account_move_line".move_id=am.id AND am.state IN %s AND "account_move_line".journal_id IN %s AND ' + query_get_clause[1] + ' ',
                        tuple(params))
        return self.env.cr.fetchone()[0] or 0.0

    def _get_taxes(self, data, journal_id):
        move_state = ['draft', 'posted']
        if data['form'].get('target_move', 'all') == 'posted':
            move_state = ['posted']

        query_get_clause = self._get_query_get_clause(data)
        params = [tuple(move_state), tuple(journal_id.ids)] + query_get_clause[2]
        query = """
            SELECT rel.account_tax_id, SUM("account_move_line".balance) AS base_amount
            FROM account_move_line_account_tax_rel rel, """ + query_get_clause[0] + """ 
            LEFT JOIN account_move am ON "account_move_line".move_id = am.id
            WHERE "account_move_line".id = rel.account_move_line_id
                AND am.state IN %s
                AND "account_move_line".journal_id IN %s
                AND """ + query_get_clause[1] + """
           GROUP BY rel.account_tax_id"""
        self.env.cr.execute(query, tuple(params))
        ids = []
        base_amounts = {}
        for row in self.env.cr.fetchall():
            ids.append(row[0])
            base_amounts[row[0]] = row[1]


        res = {}
        for tax in self.env['account.tax'].browse(ids):
            self.env.cr.execute('SELECT sum(debit - credit) FROM ' + query_get_clause[0] + ', account_move am '
                'WHERE "account_move_line".move_id=am.id AND am.state IN %s AND "account_move_line".journal_id IN %s AND ' + query_get_clause[1] + ' AND tax_line_id = %s',
                tuple(params + [tax.id]))
            res[tax] = {
                'base_amount': base_amounts[tax.id],
                'tax_amount': self.env.cr.fetchone()[0] or 0.0,
            }
            if journal_id.type == 'sale':
                #sales operation are credits
                res[tax]['base_amount'] = res[tax]['base_amount'] * -1
                res[tax]['tax_amount'] = res[tax]['tax_amount'] * -1
        return res

    def _get_query_get_clause(self, data):
        return self.env['account.move.line'].with_context(data['form'].get('used_context', {}))._query_get()


    def _print_report_excel(self,data):
        self.ensure_one()
        company = self.env.user.company_id
        #row_data = self.check_report()

        #default company currency
        currency = self.env.ref('base.main_company').currency_id

        #data = row_data.get('data', {})
        data = self.pre_print_report(data)
        data['form'].update({'sort_selection': self.sort_selection})
        #self.model = self._inherit
        if not data.get('form'):
            raise UserError(_("Form content is missing, this report cannot be printed."))

        target_move = data['form'].get('target_move', 'all')
        sort_selection = data['form'].get('sort_selection', 'date')

        res = {}
        for journal in data['form']['journal_ids']:
            res[journal] = self.with_context(data['form'].get('used_context', {})).lines(target_move, journal, sort_selection, data)
            
        
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
        other_tstyle_b = xls_format.font_style(position='center',
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
        
        sheet = workbook.add_sheet('Journal Report')
        row_start = 0
        for journal_obj in self.env['account.journal'].browse(data['form']['journal_ids']):
            col_start =0
            tilte = "%s  %s" % (journal_obj.name,'Journal')
            sheet.row(row_start).height = 256 * 2
            sheet.write_merge(row_start, row_start, col_start, 7, tilte, M_header_tstyle)
            row_start +=1
            
            sheet.col(col_start).width = 256 * 20
            sheet.write_merge(row_start, row_start, col_start, col_start + 1, _('Company:'), header_tstyle_c)
            col_start += 2
            sheet.col(col_start).width = 256 * 20
            sheet.write_merge(row_start, row_start, col_start, col_start + 1, _('Journal:'), header_tstyle_c)
            col_start += 2
            sheet.col(col_start).width = 256 * 20
            sheet.write_merge(row_start, row_start, col_start, col_start + 1, _('Entries Sorted By:'), header_tstyle_c)
            col_start += 2
            sheet.col(col_start).width = 256 * 20
            sheet.write_merge(row_start, row_start, col_start, col_start + 1, _('Target Moves:'), header_tstyle_c)
            row_start += 1
            col_start = 0
            sheet.col(col_start).width = 256 * 20
            sheet.write_merge(row_start, row_start, col_start, col_start + 1, company.name,other_tstyle_c)
            col_start += 2
            sheet.col(col_start).width = 256 * 20
            sheet.write_merge(row_start, row_start, col_start, col_start + 1, journal_obj.name,other_tstyle_c)
            col_start += 2
            if data['form']['sort_selection'] == 'l.date':
                sheet.col(col_start).width = 256 * 20
                sheet.write_merge(row_start, row_start, col_start, col_start + 1, _('Date'),other_tstyle_c)
                col_start += 2
            else:
                sheet.col(col_start).width = 256 * 20
                sheet.write_merge(row_start, row_start, col_start, col_start + 1, _('Journal Entry Number'),other_tstyle_c)
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
            sheet.write(row_start, col_start,  _('Move'), other_tstyle_b)
            col_start += 1
            sheet.col(col_start).width = 256 * 20
            sheet.write(row_start, col_start,  _('Date'), other_tstyle_b)        
            col_start += 1
            sheet.col(col_start).width = 256 * 20
            sheet.write(row_start, col_start,  _('Account'), other_tstyle_b)  
            col_start += 1
            sheet.col(col_start).width = 256 * 30
            sheet.write(row_start, col_start,  _('Partner'), other_tstyle_b)
            col_start += 1
            sheet.col(col_start).width = 256 * 20
            sheet.write(row_start, col_start,  _('Label'), other_tstyle_b)
            col_start += 1
            sheet.col(col_start).width = 256 * 20
            sheet.write(row_start, col_start,  _('Debit'), other_tstyle_b)
            col_start += 1
            sheet.col(col_start).width = 256 * 20
            sheet.write(row_start, col_start,  _('Credit'), other_tstyle_b) 
            if data['form']['amount_currency']:
                col_start += 1
                sheet.col(col_start).width = 256 * 10
                sheet.write(row_start, col_start,  _('Currency'), other_tstyle_b)
                
            
            for line in res[journal_obj.id]:
                row_start += 1
                col_start = 0
                sheet.col(col_start).width = 256 * 20
                sheet.write(row_start, col_start, line.move_id.name+'&lt;&gt;'+'/' and line.move_id.name or ('*'+str(line.move_id.id)),other_tstyle)
                col_start += 1
                sheet.col(col_start).width = 256 * 20
                sheet.write(row_start, col_start, str(line.date),other_tstyle)
                col_start += 1
                sheet.col(col_start).width = 256 * 20
                sheet.write(row_start, col_start, line.account_id.code,other_tstyle)
                col_start += 1
                sheet.col(col_start).width = 256 * 30
                sheet.write(row_start, col_start, line.sudo().partner_id and line.sudo().partner_id.name and line.sudo().partner_id.name[:23] or '',other_tstyle)
                col_start += 1
                sheet.col(col_start).width = 256 * 20
                sheet.write(row_start, col_start, line.name and line.name[:35],other_tstyle)
                col_start += 1
                sheet.col(col_start).width = 256 * 20
                sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(line.debit),other_tstyle_r)
                col_start += 1
                sheet.col(col_start).width = 256 * 20
                sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(line.credit),other_tstyle_r)              
                if data['form']['amount_currency'] and line.amount_currency:
                    col_start += 1
                    sheet.col(col_start).width = 256 * 10
                    sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(line.currency_id),other_tstyle_c)
                    
            row_start += 1
            col_start =4
            sheet.col(col_start).width = 256 * 20
            sheet.write(row_start, col_start,  _('Total'), other_tstyle_b)
            col_start += 1
            sheet.col(col_start).width = 256 * 20
            sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(self._sum_debit(data,journal_obj)),other_tstyle_r)
            col_start += 1
            sheet.col(col_start).width = 256 * 20
            sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(self._sum_credit(data,journal_obj)),other_tstyle_r)

            row_start += 1
            col_start =0

            sheet.col(col_start).width = 256 * 30
            sheet.write_merge(row_start, row_start, col_start, col_start + 2, _('Tax Declaration'), header_tstyle_c)
            
            row_start += 1
            col_start =0
            sheet.col(col_start).width = 256 * 20
            sheet.write(row_start, col_start,  _('Name'), other_tstyle_b)
            col_start += 1
            sheet.col(col_start).width = 256 * 20
            sheet.write(row_start, col_start,  _('Base Amount'), other_tstyle_b)        
            col_start += 1
            sheet.col(col_start).width = 256 * 20
            sheet.write(row_start, col_start,  _('Tax Amount'), other_tstyle_b)

            row_start += 1
            col_start =0

            taxes = self._get_taxes(data,journal_obj)

            for tax in taxes:
                sheet.col(col_start).width = 256 * 30
                sheet.write(row_start, col_start,  tax.name, other_tstyle)
                col_start += 1
                sheet.col(col_start).width = 256 * 30
                sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(taxes[tax]['base_amount']),other_tstyle_r)
                col_start += 1
                sheet.col(col_start).width = 256 * 30
                sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(taxes[tax]['tax_amount']),other_tstyle_r)

            row_start += 2
                
        stream = io.BytesIO()
        workbook.save(stream)

        export_obj = self.env['single.click.download.xls']
        self._cr.execute(""" DELETE FROM single_click_download_xls""")
        res_id = export_obj.create({
                                'file': base64.encodebytes(stream.getvalue()),
                                'fname': "Journal Report.xls"
                                })
        return {
             'type': 'ir.actions.act_url',
             'url': '/web/binary/download_document?model=single.click.download.xls&field=file&id=%s&filename=Journal Report.xls'%(res_id.id),
             'target': 'new',
             }
