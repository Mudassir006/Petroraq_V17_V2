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

class AccountingTaxReport(models.TransientModel):
    _inherit = "account.tax.report.wizard"

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form'):
            raise UserError(_("Form content is missing, this report cannot be printed."))
        return {
            'data': data['form'],
            'lines': self.get_lines(data.get('form')),
        }

    def _sql_from_amls_one(self):
        sql = """SELECT "account_move_line".tax_line_id, COALESCE(SUM("account_move_line".debit-"account_move_line".credit), 0), "account_move_line".analytic_distribution as analytic_distribution
                    FROM %s
                    WHERE %s GROUP BY "account_move_line".tax_line_id, "account_move_line".analytic_distribution"""
        return sql

    def _sql_from_amls_two(self):
        sql = """SELECT r.account_tax_id, COALESCE(SUM("account_move_line".debit-"account_move_line".credit), 0), "account_move_line".analytic_distribution as analytic_distribution
                 FROM %s
                 INNER JOIN account_move_line_account_tax_rel r ON ("account_move_line".id = r.account_move_line_id)
                 INNER JOIN account_tax t ON (r.account_tax_id = t.id)
                 WHERE %s GROUP BY r.account_tax_id, "account_move_line".analytic_distribution"""
        return sql

    def _compute_from_amls(self, options, taxes):
        #compute the tax amount
        sql = self._sql_from_amls_one()
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        query = sql % (tables, where_clause)
        self.env.cr.execute(query, where_params)
        # results = self.env.cr.fetchall()
        results = self.env.cr.dictfetchall()
        results = self._filter_analytic_data(results)
        for result in results:
            # if result[0] in taxes:
            if result.get("tax_line_id") in taxes:
                # taxes[result[0]]['tax'] = abs(result[1])
                taxes[result.get("tax_line_id")]['tax'] = abs(result.get("coalesce"))

        #compute the net amount
        sql2 = self._sql_from_amls_two()
        query = sql2 % (tables, where_clause)
        self.env.cr.execute(query, where_params)
        # results = self.env.cr.fetchall()
        results = self.env.cr.dictfetchall()
        results = self._filter_analytic_data(results)
        for result in results:
            # if result[0] in taxes:
            if result.get("tax_line_id") in taxes:
                # taxes[result[0]]['net'] = abs(result[1])
                taxes[result.get("tax_line_id")]['net'] = abs(result.get("coalesce"))


    @api.model
    def get_lines(self, options):
        taxes = {}
        for tax in self.env['account.tax'].search([('type_tax_use', '!=', 'none')]):
            if tax.children_tax_ids:
                for child in tax.children_tax_ids:
                    if child.type_tax_use != 'none':
                        continue
                    taxes[child.id] = {'tax': 0, 'net': 0, 'name': child.name, 'type': tax.type_tax_use}
            else:
                taxes[tax.id] = {'tax': 0, 'net': 0, 'name': tax.name, 'type': tax.type_tax_use}
        self.with_context(date_from=options['date_from'], date_to=options['date_to'],
                          state=options['target_move'],
                          strict_range=True)._compute_from_amls(options, taxes)
        groups = dict((tp, []) for tp in ['sale', 'purchase'])
        for tax in taxes.values():
            if tax['tax']:
                groups[tax['type']].append(tax)
        return groups


    def _print_report_excel(self,data):
        self.ensure_one()
        company = self.env.user.company_id
        #row_data = self.check_report()

        #default company currency
        currency = self.env.ref('base.main_company').currency_id

        #data = row_data.get('data', {})
        #data = self.pre_print_report(data)
        #self.model = self._inherit
        if not data.get('form'):
            raise UserError(_("Form content is missing, this report cannot be printed."))

        lines = self.get_lines(data.get('form')) 
        
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
                                              #color='yellow'
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
                                               #border=1,
                                               font_height=180,
                                               #color='grey'
                                               )
        other_tstyle_rb = xls_format.font_style(position='right',
                                               fontos='black',
                                               bold=1,
                                               border=1,
                                               font_height=200,
                                               color='grey')
        
        Hedaer_Text = 'Tax Report'
        sheet = workbook.add_sheet(Hedaer_Text)
        sheet.set_panes_frozen(True)
        sheet.set_horz_split_pos(1)
        sheet.row(0).height = 256 * 3
        sheet.write_merge(0, 0, 0, 5, 'Tax Report', M_header_tstyle)

        sales_lines = lines['sale']
        purchase_lines = lines['purchase']

        row_start,col_start = 2,0

        if data['form']['date_from']:
            row_start,col_start = 2,1
            sheet.col(col_start).width = 256 * 20
            sheet.write_merge(row_start, row_start, col_start, col_start + 1, _('Date From: '), header_tstyle)
            col_start += 2
            sheet.col(col_start).width = 256 * 20
            sheet.write_merge(row_start, row_start, col_start, col_start + 1, str(data['form']['date_from']), other_tstyle)
            row_start += 1
            col_start = 1
            
        if data['form']['date_to']:
            sheet.col(col_start).width = 256 * 20
            sheet.write_merge(row_start, row_start, col_start, col_start + 1, _('Date To: '), header_tstyle)
            col_start += 2
            sheet.col(col_start).width = 256 * 20
            sheet.write_merge(row_start, row_start, col_start, col_start + 1, str(data['form']['date_to']) , other_tstyle)
            row_start += 1
            col_start = 0
        
        sheet.col(col_start).width = 256 * 20
        sheet.write_merge(row_start, row_start, col_start, col_start + 1, _('Sale'), header_tstyle)
        col_start += 2
        sheet.col(col_start).width = 256 * 20
        sheet.write_merge(row_start, row_start, col_start, col_start + 1, _('Net'), header_tstyle_c)
        col_start += 2
        sheet.col(col_start).width = 256 * 20
        sheet.write_merge(row_start, row_start, col_start, col_start + 1, _('Tax'), header_tstyle_c)
       
        for line in sales_lines:
            row_start +=1
            col_start =0
            sheet.row(row_start).height = 256 * 2
            sheet.write_merge(row_start, row_start, col_start, col_start + 1, line.get('name'), other_tstyle)
            col_start +=2
            sheet.col(col_start).width = 256 * 20
            sheet.write_merge(row_start, row_start, col_start, col_start + 1, currency.symbol +' {:,.2f}'.format(line.get('net')), other_tstyle_r)
            col_start += 2
            sheet.col(col_start).width = 256 * 20
            sheet.write_merge(row_start, row_start, col_start, col_start + 1, currency.symbol +' {:,.2f}'.format(line.get('tax')), other_tstyle_r)

        row_start +=1
        col_start =0  
        sheet.col(col_start).width = 256 * 20
        sheet.write_merge(row_start, row_start, col_start, col_start + 1, _('Purchase'), header_tstyle)
        
        for line in purchase_lines:
            row_start +=1
            col_start =0
            sheet.row(row_start).height = 256 * 2
            sheet.write_merge(row_start, row_start, col_start, col_start + 1, line.get('name'), other_tstyle)
            col_start +=2
            sheet.col(col_start).width = 256 * 20
            sheet.write_merge(row_start, row_start, col_start, col_start + 1, currency.symbol +' {:,.2f}'.format(line.get('net')), other_tstyle_r)
            col_start += 2
            sheet.col(col_start).width = 256 * 20
            sheet.write_merge(row_start, row_start, col_start, col_start + 1, currency.symbol +' {:,.2f}'.format(line.get('tax')), other_tstyle_r)

                
        stream = io.BytesIO()
        workbook.save(stream)

        export_obj = self.env['single.click.download.xls']
        self._cr.execute(""" DELETE FROM single_click_download_xls""")
        res_id = export_obj.create({
                                'file': base64.encodebytes(stream.getvalue()),
                                'fname': "Tax Report.xls"
                                })
        return {
             'type': 'ir.actions.act_url',
             'url': '/web/binary/download_document?model=single.click.download.xls&field=file&id=%s&filename=Tax Report.xls'%(res_id.id),
             'target': 'new',
             }
