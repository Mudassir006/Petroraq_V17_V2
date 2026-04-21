from odoo import api, fields, models
import io
import json
from collections import defaultdict
from odoo.tools import float_round
try:
   from odoo.tools.misc import xlsxwriter
except ImportError:
   import xlsxwriter

MAIN_HEAD = ["main_head"]
MAIN_HEAD_FIELDS = ["assets_main_head", "liability_main_head"]
CATEGORY_FIELDS = ["current_assets_category", "fixed_assets_category", "other_assets_category", "current_liability_category", "liability_non_current_category", "equity_category", "revenue_category", "expense_category"]
CURRENT_ASSET_FIELDS = ["cash_equivalents_subcategory", "banks_subcategory", "accounts_receivable_subcategory", "inventory_subcategory", "prepaid_expenses_subcategory"]
FIXED_ASSET_FIELDS = ["vehicles_subcategory", "furniture_fixture_subcategory", "computer_printers_subcategory", "machinery_equipment_subcategory", "land_buildings_subcategory"]
OTHER_ASSET_FIELDS = ["investment_subcategory", "vat_receivable_subcategory", "suspense_account_subcategory"]

CURRENT_LIABILITY_FIELDS = ["accounts_payable_subcategory", "short_term_loans_subcategory", "other_liabilities_subcategory"]
NON_CURRENT_LIABILITY_FIELDS = ["long_term_loans_subcategory", "lease_obligations_subcategory"]

EQUITY_FIELDS = ["capital_subcategory"]

REVENUE_FIELDS = ["operating_revenue_subcategory"]

EXPENSE_FIELDS = ["cogs_subcategory", "operating_expenses_subcategory", "financial_expenses_subcategory", "other_expenses_subcategory"]


