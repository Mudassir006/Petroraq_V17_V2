# pr_vat_summary/reports/vat_summary_xlsx.py
from odoo import models


class VatSummaryXlsx(models.AbstractModel):
    _name = "report.pr_vat_summary.vat_summary_xlsx"
    _inherit = "report.report_xlsx.abstract"

    def _write_detail_section(self, sheet, row, title, details, header_fmt, cell_left, cell_right, section_fmt):
        sheet.merge_range(row, 0, row, 6, title, header_fmt)
        row += 1
        headers = ["Journal Entry", "Reference", "Date", "Description", "Amount", "VAT Amount", "Total Amount"]
        for col, value in enumerate(headers):
            sheet.write(row, col, value, header_fmt)
        row += 1

        sections = [
            ("Vated - Sales / Revenue", details["vated_sales"]),
            ("Non-Vated - Sales / Revenue", details["non_vated_sales"]),
            ("Vated - Purchases / Expenses", details["vated_purchases"]),
            ("Non-Vated - Purchases / Expenses", details["non_vated_purchases"]),
        ]
        all_lines = []
        for section_title, lines in sections:
            all_lines.extend(lines)
            sheet.merge_range(row, 0, row, 6, section_title, section_fmt)
            row += 1
            section_total = sum(line.get("amount", 0.0) for line in lines)
            section_vat_total = sum(line.get("vat_amount", 0.0) for line in lines)
            section_grand_total = sum(line.get("total_amount", 0.0) for line in lines)
            if not lines:
                sheet.merge_range(row, 0, row, 6, "No lines", cell_left)
                row += 1
            else:
                for line in lines:
                    sheet.write(row, 0, line.get("entry", ""), cell_left)
                    sheet.write(row, 1, line.get("reference", ""), cell_left)
                    sheet.write(row, 2, str(line.get("date", "")), cell_left)
                    sheet.write(row, 3, line.get("label", ""), cell_left)
                    sheet.write_number(row, 4, line.get("amount", 0.0), cell_right)
                    sheet.write_number(row, 5, line.get("vat_amount", 0.0), cell_right)
                    sheet.write_number(row, 6, line.get("total_amount", 0.0), cell_right)
                    row += 1

            sheet.merge_range(row, 0, row, 3, "Section Total", section_fmt)
            sheet.write_number(row, 4, section_total, cell_right)
            sheet.write_number(row, 5, section_vat_total, cell_right)
            sheet.write_number(row, 6, section_grand_total, cell_right)
            row += 1

        total = sum(line.get("amount", 0.0) for line in all_lines)
        vat_total = sum(line.get("vat_amount", 0.0) for line in all_lines)
        grand_total = sum(line.get("total_amount", 0.0) for line in all_lines)
        sheet.merge_range(row, 0, row, 3, "Total", cell_left)
        sheet.write_number(row, 4, total, cell_right)
        sheet.write_number(row, 5, vat_total, cell_right)
        sheet.write_number(row, 6, grand_total, cell_right)
        row += 2
        return row

    def generate_xlsx_report(self, workbook, data, wizards):
        wizard = wizards[0]

        # recompute exact values used in PDF/HTML
        wizard._compute_vat_summary()

        sales_vat_abs = abs(wizard.sales_vat)
        pur_vat_abs = abs(wizard.vated_purchases_vat)

        vated_sales_total = wizard.sales_amount + sales_vat_abs
        non_vated_sales_total = wizard.non_vated_sales_amount
        total_sales_amount = wizard.sales_amount + wizard.non_vated_sales_amount
        total_sales_vat = sales_vat_abs
        sales_total = vated_sales_total + non_vated_sales_total
        vated_pur_total = wizard.vated_purchases_amount + pur_vat_abs
        non_vated_total = wizard.non_vated_purchases_amount

        purchase_total_amount = wizard.vated_purchases_amount + wizard.non_vated_purchases_amount
        purchase_total_vat = pur_vat_abs
        purchase_total = vated_pur_total + non_vated_total

        deposit_amount = wizard.sales_amount - wizard.vated_purchases_amount
        deposit_vat = sales_vat_abs - pur_vat_abs
        deposit_total = vated_sales_total - vated_pur_total
        gov_vat_label = wizard._get_gov_vat_label(deposit_total)

        sheet = workbook.add_worksheet("VAT Summary")

        # ---------------------------------------------
        # FORMATS (matching PDF)
        # ---------------------------------------------
        header_fmt = workbook.add_format({
            "bold": True,
            "border": 2,
            "align": "center",
            "valign": "vcenter",
            "bg_color": "#29608F",
            "font_color": "white"
        })

        title_fmt = workbook.add_format({
            "bold": True,
            "border": 2,
            "align": "center",
            "valign": "vcenter",
            "font_size": 14
        })
        report_header_fmt = workbook.add_format({
            "bold": True,
            "border": 1,
            "align": "center",
            "valign": "vcenter",
            "bg_color": "#1F497D",
            "font_color": "white",
            "font_size": 12,
        })

        cell_right = workbook.add_format({
            "border": 2,
            "align": "right"
        })

        cell_center = workbook.add_format({
            "border": 2,
            "align": "center"
        })

        cell_left = workbook.add_format({
            "border": 2,
            "align": "left"
        })

        section_fmt = workbook.add_format({
            "bold": True,
            "border": 2,
            "align": "left",
            "bg_color": "#f5f5f5"
        })

        total_fmt = workbook.add_format({
            "bold": True,
            "border": 2,
            "align": "center"
        })

        # ---------------------------------------------
        # COLUMN WIDTHS
        # ---------------------------------------------
        sheet.set_column(0, 0, 8)
        sheet.set_column(1, 3, 26)
        sheet.set_column(4, 6, 18)

        company = wizard.company_id
        vat_no = company.vat or ""
        sheet.merge_range(
            0, 0, 0, 6,
            f"{company.name} - VAT Number {vat_no}",
            report_header_fmt
        )
        sheet.merge_range(
            1, 0, 1, 6,
            "Statement of VAT Summary",
            report_header_fmt
        )
        sheet.merge_range(
            2, 0, 2, 6,
            f"Period: {wizard.date_start.strftime('%d-%b-%Y')} to {wizard.date_end.strftime('%d-%b-%Y')}",
            report_header_fmt
        )

        # ---------------------------------------------
        # HEADER ROW
        # ---------------------------------------------
        row = 4
        sheet.write(row, 0, "Sr. No", header_fmt)
        sheet.merge_range(row, 1, row, 3, "Description", header_fmt)
        sheet.write(row, 4, "Amount", header_fmt)
        sheet.write(row, 5, "VAT 15%", header_fmt)
        sheet.write(row, 6, "Total", header_fmt)
        row += 1

        # ---------------------------------------------
        # SALES SECTION
        # ---------------------------------------------
        sheet.write(row, 0, "1", section_fmt)
        sheet.merge_range(row, 1, row, 3, "Sales:", section_fmt)
        sheet.write(row, 4, "", section_fmt)
        sheet.write(row, 5, "", section_fmt)
        sheet.write(row, 6, "", section_fmt)
        row += 1

        sheet.write(row, 0, "i", cell_center)
        sheet.merge_range(row, 1, row, 3, "Sales Revenue / Income Vated", cell_left)
        sheet.write_number(row, 4, wizard.sales_amount, cell_right)
        sheet.write_number(row, 5, sales_vat_abs, cell_right)
        sheet.write_number(row, 6, vated_sales_total, cell_right)
        row += 1

        sheet.write(row, 0, "ii", cell_center)
        sheet.merge_range(row, 1, row, 3, "Sales Revenue / Income Non Vated", cell_left)
        sheet.write_number(row, 4, wizard.non_vated_sales_amount, cell_right)
        sheet.write(row, 5, "-", cell_center)
        sheet.write_number(row, 6, non_vated_sales_total, cell_right)
        row += 1

        sheet.merge_range(row, 0, row, 3,
                          "Total Sales Revenue / Income",
                          section_fmt)
        sheet.write_number(row, 4, total_sales_amount, total_fmt)
        sheet.write_number(row, 5, total_sales_vat, total_fmt)
        sheet.write_number(row, 6, sales_total, total_fmt)
        row += 1

        # ---------------------------------------------
        # PURCHASES SECTION
        # ---------------------------------------------
        sheet.write(row, 0, "2", section_fmt)
        sheet.merge_range(row, 1, row, 3, "Purchases :", section_fmt)
        sheet.write(row, 4, "", section_fmt)
        sheet.write(row, 5, "", section_fmt)
        sheet.write(row, 6, "", section_fmt)
        row += 1

        sheet.write(row, 0, "i", cell_center)
        sheet.merge_range(row, 1, row, 3, "Vated Purchase/Expenses", cell_left)
        sheet.write_number(row, 4, wizard.vated_purchases_amount, cell_right)
        sheet.write_number(row, 5, pur_vat_abs, cell_right)
        sheet.write_number(row, 6, vated_pur_total, cell_right)
        row += 1

        sheet.write(row, 0, "ii", cell_center)
        sheet.merge_range(row, 1, row, 3, "Non Vated Purchase/Expenses", cell_left)
        sheet.write_number(row, 4, wizard.non_vated_purchases_amount, cell_right)
        sheet.write(row, 5, "-", cell_center)
        sheet.write_number(row, 6, non_vated_total, cell_right)
        row += 1

        # ---------------------------------------------
        # PURCHASE TOTAL ROW
        # ---------------------------------------------
        sheet.merge_range(row, 0, row, 3,
                          "Total Purchases / Expenses",
                          section_fmt)

        sheet.write_number(row, 4, purchase_total_amount, total_fmt)
        sheet.write_number(row, 5, purchase_total_vat, total_fmt)
        sheet.write_number(row, 6, purchase_total, total_fmt)
        row += 1

        # ---------------------------------------------
        # NEED TO DEPOSIT ROW
        # ---------------------------------------------
        sheet.merge_range(row, 0, row, 3,
                          gov_vat_label,
                          section_fmt)

        sheet.write_number(row, 4, deposit_amount, total_fmt)
        sheet.write_number(row, 5, deposit_vat, total_fmt)
        sheet.write_number(row, 6, deposit_total, total_fmt)

        if wizard.is_detailed:
            details = wizard._prepare_detailed_lines()
            row += 2
            sheet.set_column(0, 0, 20)
            sheet.set_column(1, 1, 24)
            sheet.set_column(2, 2, 14)
            sheet.set_column(3, 3, 40)
            sheet.set_column(4, 6, 18)
            self._write_detail_section(
                sheet, row, "Detailed Transactions", details,
                header_fmt, cell_left, cell_right, section_fmt,
            )