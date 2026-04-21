# -*- coding: utf-8 -*-

from odoo import models, fields, api, http
from odoo.http import request
import io
import xlsxwriter
import base64
from datetime import datetime

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    def action_export_grouped_ledger(self):
        """Export grouped ledger entries as shown in the view"""
        # Get the current domain and context from the view
        domain = self.env.context.get('domain', [])
        context = self.env.context.copy()
        
        # Get grouped data
        grouped_data = self._get_grouped_ledger_data(domain, context)
        
        # Create Excel file
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Grouped Ledger')
        
        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D3D3D3',
            'border': 1
        })
        currency_format = workbook.add_format({
            'num_format': '#,##0.00'
        })
        date_format = workbook.add_format({
            'num_format': 'dd/mm/yyyy'
        })
        
        # Write headers
        headers = [
            'Date', 'Journal Entry', 'Reference', 'Partner', 
            'Account', 'Description', 'Debit', 'Credit', 'Balance'
        ]
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Set column widths
        worksheet.set_column('A:A', 12)  # Date
        worksheet.set_column('B:B', 25)  # Journal Entry
        worksheet.set_column('C:C', 20)  # Reference
        worksheet.set_column('D:D', 25)  # Partner
        worksheet.set_column('E:E', 15)  # Account
        worksheet.set_column('F:F', 40)  # Description
        worksheet.set_column('G:I', 15)  # Amounts
        
        # Write grouped data
        row = 1
        for entry in grouped_data:
            worksheet.write(row, 0, entry['date'], date_format)
            worksheet.write(row, 1, entry['journal_entry'])
            worksheet.write(row, 2, entry['reference'])
            worksheet.write(row, 3, entry['partner'])
            worksheet.write(row, 4, entry['account'])
            worksheet.write(row, 5, entry['description'])
            worksheet.write(row, 6, entry['debit'], currency_format)
            worksheet.write(row, 7, entry['credit'], currency_format)
            worksheet.write(row, 8, entry['balance'], currency_format)
            row += 1
        
        # Add totals row
        if grouped_data:
            worksheet.write(row, 0, 'TOTALS', header_format)
            worksheet.write(row, 6, sum(entry['debit'] for entry in grouped_data), currency_format)
            worksheet.write(row, 7, sum(entry['credit'] for entry in grouped_data), currency_format)
            worksheet.write(row, 8, sum(entry['balance'] for entry in grouped_data), currency_format)
        
        workbook.close()
        output.seek(0)
        
        # Create attachment
        filename = f"Grouped_Ledger_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(output.getvalue()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': 'account.move.line',
            'res_id': 0,
        })
        
        # Return download action
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }
    
    def _get_grouped_ledger_data(self, domain, context):
        """Get grouped ledger data as shown in the view"""
        # Apply the same filters as the view
        move_lines = self.search(domain)
        
        # Group by journal entry
        grouped_entries = {}
        for line in move_lines:
            move_id = line.move_id
            if move_id.id not in grouped_entries:
                grouped_entries[move_id.id] = {
                    'date': move_id.date,
                    'journal_entry': move_id.name,
                    'reference': move_id.ref or '',
                    'partner': move_id.partner_id.name if move_id.partner_id else '',
                    'account': '',
                    'description': '',
                    'debit': 0.0,
                    'credit': 0.0,
                    'balance': 0.0,
                    'lines': []
                }
            
            # Add move line details
            grouped_entries[move_id.id]['lines'].append({
                'account': line.account_id.code + ' - ' + line.account_id.name,
                'description': line.name,
                'debit': line.debit,
                'credit': line.credit,
                'balance': line.balance,
                'partner': line.partner_id.name if line.partner_id else ''
            })
        
        # Create summary entries (one per journal entry)
        result = []
        for move_id, entry in grouped_entries.items():
            # Calculate totals
            total_debit = sum(line['debit'] for line in entry['lines'])
            total_credit = sum(line['credit'] for line in entry['lines'])
            total_balance = sum(line['balance'] for line in entry['lines'])
            
            # Create summary entry
            result.append({
                'date': entry['date'],
                'journal_entry': entry['journal_entry'],
                'reference': entry['reference'],
                'partner': entry['partner'],
                'account': f"({len(entry['lines'])} lines)",
                'description': f"Journal Entry Summary - {len(entry['lines'])} move lines",
                'debit': total_debit,
                'credit': total_credit,
                'balance': total_balance
            })
        
        # Sort by date and journal entry
        result.sort(key=lambda x: (x['date'], x['journal_entry']))
        
        return result