# -*- coding: utf-8 -*-
#################################################################################
#
#Copyright (c) 2013-Present IctPack Solutions LTD. (<http://ictpack.com>)
#
#################################################################################

import base64
import pytz
import xlwt
import io
from . import xls_format

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountingReport(models.TransientModel):
    _inherit = "accounting.report"
    _description = 'Report Financial'

    def _compute_account_balance(self, accounts):
        """ compute the balance, debit and credit for the provided accounts
        """
        mapping = {
            'balance': "COALESCE(SUM(debit),0) - COALESCE(SUM(credit), 0) as balance",
            'debit': "COALESCE(SUM(debit), 0) as debit",
            'credit': "COALESCE(SUM(credit), 0) as credit",
        }

        res = {}
        for account in accounts:
            res[account.id] = dict.fromkeys(mapping, 0.0)
        if accounts:
            tables, where_clause, where_params = self.env['account.move.line']._query_get()
            tables = tables.replace('"', '') if tables else "account_move_line"
            wheres = [""]
            if where_clause.strip():
                wheres.append(where_clause.strip())
            filters = " AND ".join(wheres)
            request = "SELECT account_id as id, analytic_distribution as analytic_distribution, " + ', '.join(mapping.values()) + \
                       " FROM " + tables + \
                       " WHERE account_id IN %s " \
                            + filters + \
                       " GROUP BY account_id, analytic_distribution"
            params = (tuple(accounts._ids),) + tuple(where_params)
            self.env.cr.execute(request, params)
            data_rows = self.env.cr.dictfetchall()
            data_rows = self._filter_analytic_data(data_rows)
            for row in data_rows:
                res[row['id']] = row
        return res

    def _compute_report_balance(self, reports):
        '''returns a dictionary with key=the ID of a record and value=the credit, debit and balance amount
           computed for this record. If the record is of type :
               'accounts' : it's the sum of the linked accounts
               'account_type' : it's the sum of leaf accoutns with such an account_type
               'account_report' : it's the amount of the related report
               'sum' : it's the sum of the children of this record (aka a 'view' record)'''
        res = {}
        fields = ['credit', 'debit', 'balance']
        for report in reports:
            if report.id in res:
                continue
            res[report.id] = dict((fn, 0.0) for fn in fields)
            if report.type == 'accounts':
                # it's the sum of the linked accounts
                res[report.id]['account'] = self._compute_account_balance(report.account_ids)
                for value in res[report.id]['account'].values():
                    for field in fields:
                        res[report.id][field] += value.get(field)
            elif report.type == 'account_type':
                # it's the sum the leaf accounts with such an account type
                accounts = self.env['account.account'].search(
                    [('account_type', 'in', report.account_type_ids.mapped('type'))])

                res[report.id]['account'] = self._compute_account_balance(accounts)
                for value in res[report.id]['account'].values():
                    for field in fields:
                        res[report.id][field] += value.get(field)
            elif report.type == 'account_report' and report.account_report_id:
                # it's the amount of the linked report
                res2 = self._compute_report_balance(report.account_report_id)
                for key, value in res2.items():
                    for field in fields:
                        res[report.id][field] += value[field]
            elif report.type == 'sum':
                # it's the sum of the children of this account.report
                res2 = self._compute_report_balance(report.children_ids)
                for key, value in res2.items():
                    for field in fields:
                        res[report.id][field] += value[field]
        return res

    def get_account_lines(self, data):
        lines = []
        account_report = self.env['account.financial.report'].search(
            [('id', '=', data['account_report_id'][0])])
        child_reports = account_report._get_children_by_order()
        res = self.with_context(data.get('used_context'))._compute_report_balance(child_reports)
        if data['enable_filter']:
            comparison_res = self.with_context(
                data.get('comparison_context'))._compute_report_balance(
                child_reports)
            for report_id, value in comparison_res.items():
                res[report_id]['comp_bal'] = value['balance']
                report_acc = res[report_id].get('account')
                if report_acc:
                    for account_id, val in comparison_res[report_id].get('account').items():
                        report_acc[account_id]['comp_bal'] = val['balance']
        for report in child_reports:
            vals = {
                'name': report.name,
                'balance': res[report.id]['balance'] * float(report.sign),
                'type': 'report',
                'level': bool(report.style_overwrite) and report.style_overwrite or report.level,
                'account_type': report.type or False, #used to underline the financial report balances
            }
            if data['debit_credit']:
                vals['debit'] = res[report.id]['debit']
                vals['credit'] = res[report.id]['credit']

            if data['enable_filter']:
                vals['balance_cmp'] = res[report.id]['comp_bal'] * float(report.sign)

            lines.append(vals)
            if report.display_detail == 'no_detail':
                #the rest of the loop is used to display the details of the financial report, so it's not needed here.
                continue
            if res[report.id].get('account'):
                sub_lines = []
                for account_id, value in res[report.id]['account'].items():
                    #if there are accounts to display, we add them to the lines with a level equals to their level in
                    #the COA + 1 (to avoid having them with a too low level that would conflicts with the level of data
                    #financial reports for Assets, liabilities...)
                    flag = False
                    account = self.env['account.account'].browse(account_id)
                    vals = {
                        'name': account.code + ' ' + account.name,
                        'balance': value['balance'] * float(report.sign) or 0.0,
                        'type': 'account',
                        'level': report.display_detail == 'detail_with_hierarchy' and 4,
                        'account_type': account.account_type,
                    }
                    if data['debit_credit']:
                        vals['debit'] = value['debit']
                        vals['credit'] = value['credit']
                        if not account.company_id.currency_id.is_zero(vals['debit']) or not account.company_id.currency_id.is_zero(vals['credit']):
                            flag = True
                    if not account.company_id.currency_id.is_zero(vals['balance']):
                        flag = True
                    if data['enable_filter']:
                        vals['balance_cmp'] = value['comp_bal'] * float(report.sign)
                        if not account.company_id.currency_id.is_zero(vals['balance_cmp']):
                            flag = True
                    if flag:
                        sub_lines.append(vals)
                lines += sorted(sub_lines, key=lambda sub_line: sub_line['name'])
        return lines

    def _print_report_excel(self,data):
        self.ensure_one()
        company = self.env.user.company_id
        row_data = self.check_report()

        #default company currency
        currency = self.env.ref('base.main_company').currency_id

        data = row_data.get('data', {})
        #data = self.check_report()
        #self.model = self._inherit
        accounts_res = self.get_account_lines(data.get('form'))
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
        
        display_account = data.get('form').get('target_move') 
        tilte = "%s : %s" % ("Financial Report", data.get('form').get('account_report_id')[1])
        sheet = workbook.add_sheet(tilte)
        sheet.set_panes_frozen(True)
        sheet.set_horz_split_pos(1)
        sheet.row(0).height = 256 * 3
        sheet.write_merge(0, 0, 0, 4, tilte, M_header_tstyle)
        
        
        
        row_start, col_start = 2, 0
        sheet.write_merge(row_start, row_start, col_start, col_start + 1, _('Target Moves:'), header_tstyle_c)
        if data.get('form').get('date_from'):
            col_start += 2
            sheet.col(col_start).width = 256 * 20
            sheet.write(row_start, col_start, 'Date from: ', header_tstyle_c)
            col_start += 1
            sheet.col(col_start).width = 256 * 20
            sheet.write(row_start, col_start, str(data.get('form').get('date_from')),other_tstyle_c)
        row_start += 1
        col_start = 0
        if display_account == 'all':
            sheet.write_merge(row_start, row_start, col_start, col_start + 1, _('All Entries:'), other_tstyle_c)
        if display_account == 'posted':
            sheet.write_merge(row_start, row_start, col_start, col_start + 1, _('All Posted Entries:'), other_tstyle_c)
        if data.get('form').get('date_to'):
            col_start += 2
            sheet.col(col_start).width = 256 * 20
            sheet.write(row_start, col_start, 'Date to: ', header_tstyle_c)
            col_start += 1
            sheet.col(col_start).width = 256 * 20
            sheet.write(row_start, col_start, str(data.get('form').get('date_to')),other_tstyle_c)
        if self.debit_credit:
            col_start = 0
            row_start += 2
            sheet.col(col_start).width = 256 * 70
            sheet.write(row_start, col_start,  _('Name'), other_tstyle_b)
            col_start += 2
            sheet.col(col_start).width = 256 * 30
            sheet.write(row_start, col_start,  _('Debit'), other_tstyle_b)        
            col_start += 1
            sheet.col(col_start).width = 256 * 30
            sheet.write(row_start, col_start,  _('Credit'), other_tstyle_b)  
            col_start += 1
            sheet.col(col_start).width = 256 * 30
            sheet.write(row_start, col_start,  _('Balance'), other_tstyle_b)  
            for acc in accounts_res:
                level = acc.get('level')
                if level != 0:
                    if int(level) < 3:
                        style_bold = other_tstyle_b
                    if int(level) >= 3:
                        style_bold = other_tstyle_r
                    col_start = 0
                    row_start += 1
                    sheet.write(row_start, col_start, acc.get('name'), style_bold)
                    col_start += 2
                    sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(acc.get('debit')), style_bold)
                    col_start += 1
                    sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(acc.get('credit')), style_bold)
                    col_start += 1
                    sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(acc.get('balance')), style_bold)
        if self.enable_filter and not self.debit_credit:
            col_start = 0
            row_start += 2
            sheet.col(col_start).width = 256 * 70
            sheet.write(row_start, col_start,  _('Name'), other_tstyle_b)
            col_start += 2
            sheet.col(col_start).width = 256 * 30
            sheet.write(row_start, col_start,  _('Balance'), other_tstyle_b) 
            col_start += 1
            sheet.col(col_start).width = 256 * 30
            sheet.write(row_start, col_start, _('%s') % self.label_filter, other_tstyle_b)
            for acc in accounts_res:
                level = acc.get('level')
                if level != 0:
                    if int(level) < 3:
                        style_bold = other_tstyle_b
                    if int(level) >= 3:
                        style_bold = other_tstyle_r
                    col_start = 0
                    row_start += 1
                    sheet.write(row_start, col_start, acc.get('name'), style_bold)
                    col_start += 2
                    sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(acc.get('balance')), style_bold)
                    col_start += 1
                    sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(acc.get('balance_cmp')), style_bold)
        if not self.enable_filter and not self.debit_credit:
            col_start = 0
            row_start += 2
            sheet.col(col_start).width = 256 * 70
            sheet.write(row_start, col_start,  _('Name'), other_tstyle_b)
            col_start += 3
            sheet.col(col_start).width = 256 * 30
            sheet.write(row_start, col_start,  _('Balance'), other_tstyle_b)
            for acc in accounts_res:
                level = acc.get('level')
                if level != 0:
                    if int(level) < 3:
                        style_bold = other_tstyle_b
                    if int(level) >= 3:
                        style_bold = other_tstyle_r
                    col_start = 0
                    row_start += 1
                    sheet.write(row_start, col_start, acc.get('name'), style_bold)
                    col_start += 3
                    sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(acc.get('balance')), style_bold)

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
