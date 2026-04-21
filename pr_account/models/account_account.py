# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models

MAIN_HEAD_FIELDS = ["assets_main_head", "liability_main_head"]
CATEGORY_FIELDS = [
    "current_assets_category", "fixed_assets_category", "other_assets_category",
    "current_liability_category", "liability_non_current_category", "equity_category",
    "revenue_category", "expense_category",
]

CURRENT_ASSET_FIELDS = [
    "cash_equivalents_subcategory", "banks_subcategory", "accounts_receivable_subcategory",
    "inventory_subcategory", "prepaid_expenses_subcategory",'current_assets_category_advance_sub_category',
]
FIXED_ASSET_FIELDS = [
    "vehicles_subcategory", "furniture_fixture_subcategory", "computer_printers_subcategory",
    "machinery_equipment_subcategory", "land_buildings_subcategory",
]
OTHER_ASSET_FIELDS = ["investment_subcategory", "vat_receivable_subcategory", "suspense_account_subcategory"]

CURRENT_LIABILITY_FIELDS = [
    "accounts_payable_subcategory", "short_term_loans_subcategory", "other_liabilities_subcategory",
    "current_liability_advance_sub_category",
]
NON_CURRENT_LIABILITY_FIELDS = ["long_term_loans_subcategory", "lease_obligations_subcategory"]

EQUITY_FIELDS = ["capital_subcategory"]
REVENUE_FIELDS = ["operating_revenue_subcategory"]
EXPENSE_FIELDS = [
    "cogs_subcategory", "operating_expenses_subcategory", "financial_expenses_subcategory",
    "other_expenses_subcategory",
]

# All fields used to classify accounts (used to build search domain)
CLASSIFICATION_FIELDS = (
        ["main_head"]
        + MAIN_HEAD_FIELDS
        + CATEGORY_FIELDS
        + CURRENT_ASSET_FIELDS
        + FIXED_ASSET_FIELDS
        + OTHER_ASSET_FIELDS
        + CURRENT_LIABILITY_FIELDS
        + NON_CURRENT_LIABILITY_FIELDS
        + EQUITY_FIELDS
        + REVENUE_FIELDS
        + EXPENSE_FIELDS
)

# Subcategory fields only (trigger code generation)
SUBCATEGORY_FIELDS = (
        CURRENT_ASSET_FIELDS
        + FIXED_ASSET_FIELDS
        + OTHER_ASSET_FIELDS
        + CURRENT_LIABILITY_FIELDS
        + NON_CURRENT_LIABILITY_FIELDS
        + EQUITY_FIELDS
        + REVENUE_FIELDS
        + EXPENSE_FIELDS
)


