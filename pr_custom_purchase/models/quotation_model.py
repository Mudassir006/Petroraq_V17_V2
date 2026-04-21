from odoo import models, fields, api, _
from odoo.exceptions import AccessError
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression

import logging

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    requisition_id = fields.Many2one("purchase.requisition", string="Source PR", readonly=True, ondelete="set null")
    linked_pr_state = fields.Selection([
        ("missing", "Not Created"),
        ("draft", "Draft"),
        ("rfq_sent", "RFQ Sent"),
        ("pending", "Pending"),
        ("purchase", "Purchase Order"),
        ("cancel", "Cancelled"),
    ], string="PR Status", compute="_compute_linked_statuses")
    linked_po_state = fields.Selection([
        ("missing", "Not Created"),
        ("draft", "RFQ"),
        ("sent", "RFQ Sent"),
        ("pending", "Pending"),
        ("purchase", "Purchase Order"),
        ("done", "Locked"),
        ("cancel", "Cancelled"),
    ], string="PO Status", compute="_compute_linked_statuses")
    current_user_has_acted = fields.Boolean("Current User Has Acted", )
    linked_quotation_status = fields.Selection([
        ("missing", "Not Submitted"),
        ("quote", "RFQ"),
        ("po", "Purchase Order"),
    ], string="RFQ / PO Status", compute="_compute_linked_statuses")

    is_rfq_record = fields.Boolean(
        string="Is RFQ",
        compute="_compute_is_rfq_record",
        store=False,
    )

    quotation_count = fields.Integer(
        string="Related RFQs",
        compute="_compute_quotation_count",
        store=False,
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("sent", "RFQ Sent"),
            ("pending", "Pending Approval"),
            ("purchase", "Purchase Order"),
            ("done", "Locked"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        tracking=True,
    )
    project_id = fields.Many2one("project.project", string="Project")
    pe_approved = fields.Boolean(string="Approved", default=False)
    pm_approved = fields.Boolean(string="Approved", default=False)
    od_approved = fields.Boolean(string="Approved", default=False)
    md_approved = fields.Boolean(string="Approved", default=False)
    can_confirm_order = fields.Boolean(
        compute="_compute_can_confirm_order", store=False
    )
    # Computed fields for view visibility
    show_pe_approved = fields.Boolean(compute="_compute_show_approvals", store=False)
    show_pm_approved = fields.Boolean(compute="_compute_show_approvals", store=False)
    show_od_approved = fields.Boolean(compute="_compute_show_approvals", store=False)
    show_md_approved = fields.Boolean(compute="_compute_show_approvals", store=False)
    is_current_user_approver = fields.Boolean(
        string="Is Current User Approver",
        compute="_compute_is_current_user_approver",
        search="_search_is_current_user_approver",
        store=False,
    )
    subtotal = fields.Float(
        string="Subtotal", compute="_compute_amount_untaxed_custom", store=True
    )
    tax_15 = fields.Float(
        string="15% Tax", compute="_compute_amount_untaxed_custom", store=True
    )
    grand_total = fields.Float(
        string="Grand Total", compute="_compute_amount_untaxed_custom", store=True
    )
    display_total = fields.Monetary(
        string="Total",
        currency_field="currency_id",
        compute="_compute_display_total",
        store=False,
    )
    vendor_ids = fields.Many2many("res.partner", string="All Vendors")
    custom_line_ids = fields.One2many("purchase.order.custom.line", "order_id", string="Custom Lines")
    date_request = fields.Date(
        string="Date of Request", default=fields.Date.context_today
    )
    requested_by = fields.Char(string="Requested By")
    department = fields.Char(string="Department")
    supervisor = fields.Char(string="Supervisor")
    supervisor_partner_id = fields.Char(string="supervisor_partner_id")
    grn_ses_button_type = fields.Selection([("grn", "GRN"), ("ses", "SES"), ("both", "GRN/SES")],
                                           string="GRN/SES Button Type", compute="_compute_grn_ses_button_type",
                                           store=False)
    # Reason tab field (editable by specific groups via view)
    rejection_reason = fields.Text(string="Reason for Rejection")

    @api.depends("name")
    def _compute_is_rfq_record(self):
        for order in self:
            order_name = (order.name or "").upper()
            order.is_rfq_record = order_name.startswith("RFQ")

    def _compute_quotation_count(self):
        for order in self:
            if not order.requisition_id:
                order.quotation_count = 0
                continue
            domain = [("requisition_id", "=", order.requisition_id.id), ("id", "!=", order.id)]
            order.quotation_count = self.env["purchase.order"].search_count(domain)

    def _compute_linked_statuses(self):
        po_priority = {"draft": 1, "sent": 2, "pending": 3, "purchase": 4, "done": 5, "cancel": 6}
        for rec in self:
            pr = self.env["custom.pr"].sudo().search([("name", "=", rec.pr_name)], limit=1) if rec.pr_name else False
            rec.linked_pr_state = pr.state if pr else "missing"
            linked_pos = self.env["purchase.order"].sudo().search([("origin", "=", rec.name)]) if rec.name else \
                self.env["purchase.order"]
            rec.linked_po_state = max(linked_pos,
                                      key=lambda po: po_priority.get(po.state, 0)).state if linked_pos else "missing"
            related_rfqs = self.env["purchase.order"].sudo().search([
                ("requisition_id", "=", rec.requisition_id.id),
                ("id", "!=", rec.id),
            ]) if rec.requisition_id else self.env["purchase.order"]
            if related_rfqs:
                top_state = max(related_rfqs, key=lambda r: po_priority.get(r.state, 0)).state
                rec.linked_quotation_status = "po" if top_state in ("pending", "purchase", "done") else "quote"
            else:
                rec.linked_quotation_status = "missing"

    def action_view_quotations(self):
        return self.action_view_rfq_quotations()

    def action_view_rfq_quotations(self):
        self.ensure_one()
        domain = [("requisition_id", "=", self.requisition_id.id), ("id", "!=", self.id)] if self.requisition_id else [
            ("id", "=", 0)]
        action = self.env.ref("purchase.purchase_rfq").read()[0]
        action.update({
            "name": _("Related RFQs"),
            "domain": domain,
            "context": {"group_by": "requisition_id"},
        })
        return action

    def action_create_po_from_rfq(self):
        """Create a new PO draft/pending record from the selected RFQ."""
        self.ensure_one()

        if self.state not in ("draft", "sent", "pending"):
            raise UserError(_("Only RFQs in Draft/Sent/Pending can be selected for Purchase Order."))

        if not self.order_line:
            raise UserError(_("This RFQ has no order lines."))

        existing_po = self.env["purchase.order"].sudo().search_count([
            ("requisition_id", "=", self.requisition_id.id),
            ("state", "in", ["pending", "purchase", "done"]),
        ]) if self.requisition_id else self.env["purchase.order"].sudo().search_count([
            ("origin", "=", self.name),
            ("state", "in", ["pending", "purchase", "done"]),
        ])
        if existing_po:
            raise UserError(_("A Purchase Order already exists for RFQ %s.") % self.name)

        sibling_rfqs = self.env["purchase.order"].sudo().search([
            ("requisition_id", "=", self.requisition_id.id),
            ("id", "!=", self.id),
            ("state", "in", ["draft", "sent"]),
        ]) if self.requisition_id else self.env["purchase.order"]

        line_amounts = {}
        for line in self.order_line:
            distribution = line.analytic_distribution or {}
            for cc_id, percentage in distribution.items():
                try:
                    share = (line.price_subtotal or 0.0) * (float(percentage) / 100.0)
                except (TypeError, ValueError):
                    share = 0.0
                if share <= 0.0:
                    continue
                line_amounts.setdefault(int(cc_id), 0.0)
                line_amounts[int(cc_id)] += share

        if line_amounts:
            cost_centers = self.env["account.analytic.account"].sudo().browse(list(line_amounts.keys()))
            cc_map = {cc.id: cc for cc in cost_centers}
            for cc_id, amount in line_amounts.items():
                cc = cc_map.get(cc_id)
                if not cc:
                    raise ValidationError(_("Invalid cost center found in RFQ analytic distribution."))
                if cc.budget_left < amount:
                    raise ValidationError(
                        _("Insufficient budget for cost center %s. Remaining: %s, Required: %s")
                        % (cc.display_name, cc.budget_left, amount)
                    )

        po_name = self.env["ir.sequence"].sudo().next_by_code("purchase.order") or "PO0001"
        po_vals = {
            "name": po_name,
            "state": "pending",
            "origin": self.name,
            "partner_id": self.partner_id.id,
            "partner_ref": self.partner_ref,
            "date_planned": self.date_planned or fields.Datetime.now(),
            "currency_id": self.currency_id.id,
            "company_id": self.company_id.id,
            "pr_name": self.pr_name,
            "requisition_id": self.requisition_id.id,
            "requested_by": self.requested_by,
            "department": self.department,
            "supervisor": self.supervisor,
            "supervisor_partner_id": self.supervisor_partner_id,
            "project_id": self.project_id.id if self.project_id else False,
            "budget_type": self.requisition_id.budget_type if self.requisition_id else False,
            "budget_code": self.requisition_id.budget_details if self.requisition_id else False,
            "pe_approved": False,
            "pm_approved": False,
            "od_approved": False,
            "md_approved": False,
            "order_line": [
                (0, 0, {
                    "product_id": line.product_id.id,
                    "name": line.name,
                    "product_qty": line.product_qty,
                    "product_uom": line.product_uom.id,
                    "price_unit": line.price_unit,
                    "date_planned": line.date_planned or fields.Datetime.now(),
                    "taxes_id": [(6, 0, line.taxes_id.ids)],
                    "analytic_distribution": line.analytic_distribution,
                })
                for line in self.order_line if line.product_id
            ],
        }
        new_po = self.env["purchase.order"].sudo().create(po_vals)

        amount = new_po.subtotal
        if amount <= 10000:
            new_po._schedule_activity_for_group(
                "pr_custom_purchase.project_engineer",
                "Review Purchase Order",
                f"PO {new_po.name} selected from RFQ {self.name}. Please review.",
            )
        elif amount <= 100000:
            for group_xml_id in ["pr_custom_purchase.project_engineer", "pr_custom_purchase.project_manager"]:
                new_po._schedule_activity_for_group(
                    group_xml_id,
                    "Review Purchase Order",
                    f"PO {new_po.name} selected from RFQ {self.name}. Please review.",
                )
        elif amount <= 500000:
            for group_xml_id in [
                "pr_custom_purchase.project_engineer",
                "pr_custom_purchase.project_manager",
                "pr_custom_purchase.operations_director",
            ]:
                new_po._schedule_activity_for_group(
                    group_xml_id,
                    "Review Purchase Order",
                    f"PO {new_po.name} selected from RFQ {self.name}. Please review.",
                )
        else:
            for group_xml_id in [
                "pr_custom_purchase.project_engineer",
                "pr_custom_purchase.project_manager",
                "pr_custom_purchase.operations_director",
                "pr_custom_purchase.managing_director",
            ]:
                new_po._schedule_activity_for_group(
                    group_xml_id,
                    "Review Purchase Order",
                    f"PO {new_po.name} selected from RFQ {self.name}. Please review.",
                )

        if self.state == "draft":
            self.write({"state": "sent"})
        self.message_post(body=_("Purchase Order %s created from this RFQ.") % new_po.name)

        if sibling_rfqs:
            sibling_rfqs.write({"state": "cancel"})
            for sibling_rfq in sibling_rfqs:
                sibling_rfq.message_post(body=_("Cancelled because another RFQ was selected as Purchase Order."))

        return {
            "type": "ir.actions.act_window",
            "name": _("Purchase Order"),
            "res_model": "purchase.order",
            "view_mode": "form",
            "res_id": new_po.id,
            "target": "current",
        }

    def action_open_rfq_comparison(self):
        self.ensure_one()
        if self.quotation_count == 0:
            raise UserError(_("No comparable RFQs are available for this requisition yet."))
        wizard = self.env['rfq.comparison.wizard'].create_for_custom_rfq(self)
        return {
            "type": "ir.actions.act_window",
            "name": _("RFQ Comparison"),
            "res_model": "rfq.comparison.wizard",
            "view_mode": "form",
            "target": "current",
            "res_id": wizard.id,
            "context": {"form_view_initial_mode": "edit"},
        }

    def _reload_action(self):
        """Return an action that reloads the current form to refresh button visibility."""
        return {
            "type": "ir.actions.act_window",
            "res_model": "purchase.order",
            "view_mode": "form",
            "res_id": self.id,
            "target": "current",
        }

    @api.depends("order_line.price_subtotal")
    def _compute_amount_untaxed_custom(self):
        for order in self:
            order.subtotal = sum(order.order_line.mapped("price_subtotal"))
            order.tax_15 = order.subtotal * 0.15
            order.grand_total = order.subtotal + order.tax_15

    # def button_confirm(self):
    #     for order in self:
    #         if order.state == "pending":
    #             order.write({"state": "purchase"})
    #         else:
    #             super(PurchaseOrder, order).button_confirm()

    def button_confirm(self):
        for order in self:
            if order.state == "pending":
                if not order.can_confirm_order:
                    raise UserError(
                        _("All required approvals must be completed before confirming this Purchase Order."))
                    # Re-enter the native purchase confirmation flow so stock pickings/
                    # receipts are generated by standard Odoo logic.
                order.write({"state": "draft"})
                super(PurchaseOrder, order).button_confirm()
            else:
                super(PurchaseOrder, order).button_confirm()

    def _schedule_activity_for_group(self, group_xml_id, summary, note):
        group = self.env.ref(group_xml_id, raise_if_not_found=False)
        if not group:
            return
        for user in group.users.filtered(lambda u: u.active):
            self.activity_schedule(
                "mail.mail_activity_data_todo",
                summary=summary,
                note=note,
                user_id=user.id,
            )
            if user.email:
                self.env["mail.mail"].sudo().create({
                    "email_from": "hr@petroraq.com",
                    "email_to": user.email,
                    "subject": summary,
                    "body_html": f"<p>{note}</p>",
                }).send()

    # main approval logic
    def action_approve(self):
        self.ensure_one()
        amount = self.subtotal

        if amount <= 10000:
            if not self.pe_approved:
                self.write({"pe_approved": True})
                self.message_post(body="Approved by Procurement Manager.")

        elif amount <= 100000:
            if not self.pe_approved:
                self.write({"pe_approved": True})
                self.message_post(body="Approved by Procurement Manager.")
                self._schedule_activity_for_group(
                    "pr_custom_purchase.project_manager",
                    "Review Purchase Order",
                    f"PO {self.name} approved by PE. Please review.",
                )
            elif not self.pm_approved:
                self.write({"pm_approved": True})
                self.message_post(body="Approved by Project Manager.")

        elif amount <= 500000:
            if not self.pe_approved:
                self.write({"pe_approved": True})
                self.message_post(body="Approved by Procurement Manager.")
                self._schedule_activity_for_group(
                    "pr_custom_purchase.project_manager",
                    "Review Purchase Order",
                    f"PO {self.name} approved by PE. Please review.",
                )
            elif not self.pm_approved:
                self.write({"pm_approved": True})
                self.message_post(body="Approved by Project Manager.")
                self._schedule_activity_for_group(
                    "pr_custom_purchase.operations_director",
                    "Review Purchase Order",
                    f"PO {self.name} approved by PM. Please review.",
                )
            elif not self.od_approved:
                self.write({"od_approved": True})
                self.message_post(body="Approved by Operations Director.")

        else:  # Above 500k
            if not self.pe_approved:
                self.write({"pe_approved": True})
                self.message_post(body="Approved by Procurement Manager.")
                self._schedule_activity_for_group(
                    "pr_custom_purchase.project_manager",
                    "Review Purchase Order",
                    f"PO {self.name} approved by PE. Please review.",
                )
            elif not self.pm_approved:
                self.write({"pm_approved": True})
                self.message_post(body="Approved by Project Manager.")
                self._schedule_activity_for_group(
                    "pr_custom_purchase.operations_director",
                    "Review Purchase Order",
                    f"PO {self.name} approved by PM. Please review.",
                )
            elif not self.od_approved:
                self.write({"od_approved": True})
                self.message_post(body="Approved by Operations Director.")
                self._schedule_activity_for_group(
                    "pr_custom_purchase.managing_director",
                    "Review Purchase Order",
                    f"PO {self.name} approved by OD. Please review.",
                )
            elif not self.md_approved:
                self.write({"md_approved": True})
                self.message_post(body="Approved by Managing Director.")

        return self._reload_action()

    # confirm order button visibility
    @api.depends(
        "state",
        "pe_approved",
        "pm_approved",
        "od_approved",
        "md_approved",
        "subtotal",
    )
    def _compute_can_confirm_order(self):
        for order in self:
            if order.state != "pending":
                order.can_confirm_order = False
                continue

            amt = order.subtotal
            if amt <= 10000:
                order.can_confirm_order = order.pe_approved
            elif amt <= 100000:
                order.can_confirm_order = order.pe_approved and order.pm_approved
            elif amt <= 500000:
                order.can_confirm_order = (
                        order.pe_approved and order.pm_approved and order.od_approved
                )
            else:
                order.can_confirm_order = (
                        order.pe_approved
                        and order.pm_approved
                        and order.od_approved
                        and order.md_approved
                )

    @api.depends("state", "subtotal", "pe_approved", "pm_approved", "od_approved", "md_approved")
    def _compute_show_approvals(self):
        """Show only one approval button for the next required stage."""
        user = self.env.user
        for order in self:
            order.show_pe_approved = False
            order.show_pm_approved = False
            order.show_od_approved = False
            order.show_md_approved = False

            if order.state != "pending":
                continue

            amount = order.subtotal
            if amount <= 10000:
                required_stage = "pe"
            elif amount <= 100000:
                required_stage = "pm" if order.pe_approved else "pe"
            elif amount <= 500000:
                if not order.pe_approved:
                    required_stage = "pe"
                elif not order.pm_approved:
                    required_stage = "pm"
                else:
                    required_stage = "od"
            else:
                if not order.pe_approved:
                    required_stage = "pe"
                elif not order.pm_approved:
                    required_stage = "pm"
                elif not order.od_approved:
                    required_stage = "od"
                else:
                    required_stage = "md"

            if required_stage == "pe" and user.has_group("pr_custom_purchase.project_engineer"):
                order.show_pe_approved = True
            elif required_stage == "pm" and user.has_group("pr_custom_purchase.project_manager"):
                order.show_pm_approved = True
            elif required_stage == "od" and user.has_group("pr_custom_purchase.operations_director"):
                order.show_od_approved = True
            elif required_stage == "md" and user.has_group("pr_custom_purchase.managing_director"):
                order.show_md_approved = True

    def _compute_is_current_user_approver(self):
        for order in self:
            order.is_current_user_approver = any([
                order.show_pe_approved,
                order.show_pm_approved,
                order.show_od_approved,
                order.show_md_approved,
            ])

    def _search_is_current_user_approver(self, operator, value):
        if operator not in ("=", "!=") or not isinstance(value, bool):
            raise ValidationError(_("Unsupported search operation for current approver filter."))

        user = self.env.user
        stage_domains = []

        if user.has_group("pr_custom_purchase.project_engineer"):
            stage_domains.append([("pe_approved", "=", False)])
        if user.has_group("pr_custom_purchase.project_manager"):
            stage_domains.append([
                ("subtotal", ">", 10000),
                ("pe_approved", "=", True),
                ("pm_approved", "=", False),
            ])
        if user.has_group("pr_custom_purchase.operations_director"):
            stage_domains.append([
                ("subtotal", ">", 100000),
                ("pe_approved", "=", True),
                ("pm_approved", "=", True),
                ("od_approved", "=", False),
            ])
        if user.has_group("pr_custom_purchase.managing_director"):
            stage_domains.append([
                ("subtotal", ">", 500000),
                ("pe_approved", "=", True),
                ("pm_approved", "=", True),
                ("od_approved", "=", True),
                ("md_approved", "=", False),
            ])

        if stage_domains:
            approval_domain = expression.OR(stage_domains)
            matching_domain = expression.AND([[("state", "=", "pending")], approval_domain])
        else:
            matching_domain = [("id", "=", 0)]

        if (operator == "=" and value) or (operator == "!=" and not value):
            return matching_domain
        return expression.NOT(matching_domain)

    def action_reset_to_draft(self):
        for order in self:
            if order.state == "done":
                raise UserError(_("Locked orders cannot be reset to draft."))

            order.sudo().write({
                "state": "draft",
                "pe_approved": False,
                "pm_approved": False,
                "od_approved": False,
                "md_approved": False,
            })

            if order.pr_name:
                custom_pr = self.env["custom.pr"].sudo().search([("name", "=", order.pr_name)], limit=1)
                if custom_pr:
                    custom_pr.write({"state": "draft", "approval": "pending", "pr_created": False})

            if order.origin:
                rfqs = self.env["purchase.order"].sudo().search([("name", "=", order.origin)])
                rfqs.write({"state": "draft"})

            order.message_post(body=_("Purchase Order reset to draft and approvals cleared."))
        return True

    def action_open_reject_wizard(self):
        self.ensure_one()
        if self.state != "pending":
            raise UserError(_("Only pending Purchase Orders can be rejected."))
        self._compute_show_approvals()
        if not (self.show_pe_approved or self.show_pm_approved or self.show_od_approved or self.show_md_approved):
            raise UserError(_("You can reject only when it is your current approval stage."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Reject Purchase Order"),
            "res_model": "purchase.order.reject.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_purchase_order_id": self.id,
            },
        }

    def action_reject(self, reason=False):
        reason = reason or self.env.context.get("reject_reason")
        if not reason:
            raise UserError(_("Please provide reason for rejection."))

        for order in self:
            if not order.origin:
                raise UserError(_("This Purchase Order has no origin."))

            rejecting_user = self.env.user
            order.rejection_reason = reason
            _logger.info(
                "Rejecting PO %s with origin: %s by %s",
                order.name,
                order.origin,
                rejecting_user.name,
            )

            parent_po = self.env["purchase.order"].search(
                [("name", "=", order.origin)], limit=1
            )
            if not parent_po:
                _logger.warning("No parent PO found for origin: %s", order.origin)
                order.state = "cancel"
                continue

            if not parent_po.origin:
                _logger.warning("Parent PO %s has no origin.", parent_po.name)
                order.state = "cancel"
                continue

            pr_record = self.env["purchase.requisition"].search(
                [("name", "=", parent_po.origin)], limit=1
            )
            if not pr_record:
                _logger.warning(
                    "No Purchase Requisition found with name: %s", parent_po.origin
                )
                order.state = "cancel"
                continue

            if not pr_record.supervisor_partner_id:
                _logger.warning("PR %s has no supervisor_partner_id.", pr_record.name)
                order.state = "cancel"
                continue

            try:
                supervisor_id_int = int(pr_record.supervisor_partner_id)
            except ValueError:
                _logger.error(
                    "Supervisor Partner ID in PR %s is not a valid integer: %s",
                    pr_record.name,
                    pr_record.supervisor_partner_id,
                )
                order.state = "cancel"
                continue

            supervisor_partner = self.env["res.partner"].browse(supervisor_id_int)
            if supervisor_partner.exists():
                self.env["mail.activity"].create(
                    {
                        "res_model_id": self.env["ir.model"]._get_id("purchase.order"),
                        "res_id": order.id,
                        "activity_type_id": self.env.ref(
                            "mail.mail_activity_data_todo"
                        ).id,
                        "user_id": (
                            supervisor_partner.user_ids[:1].id
                            if supervisor_partner.user_ids
                            else False
                        ),
                        "note": _("Purchase Order %s was rejected by %s.<br/>Reason: %s")
                        % (order.name, rejecting_user.name, reason),
                    }
                )

                if supervisor_partner.email:
                    mail_values = {
                        "email_from": "hr@petroraq.com",
                        "subject": _("Purchase Order %s Rejected") % order.name,
                        "body_html": _(
                            "<p>Hello %s,</p>"
                            "<p>The Purchase Order <b>%s</b> has been rejected by <b>%s</b>.</p>"
                            "<p><b>Reason:</b> %s</p>"
                            "<p>Regards,<br/>%s</p>"
                        )
                        % (
                            supervisor_partner.name,
                            order.name,
                            rejecting_user.name,
                            reason,
                            rejecting_user.company_id.name,
                        ),
                        "email_to": supervisor_partner.email,
                    }
                    self.env["mail.mail"].create(mail_values).send()

            order.message_post(body=_("Purchase Order rejected by %s.<br/>Reason: %s") % (rejecting_user.name, reason))
            order.state = "cancel"

    # PO send by Email in RFQ
    def action_rfq_send(self):
        """Override to include all vendors (partner_id + vendor_ids) in email wizard."""
        self.ensure_one()
        res = super(PurchaseOrder, self).action_rfq_send()

        # Collect all vendors: partner_id + vendor_ids
        all_vendors = self.vendor_ids.ids
        if self.partner_id:
            if self.partner_id.id not in all_vendors:
                all_vendors = [self.partner_id.id] + all_vendors

        # Update wizard context with all vendors
        if res and isinstance(res, dict):
            ctx = res.get("context", {})
            ctx.update({"default_partner_ids": all_vendors})
            res["context"] = ctx

        return res

    def unlink(self):
        prs_to_update = self.mapped("origin")
        res = super(PurchaseOrder, self).unlink()

        pr_model = self.env["purchase.requisition"]
        for pr_name in prs_to_update:
            pr = pr_model.search([("name", "=", pr_name)], limit=1)
            if pr:
                pr.status = "pr"
                pr.message_post(body=_("PO deleted, status reverted to PR."))

        return res

    # def action_confirm(self):
    #     """Custom confirm: set state from pending → purchase"""
    #     for order in self:
    #         if order.state == "pending":
    #             order.state = "purchase"
    #         # Find the group
    #         group = self.env.ref("pr_custom_purchase.inventory_data_entry", raise_if_not_found=False)
    #         if group and group.users:
    #             for user in group.users.filtered(lambda u: u.active):
    #                 order.activity_schedule(
    #                     'mail.mail_activity_data_todo',  # Default TODO activity
    #                     user_id=user.id,
    #                     summary="Purchase Order Approved",
    #                     note=f"Purchase Order {order.name} has been approved."
    #                 )
    #     return True

    # def action_confirm(self):
    #     """Custom confirm: set state from pending → purchase + create/update product & update stock (Odoo 17)."""
    #     for order in self:
    #         # --- existing logic: move to purchase & schedule activities ---
    #         if order.state == "pending":
    #             order.state = "purchase"
    #         # Find the group
    #         group = self.env.ref("pr_custom_purchase.inventory_data_entry", raise_if_not_found=False)
    #         if group and group.users:
    #             for user in group.users.filtered(lambda u: u.active):
    #                 order.activity_schedule(
    #                     'mail.mail_activity_data_todo',  # Default TODO activity
    #                     user_id=user.id,
    #                     summary="Purchase Order Approved",
    #                     note=f"Purchase Order {order.name} has been approved."
    #                 )

    #         # --- gather lines to process ---
    #         if hasattr(order, "custom_line_ids") and order.custom_line_ids:
    #             lines = order.custom_line_ids
    #         else:
    #             lines = order.order_line

    #         aggregated = {}  # { product_name: { 'qty': total_qty, 'unit': custom_unit_record, 'sample_line': line } }
    #         for line in lines:
    #             # find a product name
    #             product_name = False
    #             for attr in ("name", "description", "product_name", "default_code"):
    #                 if getattr(line, attr, False):
    #                     product_name = getattr(line, attr)
    #                     break
    #             if not product_name and getattr(line, "product_id", False):
    #                 product_name = getattr(line.product_id, "name", False)

    #             # quantity
    #             qty = 0.0
    #             for qattr in ("quantity", "product_qty", "product_uom_qty", "qty"):
    #                 val = getattr(line, qattr, False)
    #                 if val:
    #                     try:
    #                         qty = float(val)
    #                         break
    #                     except Exception:
    #                         qty = 0.0

    #             custom_unit = getattr(line, "unit", False)

    #             if not product_name or qty <= 0:
    #                 continue

    #             key = str(product_name).strip()
    #             if key not in aggregated:
    #                 aggregated[key] = {"qty": qty, "unit": custom_unit, "sample_line": line}
    #             else:
    #                 aggregated[key]["qty"] += qty

    #         if not aggregated:
    #             continue

    #         env = self.env

    #         def _get_or_create_uom_from_custom_unit(cu):
    #             """Find or create a uom.uom matching custom.unit"""
    #             try:
    #                 if not cu:
    #                     return env.ref("uom.product_uom_unit")
    #                 name = cu.name if hasattr(cu, "name") else str(cu)
    #                 uom = env["uom.uom"].sudo().search([("name", "=", name)], limit=1)
    #                 if uom:
    #                     return uom
    #                 default_uom = env.ref("uom.product_uom_unit")
    #                 uom_vals = {
    #                     "name": name,
    #                     "category_id": default_uom.category_id.id,
    #                 }
    #                 return env["uom.uom"].sudo().create(uom_vals)
    #             except Exception:
    #                 return env.ref("uom.product_uom_unit")

    #         # decide stock location
    #         stock_location = env.ref("stock.stock_location_stock", raise_if_not_found=False)
    #         if not stock_location:
    #             stock_location = env["stock.location"].sudo().search([("usage", "=", "internal")], limit=1)
    #         if not stock_location:
    #             continue  # no internal stock location, skip

    #         # --- process each aggregated product ---
    #         for prod_name, info in aggregated.items():
    #             qty = info["qty"]
    #             custom_unit = info["unit"]

    #             # find or create product.template
    #             product_tmpl = env["product.template"].sudo().search([("name", "=", prod_name)], limit=1)
    #             if not product_tmpl:
    #                 uom = _get_or_create_uom_from_custom_unit(custom_unit)
    #                 try:
    #                     categ = env.ref("product.product_category_all")
    #                 except Exception:
    #                     categ = env["product.category"].sudo().search([], limit=1)

    #                 tmpl_vals = {
    #                     "name": prod_name,
    #                     "type": "product",  # storable product
    #                     "uom_id": uom.id if uom else env.ref("uom.product_uom_unit").id,
    #                     "uom_po_id": uom.id if uom else env.ref("uom.product_uom_unit").id,
    #                     "categ_id": categ.id if categ else False,
    #                     "list_price": info["sample_line"].price_unit or 0.0,
    #                     "standard_price": info["sample_line"].price_unit or 0.0,
    #                 }
    #                 product_tmpl = env["product.template"].sudo().create(tmpl_vals)

    #             product = product_tmpl.product_variant_id

    #             # update/create stock.quant
    #             quant = env["stock.quant"].sudo().search([
    #                 ("product_id", "=", product.id),
    #                 ("location_id", "=", stock_location.id),
    #             ], limit=1)

    #             if quant:
    #                 # quant.quantity += qty
    #                  quant.sudo().write({"quantity": quant.quantity + qty})
    #             else:
    #                 env["stock.quant"].sudo().create({
    #                     "product_id": product.id,
    #                     "location_id": stock_location.id,
    #                     "quantity": qty,
    #                 })

    #     return True
    def action_confirm(self):
        """Compatibility wrapper for buttons calling action_confirm on purchase orders."""
        return self.button_confirm()

    def _create_and_validate_receipt_from_custom_lines(self):
        """Deprecated custom receipt flow."""
        return True

    def create_grn_ses(self):
        raise UserError(_("GRN/SES custom flow is disabled. Use standard receipts and vendor bills."))

    @api.depends("state", "subtotal", "grand_total")
    def _compute_display_total(self):
        for order in self:
            if order.state == "purchase":
                order.display_total = order.grand_total
            else:
                order.display_total = order.subtotal

    @api.depends("order_line.product_id.type")
    def _compute_grn_ses_button_type(self):
        for order in self:
            order.grn_ses_button_type = False

class PurchaseOrderRejectWizard(models.TransientModel):
    _name = "purchase.order.reject.wizard"
    _description = "Purchase Order Reject Wizard"

    purchase_order_id = fields.Many2one("purchase.order", required=True, readonly=True)
    reason = fields.Text(string="Reason", required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        self.purchase_order_id.action_reject(reason=self.reason)
        return {"type": "ir.actions.act_window_close"}