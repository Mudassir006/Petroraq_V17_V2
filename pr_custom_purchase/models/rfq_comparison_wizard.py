from collections import defaultdict
from io import BytesIO
import base64

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

try:
    import xlsxwriter
except ImportError:  # pragma: no cover - handled at runtime if missing
    xlsxwriter = None


class RFQComparisonWizard(models.TransientModel):
    _name = "rfq.comparison.wizard"
    _description = "RFQ Comparison"

    custom_rfq_id = fields.Many2one("purchase.order", string="RFQ", readonly=True)
    requisition_id = fields.Many2one("purchase.requisition", string="Purchase Requisition", readonly=True)
    line_ids = fields.One2many("rfq.comparison.wizard.line", "wizard_id", string="Material Requirement")
    vendor_ids = fields.Many2many("res.partner", string="Suppliers", readonly=True)
    comparison_html = fields.Html(string="Comparison", compute="_compute_comparison_html", sanitize=False)

    @api.model
    def create_for_custom_rfq(self, rfq):
        requisition = rfq.requisition_id
        if not requisition:
            raise UserError(_("This RFQ is not linked to a purchase requisition."))
        return self.create_for_requisition(requisition, rfq)

    @api.model
    def create_for_requisition(self, requisition, source_rfq=False):
        wizard = self.create({
            "custom_rfq_id": source_rfq.id if source_rfq else False,
            "requisition_id": requisition.id,
        })
        wizard._build_comparison()
        return wizard

    def _get_candidate_rfqs(self):
        self.ensure_one()
        rfqs = self.env["purchase.order"].search([
            ("requisition_id", "=", self.requisition_id.id),
            ("partner_id", "!=", False),
            ("state", "in", ["sent", "pending"]),
        ])
        if not rfqs:
            raise UserError(_("No RFQs/quotations found for requisition %s.") % self.requisition_id.display_name)
        return rfqs

    def _build_comparison(self):
        self.ensure_one()
        rfqs = self._get_candidate_rfqs()

        lines_by_product = {}
        for req_line in self.requisition_id.line_ids:
            if not req_line.description:
                continue
            lines_by_product[req_line.description.id] = {
                "req_line": req_line,
                "offers": {},
            }

        if not lines_by_product:
            raise UserError(_("No material requirement lines found on this requisition."))

        for rfq in rfqs:
            for po_line in rfq.order_line:
                product = po_line.product_id
                if not product or product.id not in lines_by_product:
                    continue
                vendor_offers = lines_by_product[product.id]["offers"]
                existing_offer = vendor_offers.get(rfq.partner_id.id)
                total_amount = po_line.price_unit * po_line.product_qty
                offer_vals = {
                    "vendor_id": rfq.partner_id.id,
                    "rfq_id": rfq.id,
                    "unit_price": po_line.price_unit,
                    "quantity": po_line.product_qty,
                    "total_amount": total_amount,
                    "rfq_line_id": po_line.id,
                }
                if not existing_offer or po_line.price_unit < existing_offer["unit_price"]:
                    vendor_offers[rfq.partner_id.id] = offer_vals

        vendor_ids = set()
        line_commands = []
        seq = 1
        for product_id, data in lines_by_product.items():
            req_line = data["req_line"]
            offers = data["offers"]
            vendor_ids.update(offers.keys())

            selected_vendor_id = False
            positive_offers = [offer for offer in offers.values() if offer["unit_price"] > 0]
            if positive_offers:
                selected_vendor_id = min(positive_offers, key=lambda x: x["unit_price"])["vendor_id"]

            quote_commands = []
            for offer in offers.values():
                quote_commands.append((0, 0, {
                    "vendor_id": offer["vendor_id"],
                    "rfq_id": offer["rfq_id"],
                    "unit_price": offer["unit_price"],
                    "total_amount": offer["total_amount"],
                    "rfq_line_id": offer["rfq_line_id"],
                }))

            line_commands.append((0, 0, {
                "sequence": seq,
                "product_id": product_id,
                "description": req_line.description.display_name,
                "unit": req_line.unit,
                "quantity": req_line.quantity,
                "selected_vendor_id": selected_vendor_id,
                "quote_line_ids": quote_commands,
            }))
            seq += 1

        self.write({
            "line_ids": [(5, 0, 0)] + line_commands,
            "vendor_ids": [(6, 0, sorted(vendor_ids))],
        })

    @api.depends("line_ids", "line_ids.selected_vendor_id", "line_ids.quote_line_ids", "vendor_ids")
    def _compute_comparison_html(self):
        for wizard in self:
            vendors = wizard.vendor_ids
            header_top = "<tr><th rowspan='2'>Sr No</th><th colspan='4'>Material Requirement</th>"
            for vendor in vendors:
                header_top += "<th colspan='2'>%s</th>" % vendor.display_name
            header_top += "<th rowspan='2'>Supplier</th>"
            header_top += "</tr>"

            header_bottom = (
                "<tr>"
                "<th>Description</th><th>Unit</th><th>Qty</th><th>Selected RFQ</th>"
            )
            for _vendor in vendors:
                header_bottom += "<th>Cost Price</th><th>Total Amount</th>"
            header_bottom += "</tr>"

            body_rows = ""
            for line in wizard.line_ids.sorted(key=lambda l: (l.sequence, l.id)):
                body_rows += "<tr>"
                body_rows += "<td>%s</td><td>%s</td><td>%s</td><td>%s</td>" % (
                    line.sequence,
                    line.description or "",
                    line.unit or "",
                    line.quantity,
                )
                selected_offer = line.quote_line_ids.filtered(lambda q: q.vendor_id == line.selected_vendor_id)[:1]
                body_rows += "<td>%s</td>" % (selected_offer.rfq_id.name if selected_offer else "")

                quotes_by_vendor = {quote.vendor_id.id: quote for quote in line.quote_line_ids}
                for vendor in vendors:
                    quote = quotes_by_vendor.get(vendor.id)
                    if quote:
                        body_rows += "<td>%.2f</td><td>%.2f</td>" % (quote.unit_price, quote.total_amount)
                    else:
                        body_rows += "<td></td><td></td>"
                body_rows += "<td>%s</td>" % (line.selected_vendor_id.display_name or "")
                body_rows += "</tr>"

            wizard.comparison_html = (
                "<div class='o_rfq_compare_scroll'>"
                "<table class='table table-sm table-bordered o_rfq_compare_table'>"
                f"<thead>{header_top}{header_bottom}</thead><tbody>{body_rows}</tbody></table>"
                "</div>"
            )


    def action_create_selected_purchase_orders(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("No comparison lines available."))

        grouped_by_vendor = defaultdict(list)
        for line in self.line_ids:
            if not line.selected_vendor_id:
                continue
            offer = line.quote_line_ids.filtered(lambda q: q.vendor_id == line.selected_vendor_id)[:1]
            if not offer:
                continue
            grouped_by_vendor[line.selected_vendor_id].append((line, offer))

        if not grouped_by_vendor:
            raise UserError(_("Please select at least one supplier with available quotation lines."))

        existing_po = self.env["purchase.order"].sudo().search_count([
            ("requisition_id", "=", self.requisition_id.id),
            ("state", "in", ["pending", "purchase", "done"]),
        ])
        if existing_po:
            raise UserError(_("A Purchase Order already exists for requisition %s.") % self.requisition_id.name)

        purchase_orders = self.env["purchase.order"]
        for vendor, vendor_lines in grouped_by_vendor.items():
            source_rfq = next((offer.rfq_id for _line, offer in vendor_lines if offer.rfq_id), False)
            line_amounts = {}
            for line, offer in vendor_lines:
                if not line.cost_center_id:
                    continue
                line_amounts.setdefault(line.cost_center_id.id, 0.0)
                line_amounts[line.cost_center_id.id] += line.quantity * offer.unit_price

            if line_amounts:
                cost_centers = self.env["account.analytic.account"].sudo().browse(list(line_amounts.keys()))
                cc_map = {cc.id: cc for cc in cost_centers}
                for cc_id, amount in line_amounts.items():
                    cc = cc_map.get(cc_id)
                    if not cc:
                        raise ValidationError(_("Invalid cost center found in selected comparison lines."))
                    if cc.budget_left < amount:
                        raise ValidationError(
                            _("Insufficient budget for cost center %s. Remaining: %s, Required: %s")
                            % (cc.display_name, cc.budget_left, amount)
                        )

            po_vals = {
                "name": self.env["ir.sequence"].sudo().next_by_code("purchase.order") or "PO0001",
                "state": "pending",
                "partner_id": vendor.id,
                "origin": self.requisition_id.name,
                "requisition_id": self.requisition_id.id,
                "pr_name": self.requisition_id.name,
                "partner_ref": source_rfq.partner_ref if source_rfq else False,
                "date_planned": source_rfq.date_planned if source_rfq else fields.Datetime.now(),
                "payment_term_id": source_rfq.payment_term_id.id if source_rfq and source_rfq.payment_term_id else False,
                "incoterm_id": source_rfq.incoterm_id.id if source_rfq and source_rfq.incoterm_id else False,
                "notes": source_rfq.notes if source_rfq else False,
                "requested_by": self.requisition_id.requested_by,
                "department": self.requisition_id.department,
                "supervisor": self.requisition_id.supervisor,
                "supervisor_partner_id": self.requisition_id.supervisor_partner_id,
                "budget_type": self.requisition_id.budget_type,
                "budget_code": self.requisition_id.budget_details,
                "pe_approved": False,
                "pm_approved": False,
                "od_approved": False,
                "md_approved": False,
                "order_line": [
                    (0, 0, {
                        "product_id": line.product_id.id,
                        "name": line.description,
                        "product_qty": line.quantity,
                        "price_unit": offer.unit_price,
                        "date_planned": fields.Datetime.now(),
                        "product_uom": offer.rfq_line_id.product_uom.id if offer.rfq_line_id and offer.rfq_line_id.product_uom else False,
                        "analytic_distribution": {str(line.cost_center_id.id): 100.0} if line.cost_center_id else False,
                    })
                    for line, offer in vendor_lines
                ],
            }
            purchase_orders |= self.env["purchase.order"].sudo().create(po_vals)

        action = {
            "type": "ir.actions.act_window",
            "name": _("Created Purchase Orders"),
            "res_model": "purchase.order",
            "view_mode": "tree,form",
            "domain": [("id", "in", purchase_orders.ids)],
        }
        if len(purchase_orders) == 1:
            action.update({"view_mode": "form", "res_id": purchase_orders.id})
        return action

    def action_export_excel(self):
        self.ensure_one()
        if not xlsxwriter:
            raise UserError(_("xlsxwriter python library is required for Excel export."))

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        ws = workbook.add_worksheet("Comparison")

        title_fmt = workbook.add_format({"bold": True, "align": "center", "valign": "vcenter", "border": 1, "bg_color": "#D9EAD3"})
        header_fmt = workbook.add_format({"bold": True, "align": "center", "border": 1, "bg_color": "#E2F0D9"})
        cell_fmt = workbook.add_format({"border": 1})
        num_fmt = workbook.add_format({"border": 1, "num_format": "#,##0.00"})

        vendors = self.vendor_ids
        ws.merge_range(0, 0, 0, 4, "Material Requirement", title_fmt)
        col = 5
        for vendor in vendors:
            ws.merge_range(0, col, 0, col + 1, vendor.display_name, title_fmt)
            col += 2
        ws.write(0, col, "Supplier", title_fmt)

        headers = ["Sr No", "Description", "Unit", "Qty", "Selected RFQ"]
        for vendor in vendors:
            headers.extend(["Cost Price", "Total Amount"])
        headers.append("Supplier")

        for idx, header in enumerate(headers):
            ws.write(1, idx, header, header_fmt)
            ws.set_column(idx, idx, 18)

        row = 2
        for line in self.line_ids.sorted(key=lambda l: (l.sequence, l.id)):
            ws.write(row, 0, line.sequence, cell_fmt)
            ws.write(row, 1, line.description or "", cell_fmt)
            ws.write(row, 2, line.unit or "", cell_fmt)
            ws.write_number(row, 3, line.quantity or 0.0, num_fmt)
            selected_offer = line.quote_line_ids.filtered(lambda q: q.vendor_id == line.selected_vendor_id)[:1]
            ws.write(row, 4, selected_offer.rfq_id.name if selected_offer else "", cell_fmt)

            quotes_by_vendor = {quote.vendor_id.id: quote for quote in line.quote_line_ids}
            col = 5
            for vendor in vendors:
                quote = quotes_by_vendor.get(vendor.id)
                if quote:
                    ws.write_number(row, col, quote.unit_price, num_fmt)
                    ws.write_number(row, col + 1, quote.total_amount, num_fmt)
                else:
                    ws.write(row, col, "", cell_fmt)
                    ws.write(row, col + 1, "", cell_fmt)
                col += 2
            ws.write(row, col, line.selected_vendor_id.display_name or "", cell_fmt)
            row += 1

        workbook.close()
        output.seek(0)

        attachment = self.env["ir.attachment"].sudo().create({
            "name": f"RFQ Comparison - {self.requisition_id.name}.xlsx",
            "type": "binary",
            "datas": base64.b64encode(output.read()),
            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "res_model": self._name,
            "res_id": self.id,
        })

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }


