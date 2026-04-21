# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools.misc import get_lang
from odoo.exceptions import ValidationError
import json
import re


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


class AccountCommonReport(models.TransientModel):
    _name = "account.common.report"
    _description = "Account Common Report"

    # region [Default Methods]

    @api.model
    def _default_project_analytic_plans(self):
        project_plan_id = self.env.ref("analytic.analytic_plan_projects")
        if project_plan_id:
            return project_plan_id

    @api.model
    def _default_division_analytic_plans(self):
        division_plan_id = self.env.ref("pr_account.pr_account_analytic_plan_division")
        if division_plan_id:
            return division_plan_id

    @api.model
    def _default_department_analytic_plans(self):
        department_plan_id = self.env.ref("pr_account.pr_account_analytic_plan_department")
        if department_plan_id:
            return department_plan_id

    # endregion [Default Methods]

    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=False, default=lambda self: self.env.company)
    journal_ids = fields.Many2many(
        comodel_name='account.journal',
        string='Journals',
        required=False,
        domain="[('company_id', '=', company_id)]",
    )
    account_ids = fields.Many2many('account.account', string='Accounts')
    account_ids_domain = fields.Char(string='Accounts Domain')
    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date')
    target_move = fields.Selection([('posted', 'All Posted Entries'),
                                    ('all', 'All Entries'),
                                    ], string='Target Moves', required=True, default='posted')
    # -- Analytic Fields -- #
    asset_id = fields.Many2one('asset.detail', string="Asset", domain="[('company_id', '=', company_id)]")
    project_plan_id = fields.Many2one('account.analytic.plan', string="Project Plan",
                                      default=_default_project_analytic_plans)
    division_plan_id = fields.Many2one('account.analytic.plan', string="Division Plan",
                                       default=_default_division_analytic_plans)
    department_plan_id = fields.Many2one('account.analytic.plan', string="Department Plan",
                                         default=_default_department_analytic_plans)
    project_id = fields.Many2one('account.analytic.account', string="Project",
                                 domain="[('plan_id', '=', project_plan_id)]")
    division_id = fields.Many2one('account.analytic.account', string="Division",
                                  domain="[('plan_id', '=', division_plan_id)]")
    department_id = fields.Many2one('account.analytic.account', string="Department",
                                    domain="[('plan_id', '=', department_plan_id)]")

    # region [Account Filter Fields]

    main_head = fields.Selection([
        ("assets", "Assets"),
        ("liabilities", "Liabilities"),
        ("equity", "Equity"),
        ("revenue", "Revenue"),
        ("expense", "Expense"),
    ], string="Main Head", required=False, tracking=True)
    assets_main_head = fields.Selection([
        ("asset_current", "Current Assets"),
        ("asset_fixed", "Fixed Assets"),
        ("asset_non_current", "Other Assets"),
    ], string="Assets Main Head", tracking=True)
    liability_main_head = fields.Selection([
        ("liability_current", "Current Liabilities"),
        ("liability_non_current", "Long-Term Liabilities"),
    ], string="Liabilities Main Head", tracking=True)
    # -- Category -- #
    current_assets_category = fields.Selection([
        ("cash_equivalents", "Cash & Equivalents"),
        ("banks", "Banks"),
        ("account_receivable", "Account Receivable"),
        ("inventory", "Inventory"),
        ("prepaid_expenses", "Prepaid Expenses"),
    ], string="Current Assets Category", tracking=True)
    fixed_assets_category = fields.Selection([
        ("vehicles", "Vehicles"),
        ("furniture_fixture", "Furniture & Fixture"),
        ("computer_printers", "Computer & Printers"),
        ("machinery_equipment", "Machinery & Equipment"),
        ("land_buildings", "Land & Buildings"),
    ], string="Fixed Assets Category", tracking=True)
    other_assets_category = fields.Selection([
        ("investment", "Investment"),
        ("vat_receivable", "VAT Receivable"),
        ("suspense_account", "Suspense Account"),
    ], string="Other Assets Category", tracking=True)
    current_liability_category = fields.Selection([
        ("accounts_payable", "Accounts Payable"),
        ("short_term_loans", "Short-Term Loans"),
        ("other_liabilities", "Other Liabilities"),
    ], string="Current Liabilities Category", tracking=True)
    liability_non_current_category = fields.Selection([
        ("long_term_loans", "Long-Term Loans"),
        ("lease_obligations", "Lease Obligations"),
    ], string="Non Current Liabilities Category", tracking=True)
    equity_category = fields.Selection([
        ("capital", "Capital"),
    ], string="Equity Category", tracking=True)
    revenue_category = fields.Selection([
        ("operating_revenue", "Operating Revenue"),
    ], string="Revenue Category", tracking=True)
    expense_category = fields.Selection([
        ("cogs", "Cost of Goods Sold - COGS"),
        ("operating_expenses", "Operating Expenses"),
        ("financial_expenses", "Financial Expenses"),
        ("other_expenses", "Other Expenses"),
    ], string="Expense Category", tracking=True)
    # -- Sub Category -- #
    cash_equivalents_subcategory = fields.Selection([
        ("petty_cash", "Petty Cash"),
    ], string="Cash & Equivalents Sub-Category", tracking=True)
    banks_subcategory = fields.Selection([
        ("banks", "Banks"),
    ], string="Banks Sub-Category", tracking=True)
    accounts_receivable_subcategory = fields.Selection([
        ("employee_advances", "Employee Advances"),
        ("customers", "Customers"),
        ("retention_receivable", "Retention-Receivable"),
    ], string="Accounts Receivable Sub-Category", tracking=True)
    inventory_subcategory = fields.Selection([
        ("raw_materials", "Raw Materials"),
        ("work_in_progress_wip", "Work in Progress-WIP"),
        ("finished_goods", "Finished Goods"),
    ], string="Inventory Sub-Category", tracking=True)
    prepaid_expenses_subcategory = fields.Selection([
        ("prepaid_rent", "Prepaid Rent"),
        ("insurance", "Insurance"),
        ("subscriptions", "Subscriptions"),
    ], string="Prepaid Expenses Sub-Category", tracking=True)
    vehicles_subcategory = fields.Selection([
        ("cars", "Cars"),
    ], string="vehicles Sub-Category", tracking=True)
    furniture_fixture_subcategory = fields.Selection([
        ("furniture", "Furniture"),
    ], string="Furniture & Fixture Sub-Category", tracking=True)
    computer_printers_subcategory = fields.Selection([
        ("it_products", "IT Products"),
    ], string="Computer & Printers Sub-Category", tracking=True)
    machinery_equipment_subcategory = fields.Selection([
        ("machinery", "Machinery"),
    ], string="Machinery & Equipment Sub-Category", tracking=True)
    land_buildings_subcategory = fields.Selection([
        ("buildings", "Buildings"),
    ], string="Land & Buildings Sub-Category", tracking=True)
    investment_subcategory = fields.Selection([
        ("short_terms", "Short Terms"),
        ("long_terms", "Long Terms"),
    ], string="Investment Sub-Category", tracking=True)
    vat_receivable_subcategory = fields.Selection([
        ("vat_receivable", "VAT Receivable"),
    ], string="VAT Receivable Sub-Category", tracking=True)
    suspense_account_subcategory = fields.Selection([
        ("suspense_account", "Suspense Account"),
    ], string="Suspense Account Sub-Category", tracking=True)
    accounts_payable_subcategory = fields.Selection([
        ("suppliers", "Suppliers"),
        ("accrued_expenses", "Accrued Expenses"),
    ], string="Accounts Payable Sub-Category", tracking=True)
    short_term_loans_subcategory = fields.Selection([
        ("bank_finance", "Bank Finance"),
    ], string="Short Term Loans Sub-Category", tracking=True)
    other_liabilities_subcategory = fields.Selection([
        ("vat_payable", "VAT Payable"),
    ], string="Other Liabilities Sub-Category", tracking=True)
    long_term_loans_subcategory = fields.Selection([
        ("loans", "Loans"),
    ], string="Long Term Loans Sub-Category", tracking=True)
    lease_obligations_subcategory = fields.Selection([
        ("lease", "Lease"),
    ], string="Lease Obligations Sub-Category", tracking=True)
    capital_subcategory = fields.Selection([
        ("petroraq", "Petroraq"),
    ], string="Capital Sub-Category", tracking=True)
    operating_revenue_subcategory = fields.Selection([
        ("product_sales", "Product Sales"),
        ("service_revenue", "Service Revenue"),
        ("other_revenue", "Other Revenue"),
    ], string="Operating Revenue Sub-Category", tracking=True)
    cogs_subcategory = fields.Selection([
        ("direct_raw_materials", "Direct Raw Materials"),
        ("direct_labor", "Direct Labor (Production Staff)"),
    ], string="COGS Sub-Category", tracking=True)
    operating_expenses_subcategory = fields.Selection([
        ("salaries_wages", "Salaries & Wages"),
        ("rent_utilities", "Rent & Utilities"),
        ("marketing", "Marketing"),
    ], string="operating_expenses Sub-Category", tracking=True)
    financial_expenses_subcategory = fields.Selection([
        ("interest_expense", "Interest Expense"),
    ], string="Financial Expenses Sub-Category", tracking=True)
    other_expenses_subcategory = fields.Selection([
        ("general_administrative_expenses", "General Administrative Expenses"),
    ], string="Other Expenses Sub-Category", tracking=True)

    # endregion [Account Filter Fields]

    # region [Constrains]

    @api.constrains("company_id")
    def _check_company(self):
        for rec in self:
            if rec.company_id and rec.company_id.id != self.env.company.id:
                raise ValidationError("You Should Select The Current Company !!, Please Check")

    # endregion [Constrains

    # @api.onchange('company_id')
    # def _onchange_company_id(self):
    #     if self.company_id:
    #         self.journal_ids = self.env['account.journal'].search(
    #             [('company_id', '=', self.company_id.id)])
    #     else:
    #         self.journal_ids = self.env['account.journal'].search([])

    # region [Onchange Methods]

    @api.onchange("main_head")
    def _onchange_main_head(self):
        ALL_FIELD_GROUPS = (
                MAIN_HEAD_FIELDS +
                CATEGORY_FIELDS +
                CURRENT_ASSET_FIELDS +
                FIXED_ASSET_FIELDS +
                OTHER_ASSET_FIELDS +
                CURRENT_LIABILITY_FIELDS +
                NON_CURRENT_LIABILITY_FIELDS +
                EQUITY_FIELDS +
                REVENUE_FIELDS +
                EXPENSE_FIELDS
        )
        for account in self:
            if account.main_head:
                for field in ALL_FIELD_GROUPS:
                    setattr(account, field, False)
            self.account_ids = False

    @api.onchange("assets_main_head", "liability_main_head")
    def _onchange_assets_liability_main_head(self):
        ALL_FIELD_GROUPS = (
                CATEGORY_FIELDS +
                CURRENT_ASSET_FIELDS +
                FIXED_ASSET_FIELDS +
                OTHER_ASSET_FIELDS +
                CURRENT_LIABILITY_FIELDS +
                NON_CURRENT_LIABILITY_FIELDS +
                EQUITY_FIELDS +
                REVENUE_FIELDS +
                EXPENSE_FIELDS
        )
        for account in self:
            if account.assets_main_head or account.liability_main_head:
                for field in ALL_FIELD_GROUPS:
                    setattr(account, field, False)
            self.account_ids = False

    @api.onchange("current_assets_category", "fixed_assets_category", "other_assets_category",
                  "current_liability_category", "liability_non_current_category", "equity_category",
                  "revenue_category", "expense_category")
    def _onchange_category(self):
        ALL_FIELD_GROUPS = (
                CURRENT_ASSET_FIELDS +
                FIXED_ASSET_FIELDS +
                OTHER_ASSET_FIELDS +
                CURRENT_LIABILITY_FIELDS +
                NON_CURRENT_LIABILITY_FIELDS +
                EQUITY_FIELDS +
                REVENUE_FIELDS +
                EXPENSE_FIELDS
        )
        for account in self:
            if (account.assets_main_head or account.liability_main_head or account.current_assets_category or account.fixed_assets_category\
                    or account.other_assets_category or account.current_liability_category or account.liability_non_current_category or account.equity_category
                    or account.revenue_category or account.expense_category):
                for field in ALL_FIELD_GROUPS:
                        setattr(account, field, False)
            self.account_ids = False

    @api.onchange("main_head", "assets_main_head", "liability_main_head", "current_assets_category", "fixed_assets_category", "other_assets_category",
                  "current_liability_category", "liability_non_current_category", "equity_category",
                  "revenue_category", "expense_category", "cash_equivalents_subcategory",
                  "banks_subcategory", "accounts_receivable_subcategory", "inventory_subcategory", "prepaid_expenses_subcategory",
                  "vehicles_subcategory", "furniture_fixture_subcategory", "computer_printers_subcategory", "machinery_equipment_subcategory",
                  "land_buildings_subcategory", "investment_subcategory", "vat_receivable_subcategory", "suspense_account_subcategory", "accounts_payable_subcategory",
                  "short_term_loans_subcategory", "other_liabilities_subcategory", "long_term_loans_subcategory", "lease_obligations_subcategory",
                  "capital_subcategory", "operating_revenue_subcategory", "cogs_subcategory", "operating_expenses_subcategory",
                  "financial_expenses_subcategory", "other_expenses_subcategory")
    def prepare_account_ids_domain(self):
        self.ensure_one()
        account_ids_domain = []
        ALL_FIELD_GROUPS = (
                MAIN_HEAD +
                MAIN_HEAD_FIELDS +
                CATEGORY_FIELDS +
                CURRENT_ASSET_FIELDS +
                FIXED_ASSET_FIELDS +
                OTHER_ASSET_FIELDS +
                CURRENT_LIABILITY_FIELDS +
                NON_CURRENT_LIABILITY_FIELDS +
                EQUITY_FIELDS +
                REVENUE_FIELDS +
                EXPENSE_FIELDS
        )
        for field in ALL_FIELD_GROUPS:
            value = getattr(self, field, False)
            if value:
                account_ids_domain.append((field, '=', value))
        if account_ids_domain:
            account_ids = self.env["account.account"].search(account_ids_domain)
            if account_ids:
                self.account_ids_domain = json.dumps([('id', 'in', account_ids.ids)])
            else:
                self.account_ids_domain = "[]"
        else:
            self.account_ids_domain = "[]"

        # endregion [Onchange Methods]

    def _build_contexts(self, data):
        result = {}
        result['journal_ids'] = 'journal_ids' in data['form'] and data['form']['journal_ids'] or False
        result['account_ids'] = 'account_ids' in data['form'] and data['form']['account_ids'] or False
        result['state'] = 'target_move' in data['form'] and data['form']['target_move'] or ''
        result['date_from'] = data['form']['date_from'] or False
        result['date_to'] = data['form']['date_to'] or False
        result['strict_range'] = True if result['date_from'] else False
        result['company_id'] = data['form']['company_id'][0] or False
        # -- Analytic Fields -- #
        result['asset_id'] = data['form']['asset_id'][0] if data['form'].get("asset_id") else False
        result['project_id'] = data['form']['project_id'][0] if data['form'].get("project_id") else False
        result['division_id'] = data['form']['division_id'][0] if data['form'].get("division_id") else False
        result['department_id'] = data['form']['department_id'][0] if data['form'].get("department_id") else False
        return result

    def _print_report(self, data):
        raise NotImplementedError()

    def check_report(self):
        self.ensure_one()
        self.prepare_account_ids()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        # data['form'] = self.read(['date_from', 'date_to', 'journal_ids', 'target_move', 'company_id'])[0]
        data['form'] = self.read(['date_from', 'date_to', 'journal_ids', 'account_ids', 'target_move', 'company_id', 'asset_id', 'project_id', 'division_id', 'department_id'])[0]
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=get_lang(self.env).code)
        return self.with_context(discard_logo_check=True)._print_report(data)

    def prepare_account_ids(self):
        self.ensure_one()

        if not self.account_ids:
            account_ids_domain = []
            analytic_domain = [("company_id", "=", self.company_id.id), ('display_type', 'not in', ('line_section', 'line_note')), ('parent_state', '=', 'posted')]
            MOVELINE = self.env["account.move.line"]
            analytic_fields_accounts = []
            filters_accounts = False
            if self.asset_id:
                analytic_domain += [('asset_id', '=', self.asset_id.id)]

            if self.project_id:
                analytic_fields_accounts.append(self.project_id.id)

            if self.division_id:
                analytic_fields_accounts.append(self.division_id.id)

            if self.department_id:
                analytic_fields_accounts.append(self.department_id.id)

            if analytic_fields_accounts:
                analytic_domain.append(('analytic_distribution', 'in', analytic_fields_accounts))

            # if domain:
            #     move_lines = self.env["account.move.line"]._query_get(domain=domain)
            if analytic_domain:
                move_line_ids = MOVELINE.search(analytic_domain)
                if move_line_ids:
                    filters_accounts = move_line_ids.mapped("account_id")
            ALL_FIELD_GROUPS = (
                    MAIN_HEAD +
                    MAIN_HEAD_FIELDS +
                    CATEGORY_FIELDS +
                    CURRENT_ASSET_FIELDS +
                    FIXED_ASSET_FIELDS +
                    OTHER_ASSET_FIELDS +
                    CURRENT_LIABILITY_FIELDS +
                    NON_CURRENT_LIABILITY_FIELDS +
                    EQUITY_FIELDS +
                    REVENUE_FIELDS +
                    EXPENSE_FIELDS
            )
            for field in ALL_FIELD_GROUPS:
                value = getattr(self, field, False)
                if value:
                    account_ids_domain.append((field, '=', value))
            if account_ids_domain:
                if filters_accounts:
                    account_ids_domain.append(("id", 'in', filters_accounts.ids))
                account_ids = self.env["account.account"].search(account_ids_domain)
                if account_ids:
                    self.account_ids = account_ids
            else:
                if filters_accounts:
                    account_ids = self.env["account.account"].browse(filters_accounts.ids)
                    self.account_ids = account_ids

    def format_param(self, param):
        if isinstance(param, (tuple, list)):
            return '(' + ', '.join(f"'{str(p)}'" for p in param) + ')'
        elif isinstance(param, str):
            return f"'{param}'"
        elif param is None:
            return 'NULL'
        else:
            return str(param)

    def build_sql(self, query, params):
        parts = query.split('%s')
        final = ''
        for i in range(len(parts) - 1):
            final += parts[i] + self.format_param(params[i])
        final += parts[-1]

        final_query = self._replace_analytic_params(final)
        final_query_after_clean_where = self.clean_where_clause(final_query)
        return final_query_after_clean_where

    def _replace_analytic_params(self, sql):
        match = re.search(r'\?\&\s*\((.*?)\)', sql)

        if match:
            values_str = match.group(1)  # e.g., '5, 6'
            values = [v.strip() for v in values_str.split(',')]  # ['5', '6']
            new_list = []
            for v in values:
                number = re.search(r'\d+', v).group()
                new_list.append(number)

            # Step 2: Build the replacement string
            combined_key = ','.join(new_list)  # Combine the values into a single string '5,6,7'
            array_str = f"?& array['{combined_key}']"

            # Step 3: Replace the old string with the new one
            new_sql = re.sub(r'\?\&\s*\(.*?\)', array_str, sql)
            final_query = self.clean_sql_query(new_sql)
            return final_query
        return sql

    def clean_sql_query(self, sql):
        # 1. Fix over-quoted array values: array['''5''', '''6'''] → array['5', '6']
        sql = re.sub(r"array\[\s*'''(.*?)'''\s*(?:,\s*'''(.*?)''')*\s*\]",
                     lambda m: "array[" + ", ".join(
                         f"'{p.strip()}'" for p in re.findall(r"'''(.*?)'''", m.group(0))) + "]",
                     sql)

        # 2. Optional: Clean up overly quoted identifiers: "l"."column" → l.column
        sql = re.sub(r'"(\w+)"\."(\w+)"', r'\1.\2', sql)

        # 3. Remove any excessive spacing around keywords
        sql = re.sub(r'\s+', ' ', sql).strip()
        return sql

    def clean_where_clause(self, query):
        # Find the WHERE clause
        where_match = re.search(r"WHERE(.*?)GROUP BY", query, re.DOTALL)

        if where_match:
            where_clause = where_match.group(1).strip()

            # Step 1: Remove extra spaces between conditions
            where_clause = re.sub(r"\s{2,}", " ", where_clause)

            # Step 2: Split conditions by 'AND' and clean up each condition
            conditions = where_clause.split("AND")

            # Use a dictionary to store the conditions by the column name to check for duplicates
            column_conditions = {}
            cleaned_conditions = []

            for condition in conditions:
                condition = condition.strip()

                # Extract the column from the condition (before the =, IN, or ?& operator)
                column_match = re.match(r"([a-zA-Z0-9_\.]+)\s*(=|IN|!=|NOT IN|\?\&|IS NULL)\s*", condition)

                if column_match:
                    column = column_match.group(1)

                    # If the column already has a condition, skip it (duplicate conditions)
                    if column not in column_conditions:
                        column_conditions[column] = condition
                        cleaned_conditions.append(condition)
                else:
                    # If we cannot match a condition (e.g., it doesn't follow column = value format), just add it
                    cleaned_conditions.append(condition)

            # Step 3: Join the cleaned conditions back into a WHERE clause
            cleaned_where_clause = " AND ".join(cleaned_conditions)

            # Step 4: Replace the old WHERE clause with the cleaned WHERE clause in the query
            cleaned_query = query.replace(where_match.group(1), cleaned_where_clause)
            return cleaned_query
        else:
            return query

    def remove_all_redundant_parentheses(self, query):
        # Step 1: Remove redundant opening parentheses
        while re.search(r"\(\(", query):  # Continue while we find double opening parentheses
            query = re.sub(r"\(\(", "(", query)  # Replace the first occurrence of ((

        # Step 2: Remove redundant closing parentheses
        while re.search(r"\)\)", query):  # Continue while we find double closing parentheses
            query = re.sub(r"\)\)", ")", query)  # Replace the first occurrence of )) with )

        # Step 3: Handle case where parentheses are at the start or end unnecessarily
        # Remove opening parentheses from the beginning
        while query.startswith('(') and query.endswith(')'):
            query = query[1:-1]  # Remove the first and last character (which are parentheses)


        final_query = self.clean_query_with_or_condition(query)
        final_query = final_query.replace("))", ")")
        return final_query

    def clean_query_with_or_condition(self, query):
        # Step 1: Remove unnecessary parentheses from conditions
        query = re.sub(r'([^\(]+)\s+OR\s+([^\)]+)', r'(\1 OR \2)', query)

        # Step 2: Remove unnecessary parentheses from the conditions
        query = re.sub(r"\(\s*([^\(\)]+)\s*\)", r"\1", query)

        # Return the cleaned query
        return query

    def _filter_analytic_data(self, data_rows):
        analytic_distribution = []
        new_data_rows = []
        if self.project_id:
            analytic_distribution.append(str(self.project_id.id))
        if self.division_id:
            analytic_distribution.append(str(self.division_id.id))
        if self.department_id:
            analytic_distribution.append(str(self.department_id.id))
        if analytic_distribution:
            new_list = []
            for v in analytic_distribution:
                number = re.search(r'\d+', v).group()
                new_list.append(number)

            # Step 2: Build the replacement string
            combined_key = ','.join(new_list)  # Combine the values into a single string '5,6,7'
            for row in data_rows:
                analytic_distribution_dict = row.get("analytic_distribution")
                if analytic_distribution_dict:
                    for key, value in analytic_distribution_dict.items():
                        if combined_key in key:
                            new_data_rows.append(row)
        if new_data_rows:
            return new_data_rows
        else:
            return data_rows

            # Step 3: Replace the old string with the new one
