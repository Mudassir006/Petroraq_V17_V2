from odoo import models
from datetime import datetime


class CustomDynamicLedgerReport(models.AbstractModel):
    _name = "report.account_ledger.custom_dynamic_ledger_report"
    _inherit = "report.report_xlsx.abstract"

    def generate_xlsx_report(self, workbook, data, wizard):
        wizard.ensure_one()
        report_data = wizard.generate_balance_report()

        sheet_name = "Balance" if not wizard.main_head or wizard.main_head == "all" else wizard.main_head
        sheet = workbook.add_worksheet(sheet_name[:31])

        # -------------------------
        # Formats
        # -------------------------
        header_big = workbook.add_format({"bold": True, "font_size": 16, "align": "center", "valign": "vcenter"})
        header_mid = workbook.add_format({"bold": True, "font_size": 12, "align": "center", "valign": "vcenter"})

        # Currency formatting (simple, reliable)
        currency_fmt = '#,##0.00 "SAR"'

        def fmt(level, kind="text"):
            bg = {0: "#BDD7EE", 1: "#D9E1F2", 2: "#F2F2F2", 3: "#F9F9F9"}.get(level, "#F9F9F9")
            base = {
                "align": "center",
                "valign": "vcenter",
                "bottom": 1,
                "bg_color": bg,
            }
            if level in (0, 1, 2):
                base["bold"] = True
            if kind == "num_pos":
                base["num_format"] = currency_fmt
            elif kind == "num_neg":
                base["num_format"] = currency_fmt
                base["font_color"] = "red"
            return workbook.add_format(base)

        # -------------------------
        # Header block
        # -------------------------
        sheet.merge_range("A1:H1", f"Company: {wizard.company_id.name}", header_big)
        sheet.merge_range("A2:H2", f"Period: {wizard.date_start} to {wizard.date_end}", header_big)

        extra_row = 3
        if wizard.department_id:
            sheet.merge_range(f"A{extra_row}:H{extra_row}", f"Department: {wizard.department_id.name}", header_mid)
            extra_row += 1
        if wizard.section_id:
            sheet.merge_range(f"A{extra_row}:H{extra_row}", f"Section: {wizard.section_id.name}", header_mid)
            extra_row += 1
        if wizard.project_id:
            sheet.merge_range(f"A{extra_row}:H{extra_row}", f"Project: {wizard.project_id.name}", header_mid)
            extra_row += 1

        if wizard.employee_id:
            sheet.merge_range(f"A{extra_row}:H{extra_row}", f"Employee: {wizard.employee_id.name}", header_mid)
            extra_row += 1
        if wizard.asset_id:
            sheet.merge_range(f"A{extra_row}:H{extra_row}", f"Asset: {wizard.asset_id.name}", header_mid)
            extra_row += 1

        start_row = extra_row + 1

        # Columns
        # A Code | B Name | C Opening Balance | D Opening Type | E Period Balance | F Period Type | G Closing Balance | H Closing Type
        sheet.set_column("A:A", 15)
        sheet.set_column("B:B", 35)
        sheet.set_column("C:C", 18)
        sheet.set_column("D:D", 12)
        sheet.set_column("E:E", 18)
        sheet.set_column("F:F", 12)
        sheet.set_column("G:G", 18)
        sheet.set_column("H:H", 12)

        # Table headers
        head = fmt(0, "text")
        sheet.write(start_row, 0, "Code", head)
        sheet.write(start_row, 1, "Name", head)
        sheet.write(start_row, 2, "Opening Balance", head)
        sheet.write(start_row, 3, "Opening Type", head)
        sheet.write(start_row, 4, "Period Balance", head)
        sheet.write(start_row, 5, "Period Type", head)
        sheet.write(start_row, 6, "Closing Balance", head)
        sheet.write(start_row, 7, "Closing Type", head)

        sheet.freeze_panes(start_row + 1, 0)
        sheet.autofilter(start_row, 0, start_row, 7)

        def to_balance_and_type(debit, credit):
            if debit > credit:
                return (debit - credit, "Debit")
            if credit > debit:
                return (credit - debit, "Credit")
            return (0.0, "-")

        # Data rows
        row_idx = start_row + 1
        for row in report_data:
            indent_spaces = len(row["level"]) - len(row["level"].lstrip())
            level = indent_spaces // 4

            text_fmt = fmt(level, "text")
            pos_fmt = fmt(level, "num_pos")
            neg_fmt = fmt(level, "num_neg")

            label = row["level"].strip()
            parts = label.split(" - ", 1)
            code = parts[0].strip()
            name = parts[1].strip() if len(parts) > 1 else ""

            # hierarchy rows: merge Code+Name
            if level in (0, 1, 2):
                sheet.merge_range(row_idx, 0, row_idx, 1, label, text_fmt)
            else:
                sheet.write(row_idx, 0, code, text_fmt)
                sheet.write(row_idx, 1, name, text_fmt)

            ob, obt = to_balance_and_type(row["initial_debit"], row["initial_credit"])
            pb, pbt = to_balance_and_type(row["period_debit"], row["period_credit"])
            cb, cbt = to_balance_and_type(row["ending_debit"], row["ending_credit"])

            def write_num(col, val):
                sheet.write_number(row_idx, col, val, pos_fmt if val >= 0 else neg_fmt)

            write_num(2, ob)
            sheet.write(row_idx, 3, obt, text_fmt)

            write_num(4, pb)
            sheet.write(row_idx, 5, pbt, text_fmt)

            write_num(6, cb)
            sheet.write(row_idx, 7, cbt, text_fmt)

            row_idx += 1


class CustomDynamicLedgerPdfReport(models.AbstractModel):
    _name = "report.account_ledger.custom_dynamic_ledger_rep"

    def _get_report_values(self, docids, data=None):
        wizard = self.env["custom.dynamic.ledger.report.wizard"].browse(docids)
        wizard.ensure_one()

        report_rows = wizard.generate_balance_report()
        today = datetime.today()

        return {
            "doc_ids": wizard.ids,
            "doc_model": wizard._name,
            "docs": report_rows,
            "company_name": wizard.company_id.name,
            "date_start": wizard.date_start,
            "date_end": wizard.date_end,
            "main_head": wizard.main_head,
            "department_name": wizard.department_id.name if wizard.department_id else "",
            "section_name": wizard.section_id.name if wizard.section_id else "",
            "project_name": wizard.project_id.name if wizard.project_id else "",
            "employee_name": wizard.employee_id.name if wizard.employee_id else "",
            "asset_name": wizard.asset_id.name if wizard.asset_id else "",
            "report_date": today.strftime("%b-%d-%Y"),
        }
