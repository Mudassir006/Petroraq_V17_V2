from odoo import models
import string


class PayrollReport(models.AbstractModel):
    _name = 'report.xlsx_payroll_report.xlsx_payroll_report'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, lines):

        # ======================
        # Formats (styling only - NO logic changes)
        # ======================
        blue_title = workbook.add_format({
            'bold': True, 'font_size': 14,
            'align': 'center', 'valign': 'vcenter',
            'bg_color': '#0B2A8F', 'font_color': 'white',
            'border': 1
        })
        blue_subtitle = workbook.add_format({
            'bold': True, 'font_size': 12,
            'align': 'center', 'valign': 'vcenter',
            'bg_color': '#0B2A8F', 'font_color': 'white',
            'border': 1
        })
        header_blue = workbook.add_format({
            'bold': True, 'font_size': 10,
            'align': 'center', 'valign': 'vcenter',
            'bg_color': '#0B2A8F', 'font_color': 'white',
            'border': 1
        })
        cell_txt = workbook.add_format({
            'font_size': 10,
            'align': 'center', 'valign': 'vcenter',
            'border': 1,
            'text_wrap': True,
        })
        cell_txt_left = workbook.add_format({
            'font_size': 10,
            'align': 'left', 'valign': 'vcenter',
            'border': 1,
            'text_wrap': True,
        })
        cell_money = workbook.add_format({
            'font_size': 10,
            'align': 'center', 'valign': 'vcenter',
            'border': 1,
            # show negatives in red with parentheses (styling only)
            'num_format': '#,##0.00;[Red]#,##0.00'
        })
        cell_money_alt = workbook.add_format({
            'font_size': 10,
            'align': 'center', 'valign': 'vcenter',
            'border': 1,
            'bg_color': '#F3F6FA',
            'num_format': '#,##0.00;[Red]#,##0.00'
        })
        cell_txt_alt = workbook.add_format({
            'font_size': 10,
            'align': 'center', 'valign': 'vcenter',
            'border': 1,
            'bg_color': '#F3F6FA'
        })
        cell_txt_left_alt = workbook.add_format({
            'font_size': 10,
            'align': 'left', 'valign': 'vcenter',
            'border': 1,
            'bg_color': '#F3F6FA',
            'text_wrap': True,
        })
        total_blue_txt = workbook.add_format({
            'bold': True, 'font_size': 10,
            'align': 'center', 'valign': 'vcenter',
            'bg_color': '#0B2A8F', 'font_color': 'white',
            'border': 1
        })
        total_blue_money = workbook.add_format({
            'bold': True, 'font_size': 10,
            'align': 'center', 'valign': 'vcenter',
            'bg_color': '#0B2A8F', 'font_color': 'white',
            'border': 1,
            'num_format': '#,##0.00'
        })

        # ======================
        # Helper for Excel column letters
        # ======================
        def xl_col_to_name(idx0):
            """0-based -> Excel letters"""
            name = ""
            n = idx0 + 1
            while n:
                n, rem = divmod(n - 1, 26)
                name = chr(65 + rem) + name
            return name

        # ======================
        # Fetch used structures
        # ======================
        used_structures = []
        seen_ids = set()
        for sal_structure in lines.slip_ids.struct_id:
            if sal_structure.id not in seen_ids:
                used_structures.append([sal_structure.id, sal_structure.name])
                seen_ids.add(sal_structure.id)

        struct_count = 1
        for used_struct in used_structures:
            sheet = workbook.add_worksheet(str(struct_count) + ' - ' + str(used_struct[1]))

            # Print & view options (styling only)
            sheet.set_landscape()
            sheet.set_paper(9)  # A4
            sheet.fit_to_pages(1, 0)
            sheet.hide_gridlines(2)

            # Page setup / print styling
            sheet.set_landscape()
            sheet.fit_to_pages(1, 0)
            sheet.set_print_scale(100)
            sheet.set_margins(left=0.3, right=0.3, top=0.4, bottom=0.4)
            sheet.hide_gridlines(2)

            # Freeze panes below header row (title rows + header row)
            sheet.freeze_panes(6, 0)

            cols = list(string.ascii_uppercase) + [
                'AA', 'AB', 'AC', 'AD', 'AE', 'AF', 'AG', 'AH', 'AI', 'AJ', 'AK', 'AL',
                'AM', 'AN', 'AO', 'AP', 'AQ', 'AR', 'AS', 'AT', 'AU', 'AV', 'AW', 'AX', 'AY', 'AZ'
            ]

            rules = []
            col_no = 3  # SHIFTED by +1 because we will add Emp ID, Name, Dept in cols 0..2

            # Salary rules (KEEP your logic)
            salary_rule_ids = lines.slip_ids.line_ids.mapped("salary_rule_id")
            order = [
                "Basic Salary",
                "Accommodation",
                "Transportation",
                "Food",
                "Fixed Overtime",
                "Overtime",
                "Annual Time Off DED",
                "Sick Time Off DED",
                "Annual Time Off",
                "Sick Time Off",
                "Absence",
                "Late In",
                # "Unpaid Leave",
                "Early Checkout",
                "Gross",
                "Reimbursement",
                "Advance Allowances",
            ]

            salary_rule_ids = salary_rule_ids.filtered(lambda s: s.name in order)

            order_map = {name: index for index, name in enumerate(order)}
            sorted_rules = sorted(salary_rule_ids, key=lambda x: order_map.get(x.name, 9999))

            for rule in sorted_rules:
                row = [None, None, None, None, None]
                row[0] = col_no
                row[1] = rule.code
                row[2] = rule.name
                col_title = str(cols[col_no]) + ':' + str(cols[col_no])
                row[3] = col_title
                row[4] = 12 if len(rule.name) < 8 else (len(rule.name) + 2)
                rules.append(row)
                col_no += 1

            # Dedicated additional columns (normalized / explicit ordering)
            extra_cols = [
                ("REIMBURSEMENT199", "Reimbursement"),
                ("GOSI_COMP_ADD", "GOSI Company Contribution"),
                ("GOSI_COMP_DED", "GOSI Company Deduction"),
                ("GOSI_EMP", "GOSI Employee Deduction"),
                ("NET", "Net Salary"),
            ]
            for code, name in extra_cols:
                if any(r[1] == code for r in rules):
                    continue
                rowx = [None, None, None, None, None]
                rowx[0] = col_no
                rowx[1] = code
                rowx[2] = name
                rowx[3] = f"{cols[col_no]}:{cols[col_no]}"
                rowx[4] = 24
                rules.append(rowx)
                col_no += 1

            full_order = [
                "Basic Salary",
                "Accommodation",
                "Transportation",
                "Food",
                "Fixed Overtime",
                "Overtime",
                "Annual Time Off DED",
                "Sick Time Off DED",
                "Annual Time Off",
                "Sick Time Off",
                "Absence",
                "Late In",
                "Unpaid Leave",
                "Early Checkout",
                "GOSI Company Contribution",
                "Gross",
                "Reimbursement",
                "Advance Allowances",
                "GOSI Company Deduction",
                "GOSI Employee Deduction",
                "Net Salary",
            ]
            order_map = {name: index for index, name in enumerate(full_order)}
            rules = sorted(rules, key=lambda r: order_map.get(r[2], 9999))
            for idx, row in enumerate(rules):
                row[0] = 3 + idx
                row[3] = f"{cols[row[0]]}:{cols[row[0]]}"
            col_no = 3 + len(rules)

            # # --- Add Saudi GOSI virtual columns (display only) ---
            # # to hide comment the below code including loop these will than not be included
            # extra_cols = [
            #     ("GOSI_COMP_ADD", "GOSI Company Contribution"),
            #     ("GOSI_EMP", "GOSI Employee Deduction"),
            #     ("GOSI_COMP_DED", "GOSI Company Deduction"),
            # ]
            # for code, name in extra_cols:
            #     rowx = [None, None, None, None, None]
            #     rowx[0] = col_no
            #     rowx[1] = code
            #     rowx[2] = name
            #     col_title = f"{cols[col_no]}:{cols[col_no]}"
            #     rowx[3] = col_title
            #     rowx[4] = 22
            #     rules.append(rowx)
            #     col_no += 1

            # Report details (KEEP your logic)
            batch_period = ""
            company_name = ""
            for item in lines.slip_ids:
                if item.struct_id.id == used_struct[0]:
                    batch_period = f"{item.date_from.strftime('%d %B %Y')}  To  {item.date_to.strftime('%d %B %Y')}"
                    company_name = item.company_id.name or ""
                    break

            last_col = col_no - 1

            # ======================
            # Title bars (PDF-like)
            # ======================
            sheet.set_row(0, 22)
            sheet.merge_range(0, 0, 0, last_col, company_name, blue_title)

            sheet.set_row(1, 20)
            sheet.merge_range(1, 0, 1, last_col, f"Payroll Month {item.date_to.strftime('%B %Y')}", blue_subtitle)

            sheet.set_row(2, 20)
            sheet.merge_range(2, 0, 2, last_col, f"For the Period {batch_period}", blue_subtitle)

            # Optional small info row (kept but styled lightly)
            sheet.set_row(3, 16)
            sheet.write(3, 0, "Payslip Structure:", cell_txt)
            sheet.merge_range(3, 1, 3, 2, used_struct[1], cell_txt)

            # ======================
            # Table header row
            # ======================
            header_row = 5
            sheet.set_row(header_row, 18)

            sheet.write(header_row, 0, 'Employee ID', header_blue)
            sheet.write(header_row, 1, 'Employee Name', header_blue)
            sheet.write(header_row, 2, 'Department', header_blue)
            for rule in rules:
                sheet.write(header_row, rule[0], rule[2], header_blue)

            # Autofilter on header row (styling / usability)
            sheet.autofilter(header_row, 0, header_row, last_col)

            # Column widths
            sheet.set_column('A:A', 12)
            sheet.set_column('B:B', 28)
            sheet.set_column('C:C', 18)
            for rule in rules:
                sheet.set_column(rule[3], rule[4])

            # ======================
            # Hide legacy GOSI column only
            # ======================
            HIDE_CODES = {"GOSI"}
            HIDE_TITLES = set()

            for r in rules:
                code = r[1]
                title = r[2]
                if code in HIDE_CODES or title in HIDE_TITLES:
                    col_idx = r[0]
                    sheet.set_column(col_idx, col_idx, 0.1, None, {'hidden': True})

            # ======================
            # Data rows (same logic, just styled)
            # ======================
            row = header_row + 1
            first_data_row = row  # for totals formula
            has_payslips = False

            for slip in lines.slip_ids:
                if slip.struct_id.id != used_struct[0]:
                    continue

                has_payslips = True
                is_alt = ((row - first_data_row) % 2 == 1)

                txt_fmt = cell_txt_alt if is_alt else cell_txt
                txt_left_fmt = cell_txt_left_alt if is_alt else cell_txt_left
                money_pos_fmt = cell_money_alt if is_alt else cell_money
                money_neg_fmt = cell_money_alt if is_alt else cell_money  # keep same format; Excel shows minus

                sheet.write(row, 0, slip.employee_id.code or '', txt_fmt)
                sheet.write(row, 1, slip.employee_id.name or '', txt_left_fmt)
                sheet.write(row, 2, slip.employee_id.department_id.name or '', txt_left_fmt)

                # Fill all rule columns (by code)
                # (Small perf improvement: build dict {code: amount} once per slip)
                slip_amount_by_code = {}
                for l in slip.line_ids:
                    slip_amount_by_code[l.code] = slip_amount_by_code.get(l.code, 0.0) + (l.amount or 0.0)

                # Normalize GOSI portions to dedicated report columns.
                # Legacy payslips may only have "GOSI" as a combined deduction.
                gosi_company_add = (
                    slip_amount_by_code.get("GOSI_COMP_ADD", 0.0) + slip_amount_by_code.get("GOSIALLOW", 0.0)
                )
                legacy_gosi_ded = slip_amount_by_code.get("GOSI", 0.0)
                gosi_employee_ded = slip_amount_by_code.get("GOSI_EMP", 0.0)
                gosi_company_ded = slip_amount_by_code.get("GOSI_COMP_DED", 0.0)

                if not gosi_employee_ded and not gosi_company_ded and legacy_gosi_ded:
                    gosi_company_ded = -gosi_company_add
                    gosi_employee_ded = legacy_gosi_ded - gosi_company_ded
                else:
                    gosi_company_ded += legacy_gosi_ded

                slip_amount_by_code["GOSI_COMP_ADD"] = gosi_company_add
                slip_amount_by_code["GOSI_EMP"] = gosi_employee_ded
                slip_amount_by_code["GOSI_COMP_DED"] = gosi_company_ded

                DEDUCTION_CODES = {
                    "ABS", "LATE", "ECO", "LEAVE90", "DIFFT", "UNPAID", "PAID87",
                    "SICKTO89", "BTD",
                    # add your own deduction rule codes here if needed
                    "GOSI", "GOSI_EMP", "GOSI_COMP_DED",
                }

                for rule in rules:
                    val = slip_amount_by_code.get(rule[1], 0.0)
                    fmt = money_pos_fmt if val >= 0 else money_neg_fmt
                    sheet.write(row, rule[0], val, fmt)

                row += 1

            if has_payslips:
                total_row = row
                sheet.write(total_row, 0, 'Total', total_blue_txt)
                sheet.write(total_row, 1, '', total_blue_txt)
                sheet.write(total_row, 2, '', total_blue_txt)

                # sum each numeric column from col 3..last_col
                for c in range(3, last_col + 1):
                    col_letter = xl_col_to_name(c)
                    # Excel rows are 1-based:
                    start = first_data_row + 1
                    end = total_row
                    sheet.write_formula(
                        total_row, c,
                        f"=SUM({col_letter}{start}:{col_letter}{end})",
                        total_blue_money
                    )

            struct_count += 1