class AccountAccount(models.Model):
    _inherit = "account.account"

    # ------------------------------------------------------------
    # Classification fields
    # ------------------------------------------------------------
    main_head = fields.Selection([
        ("assets", "Assets"),
        ("liabilities", "Liabilities"),
        ("equity", "Equity"),
        ("revenue", "Revenue"),
        ("expense", "Expense"),
    ], string="Main Head", tracking=True)

    assets_main_head = fields.Selection([
        ("asset_current", "Current Assets"),
        ("asset_fixed", "Fixed Assets"),
        ("asset_non_current", "Other Assets"),
    ], string="Assets Main Head", tracking=True)

    liability_main_head = fields.Selection([
        ("liability_current", "Current Liabilities"),
        ("liability_non_current", "Long-Term Liabilities"),
    ], string="Liabilities Main Head", tracking=True)

    # ---------------- Category ----------------
    current_assets_category = fields.Selection([
        ("cash_equivalents", "Cash & Equivalents"),
        ("banks", "Banks"),
        ("account_receivable", "Account Receivable"),
        ("inventory", "Inventory"),
        ("prepaid_expenses", "Prepaid Expenses"),
        ("advances", "Advances")

    ], string="Current Assets Category", tracking=True)

    current_assets_category_advance_sub_category = fields.Selection([
        ("customer_advances", "Customer Advances"),
        ("supplier_advances", "Supplier Advances")
    ], string="Advances Sub-Category", tracking=True)

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
        ("advances", "Advances")
    ], string="Current Liabilities Category", tracking=True)

    current_liability_advance_sub_category = fields.Selection([
        ("customer_advances", "Customer Advances"),
        ("supplier_advances", "Supplier Advances")
    ], string="Advances Sub-Category", tracking=True)

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

    # ---------------- Sub Category ----------------
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
    ], string="Vehicles Sub-Category", tracking=True)

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
        ("bank", "Bank"),
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
    ], string="Operating Expenses Sub-Category", tracking=True)

    financial_expenses_subcategory = fields.Selection([
        ("interest_expense", "Interest Expense"),
    ], string="Financial Expenses Sub-Category", tracking=True)

    other_expenses_subcategory = fields.Selection([
        ("general_administrative_expenses", "General Administrative Expenses"),
    ], string="Other Expenses Sub-Category", tracking=True)

    # ------------------------------------------------------------
    # Onchange: clear dependent fields when parent changes
    #   Rule:
    #     - main_head / sub_main_head / category change => clear code
    #     - subcategory change => generate code
    # ------------------------------------------------------------
    @api.onchange("main_head")
    def _onchange_main_head(self):
        all_groups = (
                MAIN_HEAD_FIELDS
                + CATEGORY_FIELDS
                + CURRENT_ASSET_FIELDS
                + FIXED_ASSET_FIELDS
                + OTHER_ASSET_FIELDS
                + CURRENT_LIABILITY_FIELDS
                + NON_CURRENT_LIABILITY_FIELDS
                + EQUITY_FIELDS
                + REVENUE_FIELDS
                + EXPENSE_FIELDS
        )
        for rec in self:
            if rec.main_head:
                for f in all_groups:
                    setattr(rec, f, False)
            # always clear code when head changes
            rec.code = False

    @api.onchange("assets_main_head", "liability_main_head")
    def _onchange_assets_liability_main_head(self):
        all_groups = (
                CATEGORY_FIELDS
                + CURRENT_ASSET_FIELDS
                + FIXED_ASSET_FIELDS
                + OTHER_ASSET_FIELDS
                + CURRENT_LIABILITY_FIELDS
                + NON_CURRENT_LIABILITY_FIELDS
                + EQUITY_FIELDS
                + REVENUE_FIELDS
                + EXPENSE_FIELDS
        )
        for rec in self:
            if rec.assets_main_head or rec.liability_main_head:
                for f in all_groups:
                    setattr(rec, f, False)
            rec.code = False

    @api.onchange(
        "current_assets_category", "fixed_assets_category", "other_assets_category",
        "current_liability_category", "liability_non_current_category",
        "equity_category", "revenue_category", "expense_category",
    )
    def _onchange_category(self):
        all_groups = (
                CURRENT_ASSET_FIELDS
                + FIXED_ASSET_FIELDS
                + OTHER_ASSET_FIELDS
                + CURRENT_LIABILITY_FIELDS
                + NON_CURRENT_LIABILITY_FIELDS
                + EQUITY_FIELDS
                + REVENUE_FIELDS
                + EXPENSE_FIELDS
        )
        for rec in self:
            if (
                    rec.assets_main_head or rec.liability_main_head
                    or rec.current_assets_category or rec.fixed_assets_category or rec.other_assets_category
                    or rec.current_liability_category or rec.liability_non_current_category
                    or rec.equity_category or rec.revenue_category or rec.expense_category
            ):
                for f in all_groups:
                    setattr(rec, f, False)
            rec.code = False

    # Generate code only when a subcategory changes
    @api.onchange(*SUBCATEGORY_FIELDS)
    def _onchange_subcategory_generate_code(self):
        for rec in self:
            if not rec._is_classification_ready_for_code():
                rec.code = False
                continue
            rec.code = rec._get_next_coa_code() or False

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------
    def _is_classification_ready_for_code(self):
        """Return True only when user picked enough values to define a bucket."""
        self.ensure_one()
        if not self.main_head:
            return False

        if self.main_head == "assets":
            if not self.assets_main_head:
                return False
            if self.assets_main_head == "asset_current":
                return bool(
                    self.current_assets_category and (
                            self.cash_equivalents_subcategory or self.banks_subcategory
                            or self.accounts_receivable_subcategory or self.inventory_subcategory
                            or self.prepaid_expenses_subcategory or self.current_assets_category_advance_sub_category
                    )
                )
            if self.assets_main_head == "asset_fixed":
                return bool(
                    self.fixed_assets_category and (
                            self.vehicles_subcategory or self.furniture_fixture_subcategory
                            or self.computer_printers_subcategory or self.machinery_equipment_subcategory
                            or self.land_buildings_subcategory
                    )
                )
            if self.assets_main_head == "asset_non_current":
                return bool(
                    self.other_assets_category and (
                            self.investment_subcategory or self.vat_receivable_subcategory
                            or self.suspense_account_subcategory
                    )
                )
            return False

        if self.main_head == "liabilities":
            if not self.liability_main_head:
                return False
            if self.liability_main_head == "liability_current":
                return bool(
                    self.current_liability_category and (
                            self.accounts_payable_subcategory or self.short_term_loans_subcategory
                            or self.other_liabilities_subcategory or self.current_liability_advance_sub_category
                    )
                )
            if self.liability_main_head == "liability_non_current":
                return bool(
                    self.liability_non_current_category and (
                            self.long_term_loans_subcategory or self.lease_obligations_subcategory
                    )
                )
            return False

        if self.main_head == "equity":
            return bool(self.equity_category and self.capital_subcategory)

        if self.main_head == "revenue":
            return bool(self.revenue_category and self.operating_revenue_subcategory)

        if self.main_head == "expense":
            return bool(
                self.expense_category and (
                        self.cogs_subcategory or self.operating_expenses_subcategory
                        or self.financial_expenses_subcategory or self.other_expenses_subcategory
                )
            )

        return False

    def _get_next_coa_code(self):
        """Find the last code in the same bucket (company + selected fields) then increment."""
        self.ensure_one()
        if not self.main_head:
            return False

        company = self.company_id or self.env.company
        domain = [("company_id", "=", company.id), ("code", "!=", False)]

        for field_name in CLASSIFICATION_FIELDS:
            val = getattr(self, field_name, False)
            if val:
                domain.append((field_name, "=", val))

        # sudo avoids access rules hiding accounts and returning empty candidates
        candidates = self.sudo().search(domain, limit=5000)
        if not candidates:
            return False

        def code_key(code):
            parts = (code or "").split(".")
            if parts and all(p.isdigit() for p in parts):
                return [int(p) for p in parts]
            m = re.search(r"(\d+)$", code or "")
            return [int(m.group(1))] if m else [-1]

        last_code = max((r.code for r in candidates if r.code), key=code_key, default=False)
        if not last_code:
            return False

        return self._increment_account_code(last_code)

    @staticmethod
    def _increment_account_code(code):
        """Increment last numeric segment. Works for dotted and plain codes."""
        parts = (code or "").split(".")
        if parts and all(p.isdigit() for p in parts):
            last = parts[-1]
            width = len(last)
            parts[-1] = str(int(last) + 1).zfill(width)
            return ".".join(parts)

        m = re.search(r"(\d+)$", code or "")
        if not m:
            return False
        numeric_part = m.group(1)
        width = len(numeric_part)
        next_value = str(int(numeric_part) + 1).zfill(width)
        return f"{code[:-len(numeric_part)]}{next_value}"

    # ------------------------------------------------------------
    # ORM
    # ------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        """
        Backup safety:
        If user creates via import / RPC without UI onchange, still generate code.
        """
        for vals in vals_list:
            if vals.get("code"):
                continue
            record = self.new(vals)
            if record._is_classification_ready_for_code():
                next_code = record._get_next_coa_code()
                if next_code:
                    vals["code"] = next_code
        return super().create(vals_list)

    # ------------------------------------------------------------
    # Display name
    # ------------------------------------------------------------
    @api.depends("code", "name")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec.code or rec.name
