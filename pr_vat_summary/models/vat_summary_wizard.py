# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date
from dateutil.relativedelta import relativedelta
from markupsafe import escape


class VatSummaryWizard(models.TransientModel):
    _name = "vat.summary.wizard"
    _description = "VAT Summary Wizard"

    # -------------------------------------------------------------------------
    # Fields
    # -------------------------------------------------------------------------
    date_filter = fields.Selection([
        ('this_month', "This Month"),
        ('last_month', "Last Month"),
        ('this_quarter', "This Quarter"),
        ('last_quarter', "Last Quarter"),
        ('this_year', "This Year"),
        ('last_year', "Last Year"),
        ('custom', "Custom Range"),
    ], string="Period", default="this_year", required=True)

    company_id = fields.Many2one(
        "res.company", string="Company", required=True,
        default=lambda self: self.env.company,
    )
    date_start = fields.Date(string="Start Date", required=True)
    date_end = fields.Date(string="End Date", required=True)

    summary_title = fields.Char(string="Summary Title", compute="_compute_summary_title")

    account_ids = fields.Many2many(
        "account.account",
        string="Filter Accounts (for Non-Vated)",
        help="Optional filter for Non-Vated Purchases.",
    )

    # Summaries (net/base & VAT only – totals are derived in HTML/XLSX)
    sales_amount = fields.Monetary(currency_field="currency_id", readonly=True)
    sales_vat = fields.Monetary(currency_field="currency_id", readonly=True)
    non_vated_sales_amount = fields.Monetary(currency_field="currency_id", readonly=True)

    vated_purchases_amount = fields.Monetary(currency_field="currency_id", readonly=True)
    vated_purchases_vat = fields.Monetary(currency_field="currency_id", readonly=True)

    non_vated_purchases_amount = fields.Monetary(currency_field="currency_id", readonly=True)

    # In final row:
    # - total_amount     -> Net Amount = Sales - (Vated + Non-Vated)
    # - total_vat_payable -> Net VAT   = Sales VAT - Vated Purchases VAT
    total_amount = fields.Monetary(currency_field="currency_id", readonly=True)
    total_vat_payable = fields.Monetary(currency_field="currency_id", readonly=True)

    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id.id,
    )

    summary_html = fields.Html(readonly=True)
    is_detailed = fields.Boolean(string="Is Detailed", default=False)

    # -------------------------------------------------------------------------
    # Auto Compute Date Range
    # -------------------------------------------------------------------------
    @api.onchange('date_filter')
    def _onchange_date_filter(self):
        """Automatically set date_start/date_end when user selects a pre-defined period."""
        today = date.today()

        if self.date_filter == "this_month":
            self.date_start = today.replace(day=1)
            self.date_end = (self.date_start + relativedelta(months=1)) - relativedelta(days=1)

        elif self.date_filter == "last_month":
            first_this_month = today.replace(day=1)
            last_month_end = first_this_month - relativedelta(days=1)
            self.date_start = last_month_end.replace(day=1)
            self.date_end = last_month_end

        elif self.date_filter == "this_quarter":
            q = (today.month - 1) // 3 + 1
            self.date_start = date(today.year, 3 * q - 2, 1)
            self.date_end = (self.date_start + relativedelta(months=3)) - relativedelta(days=1)

        elif self.date_filter == "last_quarter":
            q = (today.month - 1) // 3 + 1
            q_start = date(today.year, 3 * q - 2, 1) - relativedelta(months=3)
            self.date_start = q_start
            self.date_end = (q_start + relativedelta(months=3)) - relativedelta(days=1)

        elif self.date_filter == "this_year":
            self.date_start = date(today.year, 1, 1)
            self.date_end = date(today.year, 12, 31)

        elif self.date_filter == "last_year":
            last_year = today.year - 1
            self.date_start = date(last_year, 1, 1)
            self.date_end = date(last_year, 12, 31)

        # "custom" → user manually sets dates

    @api.depends('date_filter', 'date_start', 'date_end')
    def _compute_summary_title(self):
        for rec in self:
            if rec.date_filter == 'this_month':
                rec.summary_title = "SUMMARY OF " + rec.date_start.strftime('%B %Y')

            elif rec.date_filter == 'this_quarter':
                quarter = (rec.date_start.month - 1) // 3 + 1
                rec.summary_title = f"SUMMARY OF Q{quarter} {rec.date_start.year}"

            elif rec.date_filter == 'this_year':
                rec.summary_title = f"SUMMARY OF {rec.date_start.year}"

            else:
                # Custom date range
                start = rec.date_start.strftime('%d-%b-%Y')
                end = rec.date_end.strftime('%d-%b-%Y')
                rec.summary_title = f"SUMMARY OF {start} TO {end}"

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    def _base_domain(self):
        """Base domain used for all move lines in the period."""
        self.ensure_one()
        return [
            ("company_id", "=", self.company_id.id),
            ("date", ">=", self.date_start),
            ("date", "<=", self.date_end),
            ("move_id.state", "=", "posted"),
        ]

    # -------------------------------------------------------------------------
    # Core computation
    # -------------------------------------------------------------------------
    def _compute_vat_summary(self):
        """
        VAT Summary matching Odoo / KS Tax Report:

        - VAT amount (15%) is taken from tax lines (tax_line_id != False)
          -> this already matches Odoo/KS.

        - Net/base "Amount" is taken from BASE lines (with tax_ids),
          not from tax_base_amount on the tax lines.

          * Sales (type_tax_use = 'sale'):
              use -line.balance  (revenues are credits -> negative balance)
          * Purchases (type_tax_use = 'purchase'):
              use  line.balance  (expenses are debits -> positive balance)
        """
        self.ensure_one()
        base_domain = self._base_domain()
        aml = self.env["account.move.line"]

        # ---------------------------------------------------------------
        # 1) VAT AMOUNTS (tax lines)  -> this already matches Odoo/KS
        # ---------------------------------------------------------------
        tax_lines = aml.search(base_domain + [("tax_line_id", "!=", False)])

        sales_vat = 0.0
        pur_vat = 0.0

        for line in tax_lines:
            tax = line.tax_line_id
            if not tax:
                continue

            vat_amt = line.balance or 0.0  # signed

            if tax.type_tax_use == "sale":
                sales_vat += vat_amt
            elif tax.type_tax_use == "purchase":
                pur_vat += vat_amt

        # ---------------------------------------------------------------
        # 2) NET AMOUNTS (BASE LINES with tax_ids)  -> align with Odoo
        # ---------------------------------------------------------------
        base_lines = aml.search(base_domain + [("tax_ids", "!=", False)])

        sales_amount = 0.0
        vated_pur_amount = 0.0

        for line in base_lines:
            # A base line can have multiple taxes; we loop them
            for tax in line.tax_ids:
                if tax.type_tax_use == "sale":
                    # Revenue line: credit (negative balance) ⇒ we want positive base
                    sales_amount += -line.balance
                elif tax.type_tax_use == "purchase":
                    # Expense line: debit (positive balance) ⇒ we want positive base
                    vated_pur_amount += line.balance

        # ---------------------------------------------------------------
        # 3) NON-VATED SALES (income lines without taxes)
        # ---------------------------------------------------------------
        non_vated_sales_domain = base_domain + [
            ("account_id.account_type", "in", ["income", "other_income"]),
            ("tax_line_id", "=", False),
            ("tax_tag_ids", "=", False),
            ("tax_ids", "=", False),
        ]
        non_vated_sales_lines = aml.search(non_vated_sales_domain)
        non_vated_sales_amount = sum(-line.balance for line in non_vated_sales_lines)

        # ---------------------------------------------------------------
        # 4) NON-VATED PURCHASES (still: any expense w/o tax)
        # ---------------------------------------------------------------
        non_vated_domain = base_domain + [
            ("account_id.account_type", "in", ["expense", "cost_of_revenue"]),
            ("tax_line_id", "=", False),
            ("tax_tag_ids", "=", False),
            ("tax_ids", "=", False),
        ]
        if self.account_ids:
            non_vated_domain.append(("account_id", "in", self.account_ids.ids))

        expense_lines = aml.search(non_vated_domain)

        non_vated_pur_amount = 0.0
        for line in expense_lines:
            non_vated_pur_amount += line.balance

        # ---------------------------------------------------------------
        # 5) STORE FIELDS + TOTALS
        # ---------------------------------------------------------------
        # Field values (used in HTML/XLSX)
        self.sales_amount = sales_amount
        self.sales_vat = sales_vat
        self.non_vated_sales_amount = non_vated_sales_amount

        self.vated_purchases_amount = vated_pur_amount
        self.vated_purchases_vat = pur_vat

        self.non_vated_purchases_amount = non_vated_pur_amount

        # Summary row (your Excel-style logic)
        # total_amount = Total Sales Amount - Total Purchases Amount
        self.total_amount = (sales_amount + non_vated_sales_amount) - (
            vated_pur_amount + non_vated_pur_amount
        )
        # total_vat_payable = Sales VAT - Purchase VAT (abs for display)
        self.total_vat_payable = abs(sales_vat) - abs(pur_vat)

    def _prepare_detail_line_vals(self, line, amount, vat_amount=0.0):
        return {
            "date": line.date or "",
            "entry": line.move_id.name or line.move_name or "",
            "reference": line.move_id.ref or "",
            "account": f"{line.account_id.code or ''} {line.account_id.name or ''}".strip(),
            "partner": line.partner_id.name or "",
            "label": line.name or "",
            "amount": amount or 0.0,
            "vat_amount": vat_amount or 0.0,
            "total_amount": (amount or 0.0) + (vat_amount or 0.0),
        }

    def _prepare_detailed_lines(self):
        """Collect detailed base lines grouped by vated/non-vated and sales/purchase."""
        self.ensure_one()
        aml = self.env["account.move.line"]
        base_domain = self._base_domain()

        detail_lines = aml.search(base_domain + [
            ("tax_line_id", "=", False),
            ("account_id.account_type", "in", ["income", "other_income", "expense", "cost_of_revenue"]),
        ], order="date, move_id, id")

        details = {
            "vated_sales": [],
            "vated_purchases": [],
            "non_vated_sales": [],
            "non_vated_purchases": [],
        }
        for line in detail_lines:
            if line.account_id.account_type in ["income", "other_income"]:
                amount = -line.balance
                vat_amount = 0.0
                for tax in line.tax_ids:
                    if tax.amount_type in ("percent", "division"):
                        vat_amount += amount * tax.amount / 100.0
                line_vals = self._prepare_detail_line_vals(line, amount, vat_amount)
                if line.tax_ids:
                    details["vated_sales"].append(line_vals)
                else:
                    details["non_vated_sales"].append(line_vals)
            else:
                amount = line.balance
                vat_amount = 0.0
                for tax in line.tax_ids:
                    if tax.amount_type in ("percent", "division"):
                        vat_amount += amount * tax.amount / 100.0
                line_vals = self._prepare_detail_line_vals(line, amount, vat_amount)
                if line.tax_ids:
                    details["vated_purchases"].append(line_vals)
                else:
                    details["non_vated_purchases"].append(line_vals)

        return details

    def _prepare_detailed_html(self, details):
        html = "<br/><h3>Detailed Breakdown</h3>"
        html += """
        <table style='width:100%;border-collapse:collapse;font-size:12px;margin-bottom:10px;'>
            <tr>
                <th style='border:1px solid #000;padding:5px;background:#efefef;'>Journal Entry</th>
                <th style='border:1px solid #000;padding:5px;background:#efefef;'>Reference</th>
                <th style='border:1px solid #000;padding:5px;background:#efefef;'>Date</th>
                <th style='border:1px solid #000;padding:5px;background:#efefef;'>Description</th>
                <th style='border:1px solid #000;padding:5px;background:#efefef;'>Amount</th>
                <th style='border:1px solid #000;padding:5px;background:#efefef;'>VAT Amount</th>
                <th style='border:1px solid #000;padding:5px;background:#efefef;'>Total Amount</th>
            </tr>
        """

        sections = [
            ("Vated - Sales / Revenue", details["vated_sales"]),
            ("Non-Vated - Sales / Revenue", details["non_vated_sales"]),
            ("Vated - Purchases / Expenses", details["vated_purchases"]),
            ("Non-Vated - Purchases / Expenses", details["non_vated_purchases"]),
        ]
        all_lines = []
        for title, lines in sections:
            all_lines.extend(lines)
            html += f"""
            <tr>
                <td colspan='7' style='border:1px solid #000;padding:5px;background:#f5f5f5;font-weight:bold;'>
                    {escape(title)}
                </td>
            </tr>
            """
            if not lines:
                html += """
                <tr><td colspan='7' style='border:1px solid #000;padding:5px;text-align:center;'>No lines</td></tr>
                """
                continue
            section_amount_total = sum(line["amount"] for line in lines)
            section_vat_total = sum(line["vat_amount"] for line in lines)
            section_grand_total = sum(line["total_amount"] for line in lines)
            for line in lines:
                html += f"""
                <tr>
                    <td style='border:1px solid #000;padding:5px;'>{escape(line['entry'])}</td>
                    <td style='border:1px solid #000;padding:5px;'>{escape(line['reference'])}</td>
                    <td style='border:1px solid #000;padding:5px;'>{escape(line['date'])}</td>
                    <td style='border:1px solid #000;padding:5px;'>{escape(line['label'])}</td>
                    <td style='border:1px solid #000;padding:5px;text-align:right;'>{line['amount']:,.2f}</td>
                    <td style='border:1px solid #000;padding:5px;text-align:right;'>{line['vat_amount']:,.2f}</td>
                    <td style='border:1px solid #000;padding:5px;text-align:right;'>{line['total_amount']:,.2f}</td>
                </tr>
                """
            html += f"""
            <tr>
                <td colspan='4' style='border:1px solid #000;padding:5px;text-align:right;font-weight:bold;background:#fafafa;'>
                    Section Total
                </td>
                <td style='border:1px solid #000;padding:5px;text-align:right;font-weight:bold;background:#fafafa;'>{section_amount_total:,.2f}</td>
                <td style='border:1px solid #000;padding:5px;text-align:right;font-weight:bold;background:#fafafa;'>{section_vat_total:,.2f}</td>
                <td style='border:1px solid #000;padding:5px;text-align:right;font-weight:bold;background:#fafafa;'>{section_grand_total:,.2f}</td>
            </tr>
            """
        amount_total = sum(l["amount"] for l in all_lines)
        vat_total = sum(l["vat_amount"] for l in all_lines)
        grand_total = sum(l["total_amount"] for l in all_lines)
        html += f"""
            <tr>
                <td colspan='4' style='border:1px solid #000;padding:5px;text-align:right;font-weight:bold;'>Total</td>
                <td style='border:1px solid #000;padding:5px;text-align:right;font-weight:bold;'>{amount_total:,.2f}</td>
                <td style='border:1px solid #000;padding:5px;text-align:right;font-weight:bold;'>{vat_total:,.2f}</td>
                <td style='border:1px solid #000;padding:5px;text-align:right;font-weight:bold;'>{grand_total:,.2f}</td>
            </tr>
        </table>
        """
        return html

    def _get_gov_vat_label(self, net_total):
        self.ensure_one()
        quarter = ((self.date_start.month - 1) // 3) + 1 if self.date_start else 1
        action = "Deposit" if net_total >= 0 else "Recieve"
        return f"Need to {action} GOV Q{quarter} VAT"

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------
    def action_compute_summary(self):
        """Called from the wizard button: compute + fill HTML preview."""
        self.ensure_one()

        if self.date_start > self.date_end:
            raise UserError("Start Date must be before End Date.")

        self._compute_vat_summary()

        sales_vat_abs = abs(self.sales_vat)
        pur_vat_abs = abs(self.vated_purchases_vat)

        # Section totals
        vated_sales_total = self.sales_amount + sales_vat_abs
        non_vated_sales_total = self.non_vated_sales_amount
        total_sales_amount = self.sales_amount + self.non_vated_sales_amount
        total_sales_vat = sales_vat_abs
        total_sales_total = vated_sales_total + non_vated_sales_total

        vated_pur_total = self.vated_purchases_amount + pur_vat_abs
        non_vated_total = self.non_vated_purchases_amount
        total_pur_amount = self.vated_purchases_amount + self.non_vated_purchases_amount
        total_pur_vat = pur_vat_abs
        total_pur_total = vated_pur_total + non_vated_total

        # Net deposit row (vated sales - vated purchases only)
        deposit_amount = self.sales_amount - self.vated_purchases_amount
        deposit_vat = sales_vat_abs - pur_vat_abs
        deposit_total = vated_sales_total - vated_pur_total

        # Keep computed fields aligned with final row
        self.total_amount = deposit_amount
        self.total_vat_payable = deposit_vat

        gov_vat_label = self._get_gov_vat_label(deposit_total)

        # Build HTML table exactly like your Excel layout
        html = f"""
        <table style="width:100%;border-collapse:collapse;font-size:15px;margin-top:15px;">

            <tr>
                <th colspan="5" 
                    style="background-color:#29608f;color:white;padding:10px;
                           border:2px solid #000;font-size:18px;text-align:center;">
                    VAT Report {self.date_start.strftime('%d-%m-%Y')
        } to {self.date_end.strftime('%d-%m-%Y')}
                </th>
            </tr>

            <tr>
                <th style="background-color:#29608f;color:white;padding:10px;border:2px solid #000;">Sr. No</th>
                <th style="background-color:#29608f;color:white;padding:10px;border:2px solid #000;">Description</th>
                <th style="background-color:#29608f;color:white;padding:10px;border:2px solid #000;">Amount</th>
                <th style="background-color:#29608f;color:white;padding:10px;border:2px solid #000;">VAT 15%</th>
                <th style="background-color:#29608f;color:white;padding:10px;border:2px solid #000;">Total</th>
            </tr>

            <!-- SALES -->
            <tr>
                <td style="border:1.8px solid #000;padding:10px;">1</td>
                <td style="border:1.8px solid #000;padding:10px;font-weight:bold;">Sales:</td>
                <td style="border:1.8px solid #000;padding:10px;"></td>
                <td style="border:1.8px solid #000;padding:10px;"></td>
                <td style="border:1.8px solid #000;padding:10px;"></td>
            </tr>

            <tr>
                <td style="border:1.8px solid #000;padding:10px;">i</td>
                <td style="border:1.8px solid #000;padding:10px;">Sales Revenue / Income Vated</td>
                <td style="border:1.8px solid #000;padding:10px;text-align:right;">{self.sales_amount:,.2f}</td>
                <td style="border:1.8px solid #000;padding:10px;text-align:right;">{sales_vat_abs:,.2f}</td>
                <td style="border:1.8px solid #000;padding:10px;text-align:right;">{vated_sales_total:,.2f}</td>
            </tr>

            <tr>
                <td style="border:1.8px solid #000;padding:10px;">ii</td>
                <td style="border:1.8px solid #000;padding:10px;">Sales Revenue / Income Non Vated</td>
                <td style="border:1.8px solid #000;padding:10px;text-align:right;">{self.non_vated_sales_amount:,.2f}</td>
                <td style="border:1.8px solid #000;padding:10px;text-align:center;">-</td>
                <td style="border:1.8px solid #000;padding:10px;text-align:right;">{non_vated_sales_total:,.2f}</td>
            </tr>

            <tr>
                <td colspan="2"
                    style="border:2px solid #000;padding:10px;font-weight:bold;text-align:right;background:#f5f5f5;">
                    Total Sales Revenue / Income
                </td>
                <td style="border:2px solid #000;padding:10px;text-align:right;font-weight:bold;">{total_sales_amount:,.2f}</td>
                <td style="border:2px solid #000;padding:10px;text-align:right;font-weight:bold;">{total_sales_vat:,.2f}</td>
                <td style="border:2px solid #000;padding:10px;text-align:right;font-weight:bold;">{total_sales_total:,.2f}</td>
            </tr>

            <!-- PURCHASES -->
            <tr>
                <td style="border:1.8px solid #000;padding:10px;">2</td>
                <td style="border:1.8px solid #000;padding:10px;font-weight:bold;">Purchases :</td>
                <td style="border:1.8px solid #000;padding:10px;"></td>
                <td style="border:1.8px solid #000;padding:10px;"></td>
                <td style="border:1.8px solid #000;padding:10px;"></td>
            </tr>

            <tr>
                <td style="border:1.8px solid #000;padding:10px;">i</td>
                <td style="border:1.8px solid #000;padding:10px;">Vated Purchase/Expenses</td>
                <td style="border:1.8px solid #000;padding:10px;text-align:right;">{self.vated_purchases_amount:,.2f}</td>
                <td style="border:1.8px solid #000;padding:10px;text-align:right;">{abs(self.vated_purchases_vat):,.2f}</td>
                <td style="border:1.8px solid #000;padding:10px;text-align:right;">{vated_pur_total:,.2f}</td>
            </tr>

            <tr>
                <td style="border:1.8px solid #000;padding:10px;">ii</td>
                <td style="border:1.8px solid #000;padding:10px;">Non Vated Purchase/Expenses</td>
                <td style="border:1.8px solid #000;padding:10px;text-align:right;">{self.non_vated_purchases_amount:,.2f}</td>
                <td style="border:1.8px solid #000;padding:10px;text-align:right;">0.00</td>
                <td style="border:1.8px solid #000;padding:10px;text-align:right;">{non_vated_total:,.2f}</td>
            </tr>

            <!-- TOTAL -->
            <tr>
                <td colspan="2"
                    style="border:2px solid #000;padding:10px;font-weight:bold;text-align:right;background:#f5f5f5;">
                    Total Purchases / Expenses
                </td>
                <td style="border:2px solid #000;padding:10px;text-align:right;font-weight:bold;">{total_pur_amount:,.2f}</td>
                <td style="border:2px solid #000;padding:10px;text-align:right;font-weight:bold;">{total_pur_vat:,.2f}</td>
                <td style="border:2px solid #000;padding:10px;text-align:right;font-weight:bold;">{total_pur_total:,.2f}</td>
            </tr>

            <tr>
                <td colspan="2"
                    style="border:2px solid #000;padding:10px;font-weight:bold;text-align:center;background:#f5f5f5;">
                    {gov_vat_label}
                </td>
                <td style="border:2px solid #000;padding:10px;text-align:right;font-weight:bold;">{deposit_amount:,.2f}</td>
                <td style="border:2px solid #000;padding:10px;text-align:right;font-weight:bold;">{deposit_vat:,.2f}</td>
                <td style="border:2px solid #000;padding:10px;text-align:right;font-weight:bold;">{deposit_total:,.2f}</td>
            </tr>

        </table>
        """

        if self.is_detailed:
            html += self._prepare_detailed_html(self._prepare_detailed_lines())

        self.summary_html = html

        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_print_pdf(self):
        self.ensure_one()
        if not self.summary_html:
            self.action_compute_summary()
        return self.env.ref(
            "pr_vat_summary.vat_summary_pdf_report"
        ).report_action(self)

    def action_export_xlsx(self):
        self.ensure_one()
        if not self.summary_html:
            self.action_compute_summary()
        return self.env.ref(
            "pr_vat_summary.vat_summary_xlsx_report"
        ).report_action(self)