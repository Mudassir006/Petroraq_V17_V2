from markupsafe import escape

from odoo import _, fields, models


class CrossoveredBudget(models.Model):
    _inherit = "crossovered.budget"

    sale_order_id = fields.Many2one("sale.order", string="Sale Order")
    work_order_id = fields.Many2one("pr.work.order", string="Work Order")
    source_products_html = fields.Html(
        string="Source Products",
        compute="_compute_source_products_data",
        sanitize=False,
        readonly=True,
    )
    source_products_total = fields.Monetary(
        string="Source Products Total",
        compute="_compute_source_products_data",
        currency_field="company_currency_id",
        readonly=True,
    )
    company_currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        readonly=True,
    )

    def _compute_source_products_data(self):
        for rec in self:
            rows = []
            total = 0.0
            current_section = False

            if rec.work_order_id:
                for line in rec.work_order_id.boq_line_ids.sorted(key=lambda l: (l.sequence, l.id)):
                    if line.display_type == "line_section":
                        current_section = line.name or line.section_name
                        continue
                    if line.display_type == "line_note":
                        continue
                    section_name = line.section_name or current_section or _("General")
                    line_total = line.total or ((line.qty or 0.0) * (line.unit_cost or 0.0))
                    rows.append({
                        "section": section_name,
                        "product": line.product_id.display_name or line.name or "",
                        "qty": line.qty or 0.0,
                        "unit_price": line.unit_cost or 0.0,
                        "line_total": line_total,
                    })
                    total += line_total
            elif rec.sale_order_id:
                for line in rec.sale_order_id.order_line.sorted(key=lambda l: (l.sequence, l.id)):
                    if line.display_type == "line_section":
                        current_section = line.name
                        continue
                    if line.display_type == "line_note":
                        continue
                    section_name = current_section or _("General")
                    line_total = line.price_subtotal or ((line.product_uom_qty or 0.0) * (line.price_unit or 0.0))
                    rows.append({
                        "section": section_name,
                        "product": line.product_id.display_name or line.name or "",
                        "qty": line.product_uom_qty or 0.0,
                        "unit_price": line.price_unit or 0.0,
                        "line_total": line_total,
                    })
                    total += line_total

            if not rows:
                rec.source_products_html = "<p>%s</p>" % escape(_("No source products found from Sale Order / Work Order."))
                rec.source_products_total = 0.0
                continue

            html_rows = []
            current = None
            section_total = 0.0
            for row in rows:
                if current != row["section"]:
                    if current is not None:
                        html_rows.append(
                            f"<tr class='o_subtotal'><td colspan='4'><b>{escape(_('Section Total'))}</b></td>"
                            f"<td class='text-end'><b>{section_total:,.2f}</b></td></tr>"
                        )
                    current = row["section"]
                    section_total = 0.0
                    html_rows.append(
                        f"<tr class='table-secondary'><td colspan='5'><b>{escape(current)}</b></td></tr>"
                    )
                section_total += row["line_total"]
                html_rows.append(
                    "<tr>"
                    f"<td></td><td>{escape(row['product'])}</td>"
                    f"<td class='text-end'>{row['qty']:,.2f}</td>"
                    f"<td class='text-end'>{row['unit_price']:,.2f}</td>"
                    f"<td class='text-end'>{row['line_total']:,.2f}</td>"
                    "</tr>"
                )
            html_rows.append(
                f"<tr class='o_subtotal'><td colspan='4'><b>{escape(_('Section Total'))}</b></td>"
                f"<td class='text-end'><b>{section_total:,.2f}</b></td></tr>"
            )
            html_rows.append(
                f"<tr class='table-primary'><td colspan='4'><b>{escape(_('Grand Total'))}</b></td>"
                f"<td class='text-end'><b>{total:,.2f}</b></td></tr>"
            )

            rec.source_products_html = (
                "<table class='table table-sm table-hover o_list_table'>"
                "<thead><tr>"
                f"<th>{escape(_('Section'))}</th>"
                f"<th>{escape(_('Product'))}</th>"
                f"<th class='text-end'>{escape(_('Qty'))}</th>"
                f"<th class='text-end'>{escape(_('Unit Price'))}</th>"
                f"<th class='text-end'>{escape(_('Total'))}</th>"
                "</tr></thead>"
                f"<tbody>{''.join(html_rows)}</tbody></table>"
            )
            rec.source_products_total = total