class RFQComparisonWizardLine(models.TransientModel):
    _name = "rfq.comparison.wizard.line"
    _description = "RFQ Comparison Material Line"
    _order = "sequence asc, id asc"

    wizard_id = fields.Many2one("rfq.comparison.wizard", required=True, ondelete="cascade")
    sequence = fields.Integer(string="Sr No")
    product_id = fields.Many2one("product.product", string="Product", readonly=True)
    description = fields.Char(string="Description", readonly=True)
    unit = fields.Char(string="Unit", readonly=True)
    quantity = fields.Float(string="Qty", readonly=True)
    cost_center_id = fields.Many2one("account.analytic.account", string="Cost Center", compute="_compute_cost_center", store=False)
    selected_vendor_id = fields.Many2one("res.partner", string="Supplier")
    quote_line_ids = fields.One2many("rfq.comparison.wizard.quote", "wizard_line_id", string="Quotes", readonly=True)

    @api.depends("product_id", "wizard_id.requisition_id")
    def _compute_cost_center(self):
        for line in self:
            req_line = line.wizard_id.requisition_id.line_ids.filtered(lambda l: l.description == line.product_id)[:1]
            line.cost_center_id = req_line.cost_center_id


class RFQComparisonWizardQuote(models.TransientModel):
    _name = "rfq.comparison.wizard.quote"
    _description = "RFQ Comparison Vendor Quote"

    wizard_line_id = fields.Many2one("rfq.comparison.wizard.line", required=True, ondelete="cascade")
    vendor_id = fields.Many2one("res.partner", string="Supplier", readonly=True)
    rfq_id = fields.Many2one("purchase.order", string="RFQ", readonly=True)
    rfq_line_id = fields.Many2one("purchase.order.line", string="RFQ Line", readonly=True)
    unit_price = fields.Float(string="Cost Price", readonly=True)
    total_amount = fields.Float(string="Total Amount", readonly=True)