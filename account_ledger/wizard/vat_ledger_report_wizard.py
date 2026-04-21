# -*- coding: utf-8 -*-

from odoo import api, models, fields
from datetime import datetime, date
import json
from odoo.exceptions import UserError

MAIN_HEAD = ["main_head"]
MAIN_HEAD_FIELDS = ["assets_main_head", "liability_main_head"]
CATEGORY_FIELDS = ["current_assets_category", "fixed_assets_category", "other_assets_category",
                   "current_liability_category", "liability_non_current_category", "equity_category",
                   "revenue_category", "expense_category"]
CURRENT_ASSET_FIELDS = ["cash_equivalents_subcategory", "banks_subcategory", "accounts_receivable_subcategory",
                        "inventory_subcategory", "prepaid_expenses_subcategory"]
FIXED_ASSET_FIELDS = ["vehicles_subcategory", "furniture_fixture_subcategory", "computer_printers_subcategory",
                      "machinery_equipment_subcategory", "land_buildings_subcategory"]
OTHER_ASSET_FIELDS = ["investment_subcategory", "vat_receivable_subcategory", "suspense_account_subcategory"]

CURRENT_LIABILITY_FIELDS = ["accounts_payable_subcategory", "short_term_loans_subcategory",
                            "other_liabilities_subcategory"]
NON_CURRENT_LIABILITY_FIELDS = ["long_term_loans_subcategory", "lease_obligations_subcategory"]

EQUITY_FIELDS = ["capital_subcategory"]

REVENUE_FIELDS = ["operating_revenue_subcategory"]

EXPENSE_FIELDS = ["cogs_subcategory", "operating_expenses_subcategory", "financial_expenses_subcategory",
                  "other_expenses_subcategory"]


