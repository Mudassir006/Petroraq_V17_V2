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

import time
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from odoo import api, models, fields,_
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from datetime import datetime
from dateutil.relativedelta import relativedelta


class AccountAgedTrialBalance(models.TransientModel):
    _inherit = 'account.common.partner.report'
    
    def _get_partner_move_lines(self, account_type, partner_ids,
                                date_from, target_move, period_length):
        # This method can receive the context key 'include_nullified_amount' {Boolean}
        # Do an invoice and a payment and unreconcile. The amount will be nullified
        # By default, the partner wouldn't appear in this report.
        # The context key allow it to appear
        # In case of a period_length of 30 days as of 2019-02-08, we want the following periods:
        # Name       Stop         Start
        # 1 - 30   : 2019-02-07 - 2019-01-09
        # 31 - 60  : 2019-01-08 - 2018-12-10
        # 61 - 90  : 2018-12-09 - 2018-11-10
        # 91 - 120 : 2018-11-09 - 2018-10-11
        # +120     : 2018-10-10
        periods = {}
        start = datetime.strptime(str(date_from), "%Y-%m-%d")
        date_from = datetime.strptime(str(date_from), "%Y-%m-%d").date()
        for i in range(5)[::-1]:
            stop = start - relativedelta(days=period_length)
            period_name = str((5-(i+1)) * period_length + 1) + '-' + str((5-i) * period_length)
            period_stop = (start - relativedelta(days=1)).strftime('%Y-%m-%d')
            if i == 0:
                period_name = '+' + str(4 * period_length)
            periods[str(i)] = {
                'name': period_name,
                'stop': period_stop,
                'start': (i!=0 and stop.strftime('%Y-%m-%d') or False),
            }
            start = stop

        res = []
        total = []
        cr = self.env.cr
        user_company = self.env.user.company_id
        user_currency = user_company.currency_id
        company_ids = self._context.get('company_ids') or [user_company.id]
        move_state = ['draft', 'posted']
        date = self._context.get('date') or fields.Date.today()
        company = self.env['res.company'].browse(self._context.get('company_id')) or self.env.company

        if target_move == 'posted':
            move_state = ['posted']
        arg_list = (tuple(move_state), tuple(account_type))

        reconciliation_clause = '(l.reconciled IS FALSE)'
        cr.execute('SELECT debit_move_id, credit_move_id FROM account_partial_reconcile where max_date > %s', (date_from,))
        reconciled_after_date = []
        for row in cr.fetchall():
            reconciled_after_date += [row[0], row[1]]
        if reconciled_after_date:
            reconciliation_clause = '(l.reconciled IS FALSE OR l.id IN %s)'
            arg_list += (tuple(reconciled_after_date),)
        arg_list += (date_from, tuple(company_ids))
        query = '''
            SELECT DISTINCT l.partner_id, UPPER(res_partner.name)
            FROM account_move_line AS l left join res_partner on l.partner_id = res_partner.id, account_account, account_move am
            WHERE (l.account_id = account_account.id)
                AND (l.move_id = am.id)
                AND (am.state IN %s)
                AND (account_account.account_type IN %s)
                AND ''' + reconciliation_clause + '''
                AND (l.date <= %s)
                AND l.company_id IN %s
            ORDER BY UPPER(res_partner.name)'''
        cr.execute(query, arg_list)
        partners = cr.dictfetchall()
        # put a total of 0
        for i in range(7):
            total.append(0)

        # Build a string like (1,2,3) for easy use in SQL query
        if not partner_ids:
            partner_ids = [partner['partner_id'] for partner in partners if partner['partner_id']]
        lines = dict((partner['partner_id'] or False, []) for partner in partners)
        if not partner_ids:
            return [], [], {}

        # This dictionary will store the not due amount of all partners
        undue_amounts = {}
        query = '''SELECT l.id
                FROM account_move_line AS l, account_account, account_move am
                WHERE (l.account_id = account_account.id) AND (l.move_id = am.id)
                    AND (am.state IN %s)
                    AND (account_account.account_type IN %s)
                    AND (COALESCE(l.date_maturity,l.date) >= %s)\
                    AND ((l.partner_id IN %s) OR (l.partner_id IS NULL))
                AND (l.date <= %s)
                AND l.company_id IN %s'''
        cr.execute(query, (tuple(move_state), tuple(account_type), date_from,
                           tuple(partner_ids), date_from, tuple(company_ids)))
        aml_ids = cr.fetchall()
        aml_ids = aml_ids and [x[0] for x in aml_ids] or []
        for line in self.env['account.move.line'].browse(aml_ids):
            partner_id = line.partner_id.id or False
            if partner_id not in undue_amounts:
                undue_amounts[partner_id] = 0.0
            line_amount = line.company_id.currency_id._convert(line.balance,
                                                               user_currency,
                                                               company, date)
            if user_currency.is_zero(line_amount):
                continue
            for partial_line in line.matched_debit_ids:
                if partial_line.max_date <= date_from:
                    line_currency = partial_line.company_id.currency_id
                    line_amount += line_currency._convert(partial_line.amount,
                                                          user_currency,
                                                          company, date)
            for partial_line in line.matched_credit_ids:
                if partial_line.max_date <= date_from:
                    line_currency = partial_line.company_id.currency_id
                    line_amount -= line_currency._convert(partial_line.amount,
                                                          user_currency,
                                                          company, date)
            if not self.env.user.company_id.currency_id.is_zero(line_amount):
                undue_amounts[partner_id] += line_amount
                lines[partner_id].append({
                    'line': line,
                    'amount': line_amount,
                    'period': 6,
                })

        # Use one query per period and store results in history (a list variable)
        # Each history will contain: history[1] = {'<partner_id>': <partner_debit-credit>}
        history = []
        for i in range(5):
            args_list = (tuple(move_state), tuple(account_type), tuple(partner_ids),)
            dates_query = '(COALESCE(l.date_maturity,l.date)'

            if periods[str(i)]['start'] and periods[str(i)]['stop']:
                dates_query += ' BETWEEN %s AND %s)'
                args_list += (periods[str(i)]['start'], periods[str(i)]['stop'])
            elif periods[str(i)]['start']:
                dates_query += ' >= %s)'
                args_list += (periods[str(i)]['start'],)
            else:
                dates_query += ' <= %s)'
                args_list += (periods[str(i)]['stop'],)
            args_list += (date_from, tuple(company_ids))

            query = '''SELECT l.id
                    FROM account_move_line AS l, account_account, account_move am
                    WHERE (l.account_id = account_account.id) AND (l.move_id = am.id)
                        AND (am.state IN %s)
                        AND (account_account.account_type IN %s)
                        AND ((l.partner_id IN %s) OR (l.partner_id IS NULL))
                        AND ''' + dates_query + '''
                    AND (l.date <= %s)
                    AND l.company_id IN %s'''
            cr.execute(query, args_list)
            partners_amount = {}
            aml_ids = cr.fetchall()
            aml_ids = aml_ids and [x[0] for x in aml_ids] or []
            for line in self.env['account.move.line'].browse(aml_ids):
                partner_id = line.partner_id.id or False
                if partner_id not in partners_amount:
                    partners_amount[partner_id] = 0.0
                line_currency_id = line.company_id.currency_id
                line_amount = line_currency_id._convert(line.balance, user_currency, company, date)
                if user_currency.is_zero(line_amount):
                    continue
                for partial_line in line.matched_debit_ids:
                    if partial_line.max_date <= date_from:
                        line_currency_id = partial_line.company_id.currency_id
                        line_amount += line_currency_id._convert(
                            partial_line.amount, user_currency, company, date)
                for partial_line in line.matched_credit_ids:
                    if partial_line.max_date <= date_from:
                        line_currency_id = partial_line.company_id.currency_id
                        line_amount -= line_currency_id._convert(
                            partial_line.amount, user_currency, company, date)
                if not self.env.user.company_id.currency_id.is_zero(line_amount):
                    partners_amount[partner_id] += line_amount
                    lines[partner_id].append({
                        'line': line,
                        'amount': line_amount,
                        'period': i + 1,
                        })
            history.append(partners_amount)

        for partner in partners:
            if partner['partner_id'] is None:
                partner['partner_id'] = False
            at_least_one_amount = False
            values = {}
            undue_amt = 0.0
            if partner['partner_id'] in undue_amounts:  # Making sure this partner actually was found by the query
                undue_amt = undue_amounts[partner['partner_id']]

            total[6] = total[6] + undue_amt
            values['direction'] = undue_amt
            if not float_is_zero(values['direction'], precision_rounding=self.env.user.company_id.currency_id.rounding):
                at_least_one_amount = True

            for i in range(5):
                during = False
                if partner['partner_id'] in history[i]:
                    during = [history[i][partner['partner_id']]]
                # Adding counter
                total[(i)] = total[(i)] + (during and during[0] or 0)
                values[str(i)] = during and during[0] or 0.0
                if not float_is_zero(values[str(i)],
                                     precision_rounding=self.env.user.company_id.currency_id.rounding):
                    at_least_one_amount = True
            values['total'] = sum([values['direction']] + [values[str(i)] for i in range(5)])
            ## Add for total
            total[(i + 1)] += values['total']
            values['partner_id'] = partner['partner_id']
            if partner['partner_id']:
                browsed_partner = self.env['res.partner'].browse(partner['partner_id'])
                values['name'] = browsed_partner.name and len(
                    browsed_partner.name) >= 45 and browsed_partner.name[
                                                    0:40] + '...' or browsed_partner.name
                values['trust'] = browsed_partner.trust
            else:
                values['name'] = _('Unknown Partner')
                values['trust'] = False

            if at_least_one_amount or (self._context.get('include_nullified_amount') and lines[partner['partner_id']]):
                res.append(values)

        return res, total, lines

    def _print_report_excel(self,data):
        self.ensure_one()
        res = {}
        #data = self.check_report()
        #data = data.get('data', {})
        data['form'].update(self.read(['period_length'])[0])
        period_length = data['form']['period_length']
        if period_length <= 0:
            raise UserError(_('You must set a period length greater than 0.'))
        if not data['form']['date_from']:
            raise UserError(_('You must set a start date.'))
        start = data['form']['date_from']
        for i in range(5)[::-1]:
            stop = start - relativedelta(days=period_length - 1)
            res[str(i)] = {
                'name': (i != 0 and (str((5 - (i + 1)) * period_length) + '-' + str((5 - i) * period_length)) or (
                            '+' + str(4 * period_length))),
                'stop': start.strftime('%Y-%m-%d'),
                'start': (i != 0 and stop.strftime('%Y-%m-%d') or False),
            }
            start = stop - relativedelta(days=1)
        data['form'].update(res)


        #self.total_account = []
        
        #default company currency
        currency = self.env.ref('base.main_company').currency_id

        data = self.pre_print_report(data)

        #self.model = self._inherit
        date_from = data['form'].get('date_from', time.strftime('%Y-%m-%d'))
        date_string = datetime.strptime(str(date_from), '%Y-%m-%d')
        date_string = date_string.strftime('%Y-%m-%d')
        target_move = data['form'].get('target_move', 'all')
        partner_ids = data['form']['partner_ids']
        if self.result_selection == 'customer':
            account_type = ['asset_receivable']
        elif self.result_selection == 'supplier':
            account_type = ['liability_payable']
        else:
            account_type = ['asset_receivable', 'liability_payable']


        movelines, total, dummy = self._get_partner_move_lines(account_type, partner_ids, date_string, target_move, period_length)
        
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

        Hedaer_Text = 'Aged Trial Balance'
        sheet = workbook.add_sheet(Hedaer_Text)
        sheet.set_panes_frozen(True)
        sheet.set_horz_split_pos(1)
        sheet.row(0).height = 256 * 3
        sheet.write_merge(0, 0, 0, 8, 'Aged Trial Balance', M_header_tstyle)
        	
		
        row_start, col_start = 2, 0
        sheet.write_merge(row_start,row_start, col_start, col_start + 8,'Aged Partner Balance ', header_tstyle_c)
        row_start +=2
        col_start =2
        sheet.col(col_start).width = 256 * 50
        sheet.write(row_start, col_start, 'Start Date: ', header_tstyle_c)
        col_start +=2
        sheet.col(col_start).width = 256 * 50
        sheet.write(row_start, col_start, 'Period Length (days): ', header_tstyle_c)
        col_start =2
        row_start +=1
        sheet.write(row_start, col_start, date_string,other_tstyle_c)
        col_start +=2
        sheet.write(row_start, col_start, period_length,other_tstyle_c)
        row_start +=2
        col_start =2
        sheet.col(col_start).width = 256 * 30
        sheet.write(row_start, col_start, 'Partners: ', header_tstyle_c)
        col_start +=2
        sheet.col(col_start).width = 256 * 30
        sheet.write(row_start, col_start, 'Target Moves: ', header_tstyle_c)
        row_start +=1
        col_start =2
        if self.result_selection == 'customer':
            sheet.write(row_start, col_start, 'Receivable Accounts ', other_tstyle_c)
        if self.result_selection == 'supplier':
            sheet.write(row_start, col_start, 'Payable Accounts ', other_tstyle_c)
        if self.result_selection == 'customer_supplier':
            sheet.write(row_start, col_start, 'Receivable and Payable Accounts ', other_tstyle_c)
        col_start += 2
        if self.target_move == 'all':
            sheet.write(row_start, col_start, 'All Entries ', other_tstyle_c)
        if self.target_move == 'posted':
            sheet.write(row_start, col_start, 'All Posted Entries ', other_tstyle_c)
			
        row_start +=2
        col_start =0
        sheet.col(col_start).width = 256 * 50
        sheet.write_merge(row_start, row_start, col_start,col_start + 1, 'Partners ', header_tstyle_c)
        col_start += 2
        sheet.col(col_start).width = 256 * 20
        sheet.write(row_start, col_start, 'Not due', header_tstyle_c)
        col_start += 1
        sheet.col(col_start).width = 256 * 20
        sheet.write(row_start, col_start, data.get('form').get('4').get('name'), header_tstyle_c)
        col_start += 1
        sheet.col(col_start).width = 256 * 20
        sheet.write(row_start, col_start, data.get('form').get('3').get('name'), header_tstyle_c)
        col_start += 1
        sheet.col(col_start).width = 256 * 20
        sheet.write(row_start, col_start, data.get('form').get('2').get('name'), header_tstyle_c)
        col_start += 1
        sheet.col(col_start).width = 256 * 20
        sheet.write(row_start, col_start, data.get('form').get('1').get('name'), header_tstyle_c)
        col_start += 1
        sheet.col(col_start).width = 256 * 20
        sheet.write(row_start, col_start, data.get('form').get('0').get('name'), header_tstyle_c)
        col_start += 1
        sheet.col(col_start).width = 256 * 20
        sheet.write(row_start, col_start, 'Total ', header_tstyle_c)
        row_start += 1
        col_start =0
        sheet.write_merge(row_start, row_start, col_start,col_start + 1, 'Account Total', header_tstyle_c)
        col_start += 2
        sheet.col(col_start).width = 256 * 20
        sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(total[6]), header_tstyle_c)
        col_start += 1
        sheet.col(col_start).width = 256 * 20
        sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(total[4]), header_tstyle_c)
        col_start += 1
        sheet.col(col_start).width = 256 * 20
        sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(total[3]), header_tstyle_c)
        col_start += 1
        sheet.col(col_start).width = 256 * 20
        sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(total[2]), header_tstyle_c)
        col_start += 1
        sheet.col(col_start).width = 256 * 20
        sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(total[1]), header_tstyle_c)
        col_start += 1
        sheet.col(col_start).width = 256 * 20
        sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(total[0]), header_tstyle_c)
        col_start += 1
        sheet.col(col_start).width = 256 * 20
        sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(total[5]), header_tstyle_c)
        row_start += 1
		
        for mv in movelines:
            col_start = 0
            sheet.write_merge(row_start, row_start, col_start,col_start + 1, _('%s') % mv.get('name'), other_tstyle_c)
            col_start += 2
            sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(mv.get('direction')),other_tstyle_c)
            col_start += 1
            sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(mv.get('4')),other_tstyle_c)
            col_start += 1
            sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(mv.get('3')),other_tstyle_c)
            col_start += 1
            sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(mv.get('2')),other_tstyle_c)
            col_start += 1
            sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(mv.get('1')),other_tstyle_c)
            col_start += 1
            sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(mv.get('0')),other_tstyle_c)
            col_start += 1
            sheet.write(row_start, col_start, currency.symbol +' {:,.2f}'.format(mv.get('total')),other_tstyle_c)
            row_start += 1

        stream = io.BytesIO()
        workbook.save(stream)

        export_obj = self.env['single.click.download.xls']
        self._cr.execute(""" DELETE FROM single_click_download_xls""")
        res_id = export_obj.create({
                                'file': base64.encodebytes(stream.getvalue()),
                                'fname': "Aged Partner Report.xls"
                                })
        return {
             'type': 'ir.actions.act_url',
             'url': '/web/binary/download_document?model=single.click.download.xls&field=file&id=%s&filename=Aged Partner Report.xls'%(res_id.id),
             'target': 'new',
             }
