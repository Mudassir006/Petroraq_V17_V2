# -*- coding: utf-8 -*-
from odoo import api, models, fields
from datetime import date
from collections import defaultdict
from odoo.tools import float_round

MAIN_HEAD = ["main_head"]
MAIN_HEAD_FIELDS = ["assets_main_head", "liability_main_head"]
CATEGORY_FIELDS = [
    "current_assets_category", "fixed_assets_category", "other_assets_category",
    "current_liability_category", "liability_non_current_category", "equity_category",
    "revenue_category", "expense_category",
]

CURRENT_ASSET_FIELDS = [
    "cash_equivalents_subcategory", "banks_subcategory", "accounts_receivable_subcategory",
    "inventory_subcategory", "prepaid_expenses_subcategory",
]
FIXED_ASSET_FIELDS = [
    "vehicles_subcategory", "furniture_fixture_subcategory", "computer_printers_subcategory",
    "machinery_equipment_subcategory", "land_buildings_subcategory",
]
OTHER_ASSET_FIELDS = ["investment_subcategory", "vat_receivable_subcategory", "suspense_account_subcategory"]
CURRENT_LIABILITY_FIELDS = ["accounts_payable_subcategory", "short_term_loans_subcategory",
                            "other_liabilities_subcategory"]
NON_CURRENT_LIABILITY_FIELDS = ["long_term_loans_subcategory", "lease_obligations_subcategory"]
EQUITY_FIELDS = ["capital_subcategory"]
REVENUE_FIELDS = ["operating_revenue_subcategory"]
EXPENSE_FIELDS = ["cogs_subcategory", "operating_expenses_subcategory", "financial_expenses_subcategory",
                  "other_expenses_subcategory"]


