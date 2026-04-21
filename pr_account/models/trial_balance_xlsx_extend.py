from odoo import models, _
from datetime import datetime


class AccountReportXlsxCustom(models.AbstractModel):
    _inherit = "account.report"

    def _inject_report_into_xlsx_sheet(self, options, workbook, sheet):
        print(f'haaaaaaaaaaaaaaaaaaaaaa{self.custom_handler_model_id.model}')

        if self.custom_handler_model_id.model != "account.trial.balance.report.handler":
            return super()._inject_report_into_xlsx_sheet(options, workbook, sheet)

        def write_with_colspan(sheet, x, y, value, colspan, style):
            if colspan == 1:
                sheet.write(y, x, value, style)
            else:
                sheet.merge_range(y, x, y, x + colspan - 1, value, style)

        # -------- FORMATS (based on Odoo’s original) --------
        default_format_props = {
            'font_name': 'Arial',
            'font_color': '#666666',
            'font_size': 12,
            'num_format': '#,##0.00',
        }
        text_format_props = {
            'font_name': 'Arial',
            'font_color': '#666666',
            'font_size': 12,
        }
        date_format_props = {
            'font_name': 'Arial',
            'font_color': '#666666',
            'font_size': 12,
            'num_format': 'yyyy-mm-dd',
        }

        title_format = workbook.add_format({
            'font_name': 'Arial',
            'bold': True,
            'font_color': '#FFFFFF',
            'bg_color': '#29608F',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
        })

        # Our blue header formats
        top_header_format = workbook.add_format({
            'font_name': 'Arial',
            'bold': True,
            'font_color': '#FFFFFF',
            'bg_color': '#29608F',
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 13,
            'border': 1,
            'top': 1,
            'bottom': 1,
            'left': 1,
            'right': 1,
        })
        header_format = workbook.add_format({
            'font_name': 'Arial',
            'bold': True,
            'font_color': '#FFFFFF',
            'bg_color': '#29608F',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
        })

        workbook_formats = {
            0: {
                'default': workbook.add_format({**default_format_props, 'bold': True, 'font_size': 13, 'bottom': 6}),
                'text': workbook.add_format({**text_format_props, 'bold': True, 'font_size': 13, 'bottom': 6}),
                'date': workbook.add_format({**date_format_props, 'bold': True, 'font_size': 13, 'bottom': 6}),
                'total': workbook.add_format({**default_format_props, 'bold': True, 'font_size': 13, 'bottom': 6}),
            },
            1: {
                'default': workbook.add_format({**default_format_props, 'bold': True, 'font_size': 13, 'bottom': 1}),
                'text': workbook.add_format({**text_format_props, 'bold': True, 'font_size': 13, 'bottom': 1}),
                'date': workbook.add_format({**date_format_props, 'bold': True, 'font_size': 13, 'bottom': 1}),
                'total': workbook.add_format({**default_format_props, 'bold': True, 'font_size': 13, 'bottom': 1}),
                'default_indent': workbook.add_format(
                    {**default_format_props, 'bold': True, 'font_size': 13, 'bottom': 1, 'indent': 1}),
                'date_indent': workbook.add_format(
                    {**date_format_props, 'bold': True, 'font_size': 13, 'bottom': 1, 'indent': 1}),
            },
            2: {
                'default': workbook.add_format({**default_format_props, 'bold': True}),
                'text': workbook.add_format({**text_format_props, 'bold': True}),
                'date': workbook.add_format({**date_format_props, 'bold': True}),
                'initial': workbook.add_format(default_format_props),
                'total': workbook.add_format({**default_format_props, 'bold': True}),
                'default_indent': workbook.add_format({**default_format_props, 'bold': True, 'indent': 2}),
                'date_indent': workbook.add_format({**date_format_props, 'bold': True, 'indent': 2}),
                'initial_indent': workbook.add_format({**default_format_props, 'indent': 2}),
                'total_indent': workbook.add_format({**default_format_props, 'bold': True, 'indent': 1}),
            },
            'default': {
                'default': workbook.add_format(default_format_props),
                'text': workbook.add_format(text_format_props),
                'date': workbook.add_format(date_format_props),
                'total': workbook.add_format(default_format_props),
                'default_indent': workbook.add_format({**default_format_props, 'indent': 2}),
                'date_indent': workbook.add_format({**date_format_props, 'indent': 2}),
                'total_indent': workbook.add_format({**default_format_props, 'indent': 2}),
            },
        }

        def get_format(content_type='default', level='default'):
            if isinstance(level, int) and level not in workbook_formats:
                workbook_formats[level] = {
                    **workbook_formats['default'],
                    'default_indent': workbook.add_format({**default_format_props, 'indent': level}),
                    'date_indent': workbook.add_format({**date_format_props, 'indent': level}),
                    'total_indent': workbook.add_format({**default_format_props, 'bold': True, 'indent': level - 1}),
                }

            level_formats = workbook_formats[level]
            if '_indent' in content_type and not level_formats.get(content_type):
                return level_formats.get(
                    'default_indent',
                    level_formats.get(content_type.removesuffix('_indent'), level_formats['default']),
                )
            return level_formats.get(content_type, level_formats['default'])

        # -------- ORIGINAL ODOO LINES FETCHING --------
        print_mode_self = self.with_context(no_format=True)
        lines = self._filter_out_folded_children(print_mode_self._get_lines(options))

        account_lines_split_names = {}
        for line in lines:
            line_model = self._get_model_info_from_id(line['id'])[0]
            if line_model == 'account.account':
                account_lines_split_names[line['id']] = self.env['account.account']._split_code_name(line['name'])

        if len(account_lines_split_names) > 0:
            sheet.set_column(0, 0, 11)
            sheet.set_column(1, 1, 50)
        else:
            sheet.set_column(0, 0, 50)

        original_x_offset = 1 if len(account_lines_split_names) > 0 else 0

        # -------- 🔵 OUR CUSTOM TOP HEADER (3 ROWS) --------
        # span across all columns
        last_col = original_x_offset + len(options['columns'])

        company = self._get_sender_company_for_export(options)
        vat = company.vat or ''
        date_from = options['date']['date_from']
        date_to = options['date']['date_to']

        period_str = "Period {} - {}".format(
            datetime.strptime(date_from, '%Y-%m-%d').strftime('%d/%m/%Y'),
            datetime.strptime(date_to, '%Y-%m-%d').strftime('%d/%m/%Y'),
        )

        # Row 0: Company + VAT
        sheet.merge_range(0, 0, 0, last_col, f"{company.name} - VAT Number {vat}", top_header_format)
        # Row 1: Report title (generic: self.name → “Trial Balance”, “Balance Sheet”, etc.)
        sheet.merge_range(1, 0, 1, last_col, self.name or _("Report"), top_header_format)
        # Row 2: Period
        sheet.merge_range(2, 0, 2, last_col, period_str, top_header_format)

        y_offset = 3
        x_offset = original_x_offset + 1

        # -------- COLUMN GROUP HEADERS (Odoo logic) --------
        column_headers_render_data = self._get_column_headers_render_data(options)
        for header_level_index, header_level in enumerate(options['column_headers']):
            if header_level_index == 0: # critical override the odoos default TB header to pop first header
                continue
            for header_to_render in header_level * column_headers_render_data['level_repetitions'][header_level_index]:
                colspan = header_to_render.get('colspan',
                                               column_headers_render_data['level_colspan'][header_level_index])
                name = header_to_render.get('name', '') or ''
                # ALWAYS fill empty header cells with "" to avoid white gaps
                write_with_colspan(sheet, x_offset, y_offset, name or "", colspan, header_format)
                x_offset += colspan

            # Growth column (if exists)
            if options['show_growth_comparison']:
                write_with_colspan(sheet, x_offset, y_offset, "%", 1, header_format)

            y_offset += 1
            x_offset = original_x_offset + 1

        if column_headers_render_data['custom_subheaders']:
            for subheader in column_headers_render_data['custom_subheaders']:
                colspan = subheader.get('colspan', 1)
                write_with_colspan(
                    sheet,
                    x_offset,
                    y_offset,
                    subheader.get('name', ' ') or " ",
                    colspan,
                    title_format,
                )
                x_offset += colspan
            y_offset += 1  # only move down if we actually wrote a row

        # in all cases reset x_offset
        x_offset = original_x_offset + 1

        # -------- "Code" / "Account Name" row (here we rename “Code” → “Account code”) --------


        # Final per-column header row
        # ---------- CUSTOM FINAL COLUMN HEADERS ----------
        # Make header row color and style #29608F

        # These will ALWAYS be the final 6 columns (matching desired output)
        final_headers = [
            "Opening - Debit",
            "Opening - Credit",
            "Transaction - Debit",
            "Transaction - Credit",
            "Closing - Debit",
            "Closing - Credit",
        ]

        # First write Account code / name (same style)
        sheet.write(y_offset, x_offset - 2, "Account code", header_format)
        sheet.write(y_offset, x_offset - 1, "Account Name", header_format)

        # Now write our 6 custom headers
        col_index = x_offset
        for name in final_headers:
            sheet.write(y_offset, col_index, name, header_format)
            col_index += 1
        # ---------- AUTO COLUMN WIDTHS ----------
        sheet.set_column(0, 0, 14)  # Account code
        sheet.set_column(1, 1, 40)  # Account name

        num_start_col = original_x_offset + 1
        num_end_col = last_col

        for col in range(num_start_col, num_end_col + 1):
            sheet.set_column(col, col, 16)

        # Move to next row for the data
        y_offset += 1

        # -------- LINES (Odoo’s original logic, unchanged) --------
        if options.get('order_column'):
            lines = self.sort_lines(lines, options)

        max_level = max(line.get('level', -1) for line in lines) if lines else -1
        if max_level in {0, 1, 2}:
            for wb_format in (s for s in workbook_formats[max_level] if 'total' not in s):
                workbook_formats[max_level][wb_format].set_bold(False)



        for y, line in enumerate(lines):
            level = line.get('level')
            if level == 0:
                y_offset += 1
            elif not level:
                level = 'default'

            line_id = self._parse_line_id(line.get('id'))
            is_initial_line = line_id[-1][0] == 'initial' if line_id else False
            is_total_line = line_id[-1][0] == 'total' if line_id else False

            cell_type, cell_value = self._get_cell_type_value(line)
            account_code_cell_format = get_format('text', level)

            if cell_type == 'date':
                cell_format = get_format('date_indent', level)
            elif is_initial_line:
                cell_format = get_format('initial_indent', level)
            elif is_total_line:
                cell_format = get_format('total_indent', level)
            else:
                cell_format = get_format('default_indent', level)

            x_offset = original_x_offset + 1
            if lines[y]['id'] in account_lines_split_names:
                code, name = account_lines_split_names[lines[y]['id']]
                sheet.write(y + y_offset, 0, code, account_code_cell_format)
                sheet.write(y + y_offset, 1, name, cell_format)
            else:
                write_method = sheet.write_datetime if cell_type == 'date' else sheet.write
                write_method(y + y_offset, original_x_offset, cell_value, cell_format)

                if 'parent_id' in line and line['parent_id'] in account_lines_split_names:
                    sheet.write(y + y_offset, 1 + original_x_offset, account_lines_split_names[line['parent_id']][0],
                                account_code_cell_format)
                elif account_lines_split_names:
                    sheet.write(y + y_offset, 1 + original_x_offset, "", account_code_cell_format)

            columns = line['columns']
            if options['show_growth_comparison'] and 'growth_comparison_data' in line:
                columns += [line['growth_comparison_data']]
            for x, column in enumerate(columns, start=x_offset):
                cell_type, cell_value = self._get_cell_type_value(column)

                if cell_type == 'date':
                    cell_format = get_format('date', level)
                elif is_initial_line:
                    cell_format = get_format('initial', level)
                elif is_total_line:
                    cell_format = get_format('total', level)
                else:
                    cell_format = get_format('default', level)

                write_method = sheet.write_datetime if cell_type == 'date' else sheet.write
                write_method(y + y_offset, x + line.get('colspan', 1) - 1, cell_value, cell_format)
