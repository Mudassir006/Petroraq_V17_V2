from odoo import models, fields, api, _
from odoo.exceptions import UserError


class GrnSes(models.Model):
    _name = "grn.ses"
    _description = "GRN / SES"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Reference", required=True)
    partner_id = fields.Many2one("res.partner", string="Vendor")
    purchase_order_id = fields.Many2one("purchase.order", string="Purchase Order", readonly=True)
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company, required=True, readonly=True)
    partner_ref = fields.Char(string="Vendor Reference")
    date_order = fields.Date(string="Order Date")
    date_planned = fields.Date(string="Planned Date")
    project = fields.Char(string="Project")
    requested_by = fields.Char(string="Requested By")
    department = fields.Char(string="Department")
    supervisor = fields.Char(string="Supervisor")
    origin = fields.Char(string="Source Document")
    date_request = fields.Date(string="Request Date")
    subtotal = fields.Float(string="Subtotal", compute="_compute_totals", store=True)
    tax_15 = fields.Float(string="VAT 15%", compute="_compute_totals", store=True)
    grand_total = fields.Float(string="Grand Total", compute="_compute_totals", store=True)
    is_reviewed = fields.Boolean("Reviewed", default=False)
    is_approved = fields.Boolean("Approved", default=False)
    line_ids = fields.One2many("grn.ses.line", "order_id", string="GRN/SES Lines")
    bill_ids = fields.One2many("account.move", "grn_ses_id", string="Vendor Bills")
    bill_count = fields.Integer(string="Bill Count", compute="_compute_bill_count")
    stage = fields.Selection(
        [
            ("pending", "Pending"),
            ("reviewed", "Reviewed"),
            ("approved", "Approved"),
        ],
        string="Stage",
        default="pending",
        tracking=True,
    )

    @api.depends("line_ids.subtotal")
    def _compute_totals(self):
        for rec in self:
            rec.subtotal = sum(line.subtotal for line in rec.line_ids)
            rec.tax_15 = rec.subtotal * 0.15 if rec.subtotal else 0.0
            rec.grand_total = rec.subtotal + rec.tax_15

    @api.depends("bill_ids")
    def _compute_bill_count(self):
        for rec in self:
            rec.bill_count = len(rec.bill_ids)

    def action_review(self):
        """Mark record as reviewed"""
        for rec in self:
            rec.is_reviewed = True
            rec.stage = "reviewed"
            group = self.env.ref("pr_custom_purchase.inventory_admin", raise_if_not_found=False)
            if group and group.users:
                for user in group.users:
                    rec.activity_schedule(
                        'mail.mail_activity_data_todo',
                        user_id=user.id,
                        summary="Record Reviewed",
                        note=f"Record {rec.display_name} has been reviewed and awaits approval."
                    )
        return True

    def action_approve(self):
        """Mark record as approved"""
        for rec in self:
            rec.is_approved = True
            rec.stage = "approved"
            group = self.env.ref("pr_custom_purchase.inventory_admin", raise_if_not_found=False)
            if group and group.users:
                for user in group.users:
                    rec.activity_schedule(
                        'mail.mail_activity_data_todo',
                        user_id=user.id,
                        summary="Record Approved",
                        note=f"Record {rec.display_name} has been approved."
                    )

    def _get_expense_account(self, product=False):
        self.ensure_one()
        account = False
        if product:
            account = product.property_account_expense_id or product.categ_id.property_account_expense_categ_id
        company = self.company_id or self.env.company
        if not account:
            account = self.env["account.account"].sudo().search([
                ("company_id", "=", company.id),
                ("account_type", "=", "expense"),
                ("deprecated", "=", False),
            ], limit=1)
        if not account:
            raise UserError(_("No expense account found to create vendor bill lines."))
        return account

    def action_create_vendor_bill(self):
        self.ensure_one()
        if not self.is_approved:
            raise UserError(_("Please approve the GRN/SES before creating a vendor bill."))
        if not self.partner_id:
            raise UserError(_("Vendor is required on GRN/SES to create a bill."))
        if not self.line_ids:
            raise UserError(_("Cannot create vendor bill without GRN/SES lines."))

        existing_draft = self.bill_ids.filtered(lambda b: b.state == "draft")[:1]
        if existing_draft:
            return {
                "type": "ir.actions.act_window",
                "name": _("Vendor Bill"),
                "res_model": "account.move",
                "res_id": existing_draft.id,
                "view_mode": "form",
                "target": "current",
            }

        invoice_lines = []
        for line in self.line_ids:
            product = self.env["product.product"].sudo().search([("name", "=", line.name)], limit=1)
            vals = {
                "name": line.name or _("GRN/SES Item"),
                "quantity": line.quantity or 1.0,
                "price_unit": line.price_unit or 0.0,
            }
            if product:
                vals["product_id"] = product.id
            else:
                vals["account_id"] = self._get_expense_account(product=product).id
            invoice_lines.append((0, 0, vals))

        company = self.company_id or self.env.company
        purchase_journal = self.env["account.journal"].sudo().search([
            ("type", "=", "purchase"),
            ("company_id", "=", company.id),
        ], limit=1)
        if not purchase_journal:
            raise UserError(_("Please configure a purchase journal to create vendor bills."))

        bill = self.env["account.move"].sudo().create({
            "move_type": "in_invoice",
            "partner_id": self.partner_id.id,
            "invoice_date": fields.Date.context_today(self),
            "invoice_origin": self.purchase_order_id.name if self.purchase_order_id else self.name,
            "ref": self.partner_ref or self.name,
            "invoice_line_ids": invoice_lines,
            "grn_ses_id": self.id,
            "journal_id": purchase_journal.id,
            "company_id": company.id,
        })

        self.message_post(body=_("Vendor Bill %s created from %s.") % (bill.name or bill.id, self.name))

        return {
            "type": "ir.actions.act_window",
            "name": _("Vendor Bill"),
            "res_model": "account.move",
            "res_id": bill.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_vendor_bills(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Vendor Bills"),
            "res_model": "account.move",
            "view_mode": "tree,form",
            "domain": [("id", "in", self.bill_ids.ids)],
            "context": {"default_move_type": "in_invoice", "create": False},
        }

    def _get_report_base_filename(self):
        """Hide GRN/SES report until approved"""
        self.ensure_one()
        if not self.is_approved:
            return False
        return f"{self.name}_Report"

    def print_grn_ses_report(self):
        for rec in self:
            if rec.stage != "approved":
                raise UserError(_("Reports cannot be downloaded until GRN/SES is approved"))
        return self.env.ref("pr_custom_purchase.action_report_grn_ses").report_action(self)


class GrnSesLine(models.Model):
    _name = "grn.ses.line"
    _description = "GRN/SES Line"

    order_id = fields.Many2one("grn.ses", string="GRN/SES", ondelete="cascade", required=True)
    name = fields.Char(string="Description")
    quantity = fields.Float(string="Quantity")
    unit = fields.Char(string="Unit")
    type = fields.Selection(
        [("material", "Material"), ("service", "Service")],
        string="Type",
        default="material",
        required=True,
    )
    price_unit = fields.Float(string="Unit Price")
    remarks = fields.Char(string="Remarks")
    subtotal = fields.Float(string="Subtotal", compute="_compute_subtotal", store=True)

    @api.depends("quantity", "price_unit")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price_unit


class GrnSesWizard(models.TransientModel):
    _name = "grn.ses.wizard"
    _description = "Wizard for GRN/SES Creation"

    remarks = fields.Text(string="Remarks")

    def action_create_grn_ses(self):
        active_id = self.env.context.get("active_id")
        order = self.env["purchase.order"].browse(active_id)

        created_records = []

        material_lines = order.custom_line_ids.filtered(lambda l: l.type == "material")
        service_lines = order.custom_line_ids.filtered(lambda l: l.type == "service")

        common_vals = {
            "partner_id": order.partner_id.id,
            "purchase_order_id": order.id,
            "partner_ref": order.partner_ref,
            "date_order": order.date_order,
            "date_planned": order.date_planned,
            "project": order.project_id.name if getattr(order, "project_id", False) else False,
            "requested_by": order.requested_by,
            "department": order.department,
            "supervisor": order.supervisor,
            "origin": order.origin,
            "date_request": order.date_request,
            "company_id": order.company_id.id,
        }

        if material_lines:
            grn = self.env["grn.ses"].create({
                **common_vals,
                "name": f"GRN for {order.name}",
            })
            grn.write({
                "line_ids": [
                    (0, 0, {
                        "name": line.name,
                        "quantity": line.quantity,
                        "unit": line.unit,
                        "type": line.type,
                        "price_unit": line.price_unit,
                        "subtotal": line.subtotal,
                        "remarks": self.remarks,
                    })
                    for line in material_lines
                ]
            })
            created_records.append(grn)

        if service_lines:
            ses = self.env["grn.ses"].create({
                **common_vals,
                "name": f"SES for {order.name}",
            })
            ses.write({
                "line_ids": [
                    (0, 0, {
                        "name": line.name,
                        "quantity": line.quantity,
                        "unit": line.unit,
                        "type": line.type,
                        "price_unit": line.price_unit,
                        "subtotal": line.subtotal,
                        "remarks": self.remarks,
                    })
                    for line in service_lines
                ]
            })
            created_records.append(ses)

        group = self.env.ref("pr_custom_purchase.inventory_qc", raise_if_not_found=False)
        if group and group.users:
            for rec in created_records:
                for user in group.users:
                    rec.activity_schedule(
                        'mail.mail_activity_data_todo',
                        user_id=user.id,
                        summary="GRN/SES Created",
                        note=f"A {rec.name} has been created from Purchase Order {order.name} and requires your QC review."
                    )

        return {"type": "ir.actions.act_window_close"}


class AccountMove(models.Model):
    _inherit = "account.move"

    grn_ses_id = fields.Many2one("grn.ses", string="GRN/SES", readonly=True, copy=False)


class GrnSesReport(models.AbstractModel):
    _name = 'report.pr_custom_purchase.report_petroraq_grn_ses'
    _description = 'GRN/SES QWeb Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['grn.ses'].browse(docids)
        for rec in docs:
            if not rec.is_approved:
                raise UserError("You can only print the GRN/SES Report after it is approved.")
        return {
            'doc_ids': docids,
            'doc_model': 'grn.ses',
            'docs': docs,
        }