class VatLedgerReport(models.TransientModel):
    _name = 'vat.ledger.report.wizard'

    # region [Default Methods]

    # endregion [Default Methods]

    date_start = fields.Date(string="Start Date", required=True, default=date(2025, 1, 1))
    date_end = fields.Date(string="End Date", required=True, default=fields.Date.today)
    account_id = fields.Many2one('account.account', required=False, string="Account")
    account_id_domain = fields.Char(compute="_compute_account_id_domain")
    account_ids = fields.Many2many('account.account', required=True, string="Accounts")
    account_name = fields.Char(string='Account Name', related="account_id.name")
    company_id = fields.Many2one('res.company', required=True, string="Company", default=lambda self: self.env.company)
    department_id = fields.Many2one('account.analytic.account', string="Department",
                                    domain="[('analytic_plan_type', '=', 'department')]")
    section_id = fields.Many2one('account.analytic.account', string="Section",
                                 domain="[('analytic_plan_type', '=', 'section')]")
    project_id = fields.Many2one('account.analytic.account', string="Project",
                                 domain="[('analytic_plan_type', '=', 'project')]")
    employee_id = fields.Many2one('account.analytic.account', string="Employee",
                                  domain="[('analytic_plan_type', '=', 'employee')]")
    asset_id = fields.Many2one('account.analytic.account', string="Asset",
                               domain="[('analytic_plan_type', '=', 'asset')]")
    vat_option = fields.Selection(
        [("including_vat", "Including VAT"), ("excluding_vat", "Excluding VAT"), ("all", "All")], string="VAT Options",
        default="including_vat", required=True)
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

    # Inline summary fields
    total_debit = fields.Float("Total Debit", readonly=True)
    total_credit = fields.Float("Total Credit", readonly=True)
    vat_total = fields.Float("Total VAT", readonly=True)
    transaction_count = fields.Integer("Transaction Count", readonly=True)

    summary_html = fields.Html("Account Balances Summary", readonly=True)

    # endregion [Account Filter Fields]

    @api.depends("date_start", "date_end")
    def _compute_account_id_domain(self):
        for rec in self:
            if self.env.user.has_group('account.group_account_manager') \
                    or self.env.user.has_group('pr_account.custom_group_accounting_manager'):
                # Managers: All ACTIVE accounts
                rec.account_id_domain = "[('deprecated','=',False)]"
            else:
                # Restricted users: active AND not forbidden account(s)
                rec.account_id_domain = "[('deprecated','=',False), ('id','!=',749)]"

    @api.constrains("main_head", "assets_main_head", "liability_main_head", "current_assets_category",
                    "fixed_assets_category", "other_assets_category",
                    "current_liability_category", "liability_non_current_category", "equity_category",
                    "revenue_category", "expense_category", "cash_equivalents_subcategory",
                    "banks_subcategory", "accounts_receivable_subcategory", "inventory_subcategory",
                    "prepaid_expenses_subcategory",
                    "vehicles_subcategory", "furniture_fixture_subcategory", "computer_printers_subcategory",
                    "machinery_equipment_subcategory",
                    "land_buildings_subcategory", "investment_subcategory", "vat_receivable_subcategory",
                    "suspense_account_subcategory", "accounts_payable_subcategory",
                    "short_term_loans_subcategory", "other_liabilities_subcategory", "long_term_loans_subcategory",
                    "lease_obligations_subcategory",
                    "capital_subcategory", "operating_revenue_subcategory", "cogs_subcategory",
                    "operating_expenses_subcategory",
                    "financial_expenses_subcategory", "other_expenses_subcategory",
                    "account_id")
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
            account_ids = self.env["account.account"].sudo().search(account_ids_domain)
            if account_ids:
                tax_ids = self.env["account.tax"].sudo().search([("type_tax_use", "in", ["purchase", "sale"])])
                if tax_ids:
                    tax_account_ids = tax_ids.repartition_line_ids.mapped("account_id")
                    if tax_account_ids:
                        filtered_tax_account_ids = account_ids.filtered(lambda a: a.id not in tax_account_ids.ids)
                    else:
                        filtered_tax_account_ids = account_ids
                else:
                    filtered_tax_account_ids = account_ids
                if self.account_id:
                    filtered_account_ids = filtered_tax_account_ids.filtered(lambda a: a.id == self.account_id.id).ids
                    if filtered_account_ids:
                        self.account_ids = filtered_account_ids
                    else:
                        self.account_ids = False
                else:
                    self.account_ids = filtered_tax_account_ids.ids
            else:
                if self.account_id:
                    self.account_ids = self.account_id.ids
                else:
                    self.account_ids = False
        else:
            if self.account_id:
                self.account_ids = self.account_id.ids
            else:
                self.account_ids = False

        # ----------------------------------------------------------
        # FORCE MATCH WITH VAT SUMMARY IF expense + excluding_vat
        # ----------------------------------------------------------
        if self.main_head == "expense" and self.vat_option == "excluding_vat":
            self.account_ids = self.env['account.account'].search([
                ('account_type', 'in', ['expense', 'cost_of_revenue']),
                ('deprecated', '=', False),
            ]).ids
            return

    def get_report(self):
        """Call when button 'Get Report' clicked.
        """
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'date_start': self.date_start,
                'date_end': self.date_end,
                'account': self.account_ids.ids,
                'company': self.company_id.id,
                'vat_option': self.vat_option,
                'department': self.department_id.id if self.department_id else False,
                'section': self.section_id.id if self.section_id else False,
                'project': self.project_id.id if self.project_id else False,
                'employee': self.employee_id.id if self.employee_id else False,
                'asset': self.asset_id.id if self.asset_id else False,
            },
        }
        return self.env.ref('account_ledger.vat_leg_report').report_action(self, data=data)

    def print_xlsx_report(self):
        return self.env.ref('account_ledger.vat_ledger_xlsx_report_view_xlsx').report_action(self, data=None)

    def action_view_vat_ledger_report(self):
        self.ensure_one()

        Report = self.env["report.account_ledger.vat_ledger_rep"]

        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'date_start': self.date_start.strftime('%Y-%m-%d'),
                'date_end': self.date_end.strftime('%Y-%m-%d'),
                'account': self.account_ids.ids,
                'company': self.company_id.id,
                'department': self.department_id.id if self.department_id else False,
                'section': self.section_id.id if self.section_id else False,
                'project': self.project_id.id if self.project_id else False,
                'employee': self.employee_id.id if self.employee_id else False,
                'asset': self.asset_id.id if self.asset_id else False,
                'vat_option': self.vat_option,
            },
        }

        report_vals = Report._get_report_values(self.ids, data)
        docs = report_vals.get("docs", [])

        result = self.env["vat.ledger.result"].create({
            "wizard_id": self.id
        })

        for line in docs:
            is_total = True if not line.get("transaction_ref") else False

            self.env["vat.ledger.result.line"].create({
                "result_id": result.id,
                "transaction_ref": line.get("transaction_ref") or "",
                "reference": line.get("reference") or "",
                "date": line.get("date") if line.get("transaction_ref") else False,
                "description": line.get("description") or "",
                "amount": float(line.get("amount", '0').replace(",", "")) if not is_total else 0,
                "tax_amount": float(line.get("tax_amount", '0').replace(",", "")) if not is_total else 0,
                "total_amount": float(line.get("total_amount", '0').replace(",", "")) if not is_total else 0,
                "is_total": is_total,
            })

        return {
            "type": "ir.actions.act_window",
            "name": "VAT Ledger Report",
            "res_model": "vat.ledger.result",
            "res_id": result.id,
            "view_mode": "form",
            "target": "current",
        }