class CustomDynamicLedgerReportWizard(models.TransientModel):
    _name = "custom.dynamic.ledger.report.wizard"

    date_start = fields.Date(string="Start Date", required=True, default=date(2025, 1, 1))
    date_end = fields.Date(string="End Date", required=True, default=fields.Date.today)

    main_head = fields.Selection([
        ("all", "All"),
        ("assets", "Assets"),
        ("liabilities", "Liabilities"),
        ("equity", "Equity"),
        ("revenue", "Revenue"),
        ("expense", "Expense"),
    ], string="Main Head", required=True, tracking=True)

    assets_main_head = fields.Selection([
        ("asset_current", "Current Assets"),
        ("asset_fixed", "Fixed Assets"),
        ("asset_non_current", "Other Assets"),
    ], string="Assets Main Head", tracking=True)
    liability_main_head = fields.Selection([
        ("liability_current", "Current Liabilities"),
        ("liability_non_current", "Long-Term Liabilities"),
    ], string="Liabilities Main Head", tracking=True)

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
    # domain handled via account_id_domain compute (and used in XML)
    account_id = fields.Many2one("account.account", string="Account")
    account_id_domain = fields.Char(compute="_compute_account_id_domain")

    account_name = fields.Char(string="Account Name", related="account_id.name")
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)

    department_id = fields.Many2one("account.analytic.account", string="Department",
                                    domain="[('analytic_plan_type', '=', 'department')]")
    section_id = fields.Many2one("account.analytic.account", string="Section",
                                 domain="[('analytic_plan_type', '=', 'section')]")
    project_id = fields.Many2one("account.analytic.account", string="Project",
                                 domain="[('analytic_plan_type', '=', 'project')]")
    employee_id = fields.Many2one("account.analytic.account", string="Employee",
                                  domain="[('analytic_plan_type', '=', 'employee')]")
    asset_id = fields.Many2one("account.analytic.account", string="Asset",
                               domain="[('analytic_plan_type', '=', 'asset')]")

    # ----------------------------
    # UI buttons
    # ----------------------------
    def print_report(self):
        return self.print_xlsx_report()

    def print_xlsx_report(self):
        return self.env.ref("account_ledger.custom_dynamic_ledger_report_view_xlsx").report_action(self, data=None)

    def get_report(self):
        data = {
            "ids": self.ids,
            "model": self._name,
            "form": {
                "date_start": self.date_start,
                "date_end": self.date_end,
                "main_head": self.main_head,
                "company": self.company_id.id,
                "department": self.department_id.id if self.department_id else False,
                "section": self.section_id.id if self.section_id else False,
                "project": self.project_id.id if self.project_id else False,
                "employee": self.employee_id.id if self.employee_id else False,
                "asset": self.asset_id.id if self.asset_id else False,
            },
        }
        return self.env.ref("account_ledger.custom_dynamic_ledger_report_pdf").report_action(self, data=data)

    # ----------------------------
    # Domains / analytics
    # ----------------------------
    @api.depends("main_head", "company_id")
    def _compute_account_id_domain(self):
        """
        Build domain for account_id field.
        Also supports restricting accounts for non-managers through an ir.config_parameter:
            key: account_ledger.restricted_account_ids
            value: "12,45,78"
        """
        Param = self.env["ir.config_parameter"].sudo()
        restricted_raw = (Param.get_param("account_ledger.restricted_account_ids") or "").strip()
        restricted_ids = []
        if restricted_raw:
            restricted_ids = [int(x) for x in restricted_raw.split(",") if x.strip().isdigit()]

        for rec in self:
            dom = []
            if rec.main_head and rec.main_head != "all":
                dom.append(("main_head", "=", rec.main_head))

            # If you want parent company accounts too, keep it; otherwise remove.
            if rec.company_id:
                dom.append(("company_id", "in",
                            [rec.company_id.id, rec.company_id.parent_id.id] if rec.company_id.parent_id else [
                                rec.company_id.id]))

            # restriction only for non managers
            is_manager = rec.env.user.has_group("account.group_account_manager") or rec.env.user.has_group(
                "pr_account.custom_group_accounting_manager")
            if restricted_ids and not is_manager:
                dom.append(("id", "not in", restricted_ids))

            rec.account_id_domain = str(dom)

    def _selected_analytic_ids(self):
        ids = []
        if self.department_id:
            ids.append(self.department_id.id)
        if self.section_id:
            ids.append(self.section_id.id)
        if self.project_id:
            ids.append(self.project_id.id)

        if self.employee_id:
            ids.append(self.employee_id.id)
        if self.asset_id:
            ids.append(self.asset_id.id)

        return ids

    def _filter_move_lines_by_analytic(self, move_lines):
        """
        Keep AML only if it contains ALL selected analytics in analytic_distribution.
        analytic_distribution keys are strings.
        """
        analytic_ids = self._selected_analytic_ids()
        if not analytic_ids:
            return move_lines

        keys = [str(i) for i in analytic_ids]

        def _ok(line):
            dist = line.analytic_distribution or {}
            return all(k in dist for k in keys)

        return move_lines.filtered(_ok)

    # ----------------------------
    # Report generation (FAST + correct)
    # ----------------------------
    def action_view_custom_dynamic_ledger_report(self):
        self.ensure_one()
        report_rows = self.generate_balance_report()

        result = self.env["custom.dynamic.ledger.result"].create({"wizard_id": self.id})

        for row in report_rows:
            ending_debit = row["ending_debit"]
            ending_credit = row["ending_credit"]

            if ending_debit > ending_credit:
                balance = ending_debit - ending_credit
                balance_type = "Debit"
            elif ending_credit > ending_debit:
                balance = ending_credit - ending_debit
                balance_type = "Credit"
            else:
                balance = 0.0
                balance_type = "-"

            self.env["custom.dynamic.ledger.result.line"].create({
                "result_id": result.id,
                "label": row["level"],
                "initial_debit": row["initial_debit"],
                "initial_credit": row["initial_credit"],
                "period_debit": row["period_debit"],
                "period_credit": row["period_credit"],
                "ending_debit": ending_debit,
                "ending_credit": ending_credit,
                "balance": balance,
                "balance_type": balance_type,
            })

        return {
            "type": "ir.actions.act_window",
            "name": "Dynamic Balance Report",
            "res_model": "custom.dynamic.ledger.result",
            "res_id": result.id,
            "view_mode": "form",
            "target": "current",
        }

    def generate_balance_report(self):
        """
        Hierarchical trial balance:
        Main Head → Category → Subcategory → Account
        """
        self.ensure_one()

        account_domain = [
            ("main_head", "!=", False),
            ("company_id", "in",
             [self.company_id.id, self.company_id.parent_id.id] if self.company_id.parent_id else [self.company_id.id]),
        ]
        if self.main_head and self.main_head != "all":
            account_domain.append(("main_head", "=", self.main_head))
        filter_fields = (
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
        for field_name in filter_fields:
            value = getattr(self, field_name, False)
            if value:
                account_domain.append((field_name, "=", value))
        if self.account_id:
            account_domain.append(("id", "=", self.account_id.id))

        accounts = self.env["account.account"].sudo().search(account_domain, order="code asc")
        if not accounts:
            return []

        aml = self.env["account.move.line"].sudo()
        analytic_ids = self._selected_analytic_ids()

        # ----------------------------
        # 1) Build totals per account (initial & period)
        # ----------------------------
        def _map_from_read_group(domain):
            rows = aml.read_group(domain, ["debit:sum", "credit:sum", "account_id"], ["account_id"])
            out = {}
            for r in rows:
                if r.get("account_id"):
                    out[r["account_id"][0]] = {
                        "debit": float_round(r.get("debit", 0.0), 2),
                        "credit": float_round(r.get("credit", 0.0), 2),
                    }
            return out

        initial_map = {}
        period_map = {}

        base_domain = [
            ("move_id.state", "=", "posted"),
            ("company_id", "in",
             [self.company_id.id, self.company_id.parent_id.id] if self.company_id.parent_id else [self.company_id.id]),
            ("account_id", "in", accounts.ids),
        ]

        if not analytic_ids:
            # FAST path (SQL group-by)
            initial_map = _map_from_read_group(base_domain + [("date", "<", self.date_start)])
            period_map = _map_from_read_group(
                base_domain + [("date", ">=", self.date_start), ("date", "<=", self.date_end)])
        else:
            # Analytics selected: fetch once per range, then filter & aggregate in python
            init_lines = aml.search(base_domain + [("date", "<", self.date_start)])
            init_lines = self._filter_move_lines_by_analytic(init_lines)

            per_lines = aml.search(base_domain + [("date", ">=", self.date_start), ("date", "<=", self.date_end)])
            per_lines = self._filter_move_lines_by_analytic(per_lines)

            def _aggregate(lineset):
                acc_tot = defaultdict(lambda: {"debit": 0.0, "credit": 0.0})
                for l in lineset:
                    acc_tot[l.account_id.id]["debit"] += l.debit
                    acc_tot[l.account_id.id]["credit"] += l.credit
                # rounding at end
                for k, v in acc_tot.items():
                    v["debit"] = float_round(v["debit"], 2)
                    v["credit"] = float_round(v["credit"], 2)
                return dict(acc_tot)

            initial_map = _aggregate(init_lines)
            period_map = _aggregate(per_lines)

        # ----------------------------
        # 2) Group into hierarchy
        # ----------------------------
        grouped_data = defaultdict(lambda: {
            "summary": self._init_balance_totals(),
            "categories": defaultdict(lambda: {
                "summary": self._init_balance_totals(),
                "subcategories": defaultdict(lambda: {
                    "summary": self._init_balance_totals(),
                    "accounts": {}
                })
            })
        })

        for account in accounts:
            main_head = account.main_head or "Unclassified"
            category = self.get_category(account)
            subcategory = self.get_subcategory(account)

            initial = initial_map.get(account.id, {"debit": 0.0, "credit": 0.0})
            period = period_map.get(account.id, {"debit": 0.0, "credit": 0.0})

            ending = {
                "debit": float_round(initial["debit"] + period["debit"], 2),
                "credit": float_round(initial["credit"] + period["credit"], 2),
            }

            account_key = f"{account.code} - {account.name}"
            account_row = {
                "initial_debit": initial["debit"],
                "initial_credit": initial["credit"],
                "period_debit": period["debit"],
                "period_credit": period["credit"],
                "ending_debit": ending["debit"],
                "ending_credit": ending["credit"],
            }

            subcat_data = grouped_data[main_head]["categories"][category]["subcategories"][subcategory]
            subcat_data["accounts"][account_key] = account_row

            self._update_totals(grouped_data[main_head]["summary"], account_row)
            self._update_totals(grouped_data[main_head]["categories"][category]["summary"], account_row)
            self._update_totals(subcat_data["summary"], account_row)

        # ----------------------------
        # 3) Flatten rows in order
        # ----------------------------
        report_rows = []
        for main_head, main_data in grouped_data.items():
            report_rows.append(self.format_row(main_head.title(), main_data["summary"], level=0))

            for category, cat_data in main_data["categories"].items():
                report_rows.append(self.format_row(category.title(), cat_data["summary"], level=1))

                for subcategory, subcat_data in cat_data["subcategories"].items():
                    report_rows.append(self.format_row(subcategory.title(), subcat_data["summary"], level=2))

                    for acc_label, acc_data in subcat_data["accounts"].items():
                        report_rows.append(self.format_row(acc_label, acc_data, level=3))

        return report_rows

    # ----------------------------
    # Helpers
    # ----------------------------
    def _init_balance_totals(self):
        return {
            "initial_debit": 0.0,
            "initial_credit": 0.0,
            "period_debit": 0.0,
            "period_credit": 0.0,
            "ending_debit": 0.0,
            "ending_credit": 0.0,
        }

    def _update_totals(self, summary, row):
        for k in summary:
            summary[k] += float_round(row.get(k, 0.0), precision_digits=2)

    def format_row(self, label, data, level=0):
        indent = "    " * level
        return {
            "level": f"{indent}{label}",
            "initial_debit": data["initial_debit"],
            "initial_credit": data["initial_credit"],
            "period_debit": data["period_debit"],
            "period_credit": data["period_credit"],
            "ending_debit": data["ending_debit"],
            "ending_credit": data["ending_credit"],
        }

    def get_category(self, account):
        if account.main_head == "assets":
            return getattr(account, "current_assets_category") or getattr(account, "fixed_assets_category") or getattr(
                account, "other_assets_category") or "Unclassified"
        if account.main_head == "liabilities":
            return getattr(account, "current_liability_category") or getattr(account,
                                                                             "liability_non_current_category") or "Unclassified"
        if account.main_head == "equity":
            return getattr(account, "equity_category") or "Unclassified"
        if account.main_head == "revenue":
            return getattr(account, "revenue_category") or "Unclassified"
        if account.main_head == "expense":
            return getattr(account, "expense_category") or "Unclassified"
        return "Unclassified"

    def get_subcategory(self, account):
        category = self.get_category(account)
        if not category or category == "Unclassified":
            return "Unclassified"

        subcategory_fields = (
                CURRENT_ASSET_FIELDS + FIXED_ASSET_FIELDS + OTHER_ASSET_FIELDS +
                CURRENT_LIABILITY_FIELDS + NON_CURRENT_LIABILITY_FIELDS +
                EQUITY_FIELDS + REVENUE_FIELDS + EXPENSE_FIELDS
        )
        for f in subcategory_fields:
            if getattr(account, f, False):
                return getattr(account, f)
        return "Unclassified"