class DynamicBalanceReport(models.Model):
   """Model for getting dynamic purchase report """
   _name = "dynamic.balance.report"
   _description = "Dynamic Balance Report"

   balance_report = fields.Char(string="Balance Report",
                                 help='Name of the report')
   date_from = fields.Date(string="Date From", help='Start date of report')
   date_to = fields.Date(string="Date to", help='End date of report')
   # region [Account Filter Fields]

   main_head = fields.Selection([
       ("assets", "Assets"),
       ("liabilities", "Liabilities"),
       ("equity", "Equity"),
       ("revenue", "Revenue"),
       ("expense", "Expense"),
   ], string="Report Type", required=True, tracking=True)

   # endregion [Account Filter Fields]
   account_id = fields.Many2one('account.account', required=False, string="Account",
                                domain="[('main_head', '=', main_head)]")
   account_name = fields.Char(string='Account Name', related="account_id.name")
   company_id = fields.Many2one('res.company', required=True, string="Company", default=lambda self: self.env.company)
   department_id = fields.Many2one('account.analytic.account', string="Department",
                                   domain="[('analytic_plan_type', '=', 'department')]")
   section_id = fields.Many2one('account.analytic.account', string="Section",
                                domain="[('analytic_plan_type', '=', 'section')]")
   project_id = fields.Many2one('account.analytic.account', string="Project",
                                domain="[('analytic_plan_type', '=', 'project')]")



   @api.model
   def balance_report(self, option):
       """Function for getting datas for requests """
       report_values = self.env['dynamic.balance.report'].search(
           [('id', '=', option[0])])
       data = {
           'model': self,
       }
       # Company
       data.update({
           'company_id': self.env.company.id,
       })
       if report_values.date_from:
           data.update({
               'date_from': report_values.date_from,
           })
       if report_values.date_to:
           data.update({
               'date_to': report_values.date_to,
           })
       if report_values.main_head:
           data.update({
               'main_head': report_values.main_head,
           })

       if report_values.department_id:
           data.update({
               'department_id': report_values.department_id,
           })
       if report_values.section_id:
           data.update({
               'section_id': report_values.section_id,
           })
       if report_values.project_id:
           data.update({
               'project_id': report_values.project_id,
           })
       if report_values.account_id:
           data.update({
               'account_id': report_values.account_id,
           })
       filters = self.get_filter(option)
       lines = self._get_report_values(data).get('BALANCE')
       return {
           'name': "Balance Lines",
           'type': 'ir.actions.client',
           'tag': 's_r',
           'orders': data,
           'filters': filters,
           'report_lines': lines,
       }

   def get_filter(self, option):
       """Function for get data according to order_by filter """
       # data = self.get_filter_data(option)
       filters = {}
       return filters

   def get_filter_data(self, option):
       """ Function for get filter data in report """
       record = self.env['dynamic.balance.report'].search([('id', '=', option[0])])
       default_filters = {}
       filter_dict = {
       }
       filter_dict.update(default_filters)
       return filter_dict

   def generate_balance_report(self, data):
       """
       Generate a hierarchical trial balance report:
       - Grouped by: Main Head → Category → Subcategory → Account
       - Output: List of rows for Excel/table
       """
       report_rows = []
       domain = [
           ("main_head", "=", data.main_head),
           ("main_head", "!=", False),
           ("company_id", "in", [self.env.company.id, self.env.company.parent_id.id]),
       ]
       if data.account_id:
           domain.append(("id", "=", data.account_id.id))

       accounts = self.env['account.account'].sudo().search(domain)

       for account in accounts:
           initial = self.compute_balance(data, account.id, self.env.company, start_date=data.date_from,
                                          end_date=data.date_to, before=True)
           period = self.compute_balance(data, account.id, self.env.company, start_date=data.date_from,
                                         end_date=data.date_to)

           final_ending_debit = initial['debit'] + period['debit']
           final_ending_credit = initial['credit'] + period['credit']

           ending = {
               'debit': final_ending_debit,
               'credit': final_ending_credit,
           }

           final_ending_balance = 0
           final_ending_balance_type = "-"

           if final_ending_debit > final_ending_credit:
               final_ending_balance = final_ending_debit - final_ending_credit
               final_ending_balance_type = "Debit"

           elif final_ending_credit > final_ending_debit:
               final_ending_balance = final_ending_credit - final_ending_debit
               final_ending_balance_type = "Credit"

           elif final_ending_debit == final_ending_credit:
               final_ending_balance = final_ending_debit - final_ending_credit
               final_ending_balance_type = "-"

           account_row = {
               'account_code': account.code,
               'account_name': account.name,
               'account_balance': final_ending_balance,
               'account_balance_type': final_ending_balance_type
           }
           report_rows.append(account_row)
       return report_rows

   def compute_balance(self, data, account_id, company_id, start_date=None, end_date=None, before=False):
       """
       Compute total debit and credit for the given account and period.
       If 'before' is True, include Opening Journal Entry amounts in the totals.
       """
       # Standard domain
       domain = [
           ('account_id', '=', account_id),
           ('company_id', '=', company_id.id),
           ('move_id.state', '=', 'posted'),
       ]

       if before:
           domain.append(('date', '<', start_date))
       else:
           if start_date:
               domain.append(('date', '>=', start_date))
           if end_date:
               domain.append(('date', '<=', end_date))

       # Add base analytic filter
       if data.department_id:
           analytic_distribution_ids = [int(data.department_id.id)]
           domain.append(('analytic_distribution', 'in', analytic_distribution_ids))

       # Search move lines first
       move_lines = self.env['account.move.line'].sudo().search([domain])

       # Apply further filtering based on section/project (custom logic)
       if data.section_id:
           analytic_distribution_ids = [int(data.section_id.id)]
           move_lines = move_lines.filtered(lambda ml: ml.analytic_distribution in analytic_distribution_ids)

       if data.project_id:
           analytic_distribution_ids = [int(data.project_id.id)]
           move_lines = move_lines.filtered(lambda ml: ml.analytic_distribution in analytic_distribution_ids)

       # Compute totals from move_lines instead of read_group
       debit = float_round(sum(ml.debit for ml in move_lines), 2) if move_lines else 0.0
       credit = float_round(sum(ml.credit for ml in move_lines), 2) if move_lines else 0.0

       # Add OJE only if 'before' is True
       if before and start_date:
           oje_company_ids = [company_id.id]
           if company_id.parent_id:
               oje_company_ids.append(company_id.parent_id.id)

           oje_domain = [
               ('account_id', '=', account_id),
               ('company_id', 'in', oje_company_ids),
               ('date', '<', start_date),
               ('move_id.ref', '=', 'Opening Journal Entry'),
           ]
           oje_result = self.env['account.move.line'].sudo().read_group(oje_domain, ['debit', 'credit'], [])
           if oje_result:
               debit += float_round(oje_result[0].get('debit', 0.0), 2)
               credit += float_round(oje_result[0].get('credit', 0.0), 2)

       return {
           'debit': debit,
           'credit': credit,
       }

   # def compute_balance(self, data, account_id, company_id, start_date=None, end_date=None, before=False):
   #     """
   #     Compute total debit and credit for the given account and period.
   #     If 'before' is True, include Opening Journal Entry amounts in the totals.
   #     """
   #     analytic_distribution_ids = []
   #
   #     # Standard domain
   #     domain = [
   #         ('account_id', '=', account_id),
   #         ('company_id', '=', company_id.id),
   #         ('move_id.state', '=', 'posted'),
   #     ]
   #
   #     if before:
   #         domain.append(('date', '<', start_date))
   #     else:
   #         if start_date:
   #             domain.append(('date', '>=', start_date))
   #         if end_date:
   #             domain.append(('date', '<=', end_date))
   #
   #     # Add analytic filters if available
   #     if data.department_id:
   #         analytic_distribution_ids.append(int(data.department_id.id))
   #     if data.section_id:
   #         analytic_distribution_ids.append(int(data.section_id.id))
   #     if data.project_id:
   #         analytic_distribution_ids.append(int(data.project_id.id))
   #     if analytic_distribution_ids:
   #         domain.append(('analytic_distribution', 'in', analytic_distribution_ids))
   #
   #     # Compute main result
   #     result = self.env['account.move.line'].sudo().read_group(domain, ['debit', 'credit'], [])
   #     debit = float_round(result[0].get('debit', 0.0), 2) if result else 0.0
   #     credit = float_round(result[0].get('credit', 0.0), 2) if result else 0.0
   #
   #     # Add OJE only if 'before' is True
   #     if before and start_date:
   #         oje_company_ids = [company_id.id]
   #         if company_id.parent_id:
   #             oje_company_ids.append(company_id.parent_id.id)
   #
   #         oje_domain = [
   #             ('account_id', '=', account_id),
   #             ('company_id', 'in', oje_company_ids),
   #             ('date', '<', start_date),
   #             ('move_id.ref', '=', 'Opening Journal Entry'),
   #         ]
   #         oje_result = self.env['account.move.line'].sudo().read_group(oje_domain, ['debit', 'credit'], [])
   #         if oje_result:
   #             debit += float_round(oje_result[0].get('debit', 0.0), 2)
   #             credit += float_round(oje_result[0].get('credit', 0.0), 2)
   #
   #     return {
   #         'debit': debit,
   #         'credit': credit,
   #     }

   def _get_report_values(self, data):
       """ Get report values based on the provided data. """
       docs = data['model']
       report_res = self.generate_balance_report(data)
       return {
           'doc_ids': self.ids,
           'docs': docs,
           'BALANCE': report_res,
       }
