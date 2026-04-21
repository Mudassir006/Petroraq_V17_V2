from odoo import models
from datetime import datetime, date, timedelta
import base64
from io import BytesIO
from reportlab.lib.units import mm


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def _get_report_base_filename(self):
        self.ensure_one()
        if self.state in ("draft", "sent") or getattr(self, "is_rfq_record", False):
            return f"Request for Quotation - {self.name}"
        return f"Purchase Order - {self.name}"

    def action_send_purchase_order_email(self):
        """Open the standard Compose wizard pre-filled with our custom body and recipients."""
        self.ensure_one()

        # Header fields (read defensively for custom attrs)
        vendor_name = self.partner_id.display_name or ''
        vendor_ref = self.partner_ref or ''
        rfq_origin = self.name or ''
        # Expected Arrival from PO planning date
        planned_val = self._get_expected_arrival_from_quotation() or self.date_planned or ''
        planned = self._format_expected_arrival(planned_val)

        # Persist back to PO so the backend reflects the quotation's expected arrival
        planned_dt = self._coerce_to_datetime(planned_val)
        if planned_dt and (not self.date_planned or self.date_planned != planned_dt):
            try:
                self.write({'date_planned': planned_dt})
            except Exception:
                # Non-blocking; continue even if write fails
                pass

        project_name = getattr(self, 'project_id', False) and self.project_id.display_name or ''
        budget_type = getattr(self, 'budget_type', '') or ''
        budget_code = getattr(self, 'budget_code', '') or ''

        total_amount = getattr(self, 'amount_total', 0.0)

        # Build HTML sections
        summary_html = f"""
        <h3 style="margin-top:16px;">Summary</h3>
        <table border="0" cellspacing="0" cellpadding="4" style="width:100%;">
          <tr>
            <td style="width:25%;"><strong>Vendor</strong></td>
            <td>{vendor_name}</td>
            <td style="width:25%;"><strong>Vendor Ref</strong></td>
            <td>{vendor_ref}</td>
          </tr>
          <tr>
            <td><strong>RFQ Origin</strong></td>
            <td>{rfq_origin}</td>
            <td><strong>Expected Arrival</strong></td>
            <td>{planned}</td>
          </tr>
          <tr>
            <td><strong>Project</strong></td>
            <td>{project_name}</td>
            <td><strong>Quotation Ref No</strong></td>
            <td>{rfq_origin}</td>
          </tr>
        </table>
        """

        # Custom quotation lines (if your PO has custom_line_ids)
        custom_lines = getattr(self, 'custom_line_ids', False)
        custom_lines_html = ''
        if custom_lines:
            rows = []
            subtotal_sum = 0.0
            for ln in custom_lines:
                qty_val = ln.quantity or 0.0
                price_val = ln.price_unit or 0.0
                subtotal_sum += price_val * qty_val
                rows.append(
                    f"<tr>"
                    f"<td>{ln.name or ''}</td>"
                    f"<td>{qty_val}</td>"
                    f"<td>{ln.type or ''}</td>"
                    f"<td>{ln.unit or ''}</td>"
                    f"<td>{price_val}</td>"
                    f"</tr>"
                )
            currency = getattr(self, 'currency_id', False)
            symbol = (currency and currency.symbol) or ''
            amount_str = f"{symbol} {subtotal_sum:,.2f}".strip()
            custom_lines_html = (
                    "<h3 style=\"margin-top:24px;\">Quotation Lines</h3>"
                    "<table border=\"1\" cellspacing=\"0\" cellpadding=\"4\" style=\"border-collapse: collapse; width: 100%;\">"
                    "<thead><tr style=\"background-color:#f2f2f2;\">"
                    "<th>Description</th><th>Quantity</th><th>Type</th><th>Unit</th><th>Unit Price</th>"
                    "</tr></thead><tbody>" + ''.join(rows) + "</tbody></table>"
                                                             f"<div style=\"display:flex; justify-content:flex-end; margin-top:10px;\">"
                                                             f"  <div style=\"min-width:260px; text-align:right;\">"
                                                             f"    <span style=\"margin-right:12px;\"><strong>Subtotal</strong></span>"
                                                             f"    <span>{amount_str}</span>"
                                                             f"  </div>"
                                                             f"</div>"
            )

        # Standard PO lines (commented out per request)
        # po_rows = []
        # for line in self.order_line:
        #     po_rows.append(
        #         f"<tr>"
        #         f"<td>{line.product_id.display_name or ''}</td>"
        #         f"<td>{line.name or ''}</td>"
        #         f"<td>{line.product_qty or 0}</td>"
        #         f"<td>{line.price_unit or 0}</td>"
        #         f"<td>{line.price_subtotal or 0}</td>"
        #         f"</tr>"
        #     )
        # po_lines_html = (
        #     "<h3 style=\"margin-top:24px;\">Purchase Order Lines</h3>"
        #     "<table border=\"1\" cellspacing=\"0\" cellpadding=\"4\" style=\"border-collapse: collapse; width: 100%;\">"
        #     "<thead><tr style=\"background-color:#f2f2f2;\">"
        #     "<th>Product</th><th>Description</th><th>Quantity</th><th>Unit Price</th><th>Subtotal</th>"
        #     "</tr></thead><tbody>" + ''.join(po_rows) + "</tbody></table>"
        # )
        po_lines_html = ""

        # Terms & conditions from purchase order fields
        terms = self._get_terms_section()
        terms_html = terms.get('html', '')

        body = f"""
        <p>Dear Vendor,</p>
        <p>Please find below the details of Purchase Order <strong>{self.name}</strong>:</p>
        {summary_html}
        {custom_lines_html}
        {po_lines_html}
        {terms_html}
        <p style=\"margin-top:16px;\">Regards,<br/>{self.env.user.name}</p>
        """

        subject = f"Purchase Order: {self.name}"

        # Recipients: partner_id + optional vendor_ids (if present on model)
        partner_ids = []
        if self.partner_id:
            partner_ids.append(self.partner_id.id)
        extra_vendor_ids = getattr(self, 'vendor_ids', False) and self.vendor_ids.ids or []
        for vid in extra_vendor_ids:
            if vid not in partner_ids:
                partner_ids.append(vid)

        compose_form = self.env.ref('mail.email_compose_message_wizard_form')
        mail_template = self.env.ref(
            'pr_custom_purchase.purchase_order_custom_email_template',
            raise_if_not_found=False,
        )
        ctx = {
            'default_model': 'purchase.order',
            'default_res_ids': self.ids,
            'default_composition_mode': 'comment',
            'default_template_id': mail_template.id if mail_template else None,
            'default_use_template': bool(mail_template),
            'default_subject': subject,
            'default_body': body,
            'default_partner_ids': partner_ids,
            'default_email_layout_xmlid': 'mail.mail_notification_light',
            'force_email': True,
            'mark_rfq_as_sent': True,
        }

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    def _build_email_pdf_bytes(self):
        """Create email PDF with existing custom content and purchase-report style header/footer."""
        try:
            from odoo.modules.module import get_module_resource
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.utils import ImageReader
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        except Exception:
            return b''

        self.ensure_one()
        terms = self._get_terms_section()

        # Match module report paper format (250mm x 370mm)
        page_width = 250 * mm
        page_height = 370 * mm

        # Resolve static assets used by report header/footer templates
        header_img = get_module_resource('pr_custom_purchase', 'static', 'src', 'img', 'white_header.jpg')
        footer_img = get_module_resource('pr_custom_purchase', 'static', 'src', 'img', 'blue_footer.jpeg')
        arabic_font_path = get_module_resource(
            'pr_custom_purchase',
            'static',
            'src',
            'font',
            'droid-arabic-naskh-regular',
            'Droid Arabic Naskh Regular',
            'Droid Arabic Naskh Regular.ttf',
        )

        try:
            header_reader = ImageReader(header_img) if header_img else None
        except Exception:
            header_reader = None
        try:
            footer_reader = ImageReader(footer_img) if footer_img else None
        except Exception:
            footer_reader = None

        arabic_font = None
        try:
            if arabic_font_path:
                arabic_font = 'DroidArabicNaskh'
                pdfmetrics.registerFont(TTFont(arabic_font, arabic_font_path))
        except Exception:
            arabic_font = None

        # Keep body area clear from larger branded header/footer
        left_margin = 18 * mm
        right_margin = 18 * mm
        top_margin = 70 * mm
        bottom_margin = 52 * mm

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=(page_width, page_height),
            leftMargin=left_margin,
            rightMargin=right_margin,
            topMargin=top_margin,
            bottomMargin=bottom_margin,
        )
        styles = getSampleStyleSheet()
        elements = []

        def _draw_header_footer(canvas, _doc):
            canvas.saveState()

            # Header image like custom_invoice_header_layout (full width, taller)
            if header_reader:
                header_h = 42 * mm
                canvas.drawImage(
                    header_reader,
                    0,
                    page_height - header_h,
                    width=page_width,
                    height=header_h,
                    preserveAspectRatio=False,
                    mask='auto',
                )

            # Footer disclaimer block similar to custom_invoice_footer_layout
            disclaimer_y = 27 * mm
            canvas.setStrokeColorRGB(0.19, 0.31, 0.51)
            canvas.setLineWidth(0.8)
            canvas.line(left_margin, disclaimer_y + 11 * mm, page_width - right_margin, disclaimer_y + 11 * mm)

            canvas.setFillColorRGB(0, 0, 0)
            canvas.setFont('Helvetica', 8)
            en_text = 'This is computer generated document, no signature and stamp required'
            canvas.drawString(left_margin, disclaimer_y + 7 * mm, en_text)

            ar_text = 'هذه وثيقة تم إنشاؤها بواسطة الكمبيوتر، ولا تتطلب توقيعًا أو ختمًا'
            if arabic_font:
                try:
                    canvas.setFont(arabic_font, 8)
                    tw = canvas.stringWidth(ar_text, arabic_font, 8)
                    canvas.drawString(page_width - right_margin - tw, disclaimer_y + 7 * mm, ar_text)
                except Exception:
                    pass

            # Footer image as full-width band
            if footer_reader:
                footer_h = 17 * mm
                canvas.drawImage(
                    footer_reader,
                    0,
                    8 * mm,
                    width=page_width,
                    height=footer_h,
                    preserveAspectRatio=False,
                    mask='auto',
                )

            # Page counter centered at bottom
            canvas.setFillColorRGB(0.07, 0.19, 0.38)
            canvas.setFont('Helvetica', 8)
            page_txt = f'Page: {canvas.getPageNumber()}'
            tw = canvas.stringWidth(page_txt, 'Helvetica', 8)
            canvas.drawString((page_width - tw) / 2.0, 4 * mm, page_txt)

            canvas.restoreState()

        title = Paragraph(f"Your Purchase Order <b>{self.name}</b>", styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 12))

        elements.append(Paragraph("Dear Vendor,", styles['Normal']))
        elements.append(Spacer(1, 8))
        elements.append(Paragraph(f"Please find below the details of Purchase Order <b>{self.name}</b>:", styles['Normal']))
        elements.append(Spacer(1, 12))

        def _val(v):
            return v if v is not None else ''

        data_summary = [
            ['Vendor', _val(self.partner_id.display_name or ''), 'Vendor Ref', _val(self.partner_ref or '')],
            ['RFQ Origin', _val(self.name), 'Expected Arrival', _val(
                self._format_expected_arrival(self._get_expected_arrival_from_quotation() or self.date_planned or ''))],
            ['Project', _val(getattr(self.project_id, 'display_name', '')), 'Quotation Ref No', _val(self.name)],
        ]
        t_summary = Table(data_summary, colWidths=[90, 170, 110, 170])
        t_summary.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(Paragraph('Summary', styles['Heading2']))
        elements.append(t_summary)
        elements.append(Spacer(1, 12))

        rows = [['Description', 'Quantity', 'Type', 'Unit', 'Unit Price']]
        source_lines = getattr(self, 'custom_line_ids', False) or self.order_line
        subtotal_sum = 0.0
        for ln in source_lines:
            desc = getattr(ln, 'name', '')
            qty = getattr(ln, 'quantity', None)
            if qty is None:
                qty = getattr(ln, 'product_qty', 0.0)
            typ = getattr(ln, 'type', '')
            unit = getattr(ln, 'unit', '')
            if not unit:
                uom = getattr(ln, 'product_uom', False)
                unit = uom and uom.name or ''
            price = getattr(ln, 'price_unit', 0.0)
            subtotal_sum += (price or 0.0) * (qty or 0.0)
            rows.append([desc or '', f"{qty}", typ or '', unit or '', f"{price}"])

        t_lines = Table(rows, colWidths=[200, 70, 70, 70, 100])
        t_lines.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        elements.append(Paragraph('Quotation Lines', styles['Heading2']))
        elements.append(t_lines)

        symbol = getattr(getattr(self, 'currency_id', False), 'symbol', '') or ''
        subtotal_str = f"{symbol} {subtotal_sum:,.2f}".strip()
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(f"<para align='right'><b>Subtotal</b>  {subtotal_str}</para>", styles['Normal']))

        if terms and terms.get('items'):
            elements.append(Spacer(1, 12))
            elements.append(Paragraph('Terms and Conditions', styles['Heading2']))
            data_tc = [[label, value] for label, value in terms['items']]
            t_tc = Table(data_tc, colWidths=[180, 360])
            t_tc.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            elements.append(t_tc)

        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"Regards,<br/>{self.env.user.name}", styles['Normal']))

        doc.build(elements, onFirstPage=_draw_header_footer, onLaterPages=_draw_header_footer)
        return buffer.getvalue()

    def _get_expected_arrival_from_quotation(self):
        """Return expected arrival from PO planning date."""
        return self.date_planned or False

    def _format_expected_arrival(self, value):
        """Return a YYYY-MM-DD string with +5h adjustment for datetimes, similar to client JS."""
        if not value:
            return ''
        try:
            # if it's a string already, try to parse, else return as-is
            if isinstance(value, str):
                try:
                    # attempt parse common formats
                    dt = datetime.fromisoformat(value)
                    value = dt
                except Exception:
                    return value
            if isinstance(value, datetime):
                adjusted = value + timedelta(hours=5)
                return adjusted.date().isoformat()
            if isinstance(value, date):
                return value.isoformat()
        except Exception:
            return str(value)
        return str(value)

    def _coerce_to_datetime(self, value):
        """Coerce a date/iso string into a datetime for writing into date_planned."""
        if not value:
            return False
        try:
            if isinstance(value, datetime):
                return value
            if isinstance(value, date):
                return datetime.combine(value, datetime.min.time())
            if isinstance(value, str):
                try:
                    return datetime.fromisoformat(value)
                except Exception:
                    return False
        except Exception:
            return False
        return False

    def _get_terms_section(self):
        """Return terms and conditions derived from purchase order fields."""
        items = []
        if self.payment_term_id:
            items.append(('Payment Terms', self.payment_term_id.display_name))
        if self.incoterm_id:
            items.append(('Delivery Terms', self.incoterm_id.display_name))
        if self.partner_ref:
            items.append(('Vendor Reference', self.partner_ref))
        return {'html': '', 'items': items}