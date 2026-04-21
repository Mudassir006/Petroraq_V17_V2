import logging
from odoo import _, models, fields, api
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class PurchaseRequisition(models.Model):
    _name = "purchase.requisition"
    _description = "Purchase Requisition"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name desc"

    name = fields.Char(
        string="PR Number", required=True, copy=False, readonly=True, default="New"
    )
    date_request = fields.Date(
        string="Date of Request", default=fields.Date.context_today
    )
    requested_by = fields.Char(string="Requested By")
    requested_user_id = fields.Many2one("res.users", string="Requested User", readonly=True)
    department = fields.Char(string="Department")
    supervisor = fields.Char(string="Supervisor")
    supervisor_partner_id = fields.Char(string="supervisor_partner_id")
    required_date = fields.Date(string="Required Date", readonly=True)
    priority = fields.Selection(
        [("low", "Low"), ("medium", "Medium"), ("high", "High"), ("urgent", "Urgent")],
        string="Priority",
        required=True,
        default="low",
    )
    budget_type = fields.Selection(
        [("opex", "Opex"), ("capex", "Capex")], string="Budget Type"
    )
    budget_details = fields.Char(string="Cost Center Code")
    cost_center_id = fields.Many2one("account.analytic.account", string="Cost Center")
    notes = fields.Text(string="Notes")
    approval = fields.Selection(
        [("pending", "Pending"), ("rejected", "Rejected"), ("approved", "Approved")],
        default="pending",
        string="Approval",
    )
    wo_variance_requires_approval = fields.Boolean(
        string="WO Variance Requires Approval",
        compute="_compute_wo_variance_requires_approval",
        store=False,
        help="Quantity/unit cost exceeds WO baseline but total requested amount remains within allowed WO amount.",
    )
    comments = fields.Text(string="Comments")
    vendor_id = fields.Many2one("res.partner", string="Preferred Vendor")
    total_excl_vat = fields.Float(
        string="Total Amount",
        compute="_compute_totals",
        store=True,
        currency_field="currency_id",
    )
    vat_amount = fields.Float(
        string="VAT (15%)",
        compute="_compute_totals",
        store=True,
        currency_field="currency_id",
    )
    total_incl_vat = fields.Float(
        string="Total Incl. VAT",
        compute="_compute_totals",
        store=True,
        currency_field="currency_id",
    )
    pr_type = fields.Selection(
        [
            ("pr", "PR"),
            ("cash", "Cash PR"),
        ],
        string="Type",
        default="pr",
    )
    is_supervisor = fields.Boolean(
        string="Can Approve",
        compute="_compute_is_supervisor",
    )
    status = fields.Selection(
        [("pr", "PR"), ("rfq", "RFQ"), ("po", "PO"), ("completed", "Completed")],
        default="pr",
        string="PR Status",
    )
    line_ids = fields.One2many(
        "purchase.requisition.line", "requisition_id", string="Line Items"
    )
    rfq_ids = fields.One2many("purchase.order", "requisition_id", string="RFQs")
    rfq_count = fields.Integer(string="RFQ Count", compute="_compute_rfq_metrics")
    rfq_sent_count = fields.Integer(string="RFQ Sent Count", compute="_compute_rfq_metrics")

    # Computed fields for button visibility logic
    show_create_rfq_button = fields.Boolean(
        compute="_compute_button_visibility", store=False
    )
    show_create_po_button = fields.Boolean(
        compute="_compute_button_visibility", store=False
    )
    show_request_budget_increase_button = fields.Boolean(
        compute="_compute_show_request_budget_increase_button", store=False
    )
    project_id = fields.Many2one("project.project", string="Project")
    expense_bucket_id = fields.Many2one("pr.expense.bucket", string="Expense")
    expense_scope = fields.Selection(
        [("department", "Department"), ("project", "Project")],
        string="Expense Scope",
    )
    expense_type = fields.Selection(
        [("opex", "Opex"), ("capex", "Capex")],
        string="Expense Type",
    )

    def _required_date_from_priority(self, priority):
        today = fields.Date.context_today(self)
        offsets = {
            "low": 30,
            "medium": 10,
            "high": 3,
            "urgent": 0,
        }
        return today + relativedelta(days=offsets.get(priority, 0))

    @api.onchange("priority")
    def _onchange_priority_set_required_date(self):
        for rec in self:
            if rec.priority:
                rec.required_date = rec._required_date_from_priority(rec.priority)

    @api.model
    def create(self, vals):
        if vals.get("priority"):
            vals["required_date"] = self._required_date_from_priority(vals["priority"])

        if not vals.get("requested_user_id"):
            vals["requested_user_id"] = self.env.user.id

        requester = self.env["res.users"].sudo().browse(vals.get("requested_user_id")) if vals.get(
            "requested_user_id") else self.env.user

        employee = self.env["hr.employee"].sudo().search([
            ("user_id", "=", requester.id)
        ], limit=1) if requester else False

        if not vals.get("requested_by"):
            vals["requested_by"] = employee.name if employee else (requester.name if requester else self.env.user.name)

        if not vals.get("department") and employee and employee.department_id:
            vals["department"] = employee.department_id.name

        supervisor_user = requester.supervisor_user_id if requester else False
        if supervisor_user:
            vals["supervisor"] = vals.get("supervisor") or supervisor_user.name
            vals["supervisor_partner_id"] = vals.get("supervisor_partner_id") or str(supervisor_user.partner_id.id)

        record = super().create(vals)
        if record.name == "New":
            if record.pr_type == "cash":
                record.name = (
                        self.env["ir.sequence"]
                        .sudo()
                        .next_by_code("cash.purchase.requisition")
                        or "CPR0001"
                )
            else:
                record.name = (
                        self.env["ir.sequence"].sudo().next_by_code("purchase.requisition")
                        or "PR0001"
                )
        record._notify_supervisor()
        return record

    # Checking when PR is approved
    def write(self, vals):
        if vals.get("priority"):
            vals["required_date"] = self._required_date_from_priority(vals["priority"])

        approval_changed = "approval" in vals
        res = super().write(vals)

        if approval_changed:
            for requisition in self:
                new_approval = vals.get("approval", requisition.approval)
                custom_pr = (
                    self.env["custom.pr"]
                    .sudo()
                    .search([("name", "=", requisition.name)], limit=1)
                )

                if custom_pr:
                    # Sync approval → state
                    if new_approval == "approved" and custom_pr.approval != "approved":
                        custom_pr.write(
                            {"approval": "approved"}
                        )
                        self._notify_procurement_admins()

                    elif (
                            new_approval == "rejected" and custom_pr.approval != "rejected"
                    ):
                        custom_pr.write(
                            {"approval": "rejected"}
                        )

                    elif new_approval == "pending" and custom_pr.approval != "pending":
                        custom_pr.write({"approval": "pending"})

        return res

    @api.depends("line_ids.total_price")
    def _compute_totals(self):
        for rec in self:
            total = sum(line.total_price for line in rec.line_ids)
            rec.total_excl_vat = total
            rec.vat_amount = total * 0.15
            rec.total_incl_vat = total + rec.vat_amount

    @api.depends("rfq_ids", "rfq_ids.state")
    def _compute_rfq_metrics(self):
        for rec in self:
            rec.rfq_count = len(rec.rfq_ids)
            rec.rfq_sent_count = len(rec.rfq_ids.filtered(lambda r: r.state == "sent"))

    @api.depends("pr_type", "approval", "status", "rfq_ids", "rfq_ids.state")
    def _compute_button_visibility(self):
        """Compute button visibility based on PR type, approval, status and existing PO state."""
        for rec in self:
            has_po = bool(rec.rfq_ids.filtered(lambda r: r.state in ("pending", "purchase", "done")))
            rec.show_create_rfq_button = (
                    rec.pr_type != "cash"
                    and rec.approval == "approved"
                    and rec.status in ["pr", "rfq"]
                    and not has_po
            )

            rec.show_create_po_button = (
                    rec.pr_type == "cash"
                    and rec.approval == "approved"
                    and rec.status in ["pr", "rfq"]
                    and not has_po
            )

    @api.depends(
        "line_ids.quantity",
        "line_ids.unit_price",
        "line_ids.cost_center_id",
        "line_ids.description",
    )
    def _compute_wo_variance_requires_approval(self):
        for rec in self:
            variance_found = False
            for line in rec.line_ids:
                caps = line._get_wo_product_caps()
                if not caps:
                    continue
                if line.quantity > caps["allowed_qty"] or line.unit_price > caps["allowed_unit_price"]:
                    variance_found = True
                    break
            rec.wo_variance_requires_approval = variance_found

    @api.depends("line_ids.total_price", "line_ids.cost_center_id", "line_ids.cost_center_id.budget_left")
    def _compute_show_request_budget_increase_button(self):
        for rec in self:
            amount_by_cost_center = {}
            for line in rec.line_ids:
                line_cc = line.cost_center_id
                if not line_cc:
                    continue
                amount_by_cost_center.setdefault(line_cc.id, {"cc": line_cc, "amount": 0.0})
                amount_by_cost_center[line_cc.id]["amount"] += line.total_price

            rec.show_request_budget_increase_button = any(
                item["amount"] > item["cc"].budget_left for item in amount_by_cost_center.values()
            )

    def action_request_budget_increase(self):
        self.ensure_one()
        line_amounts = {}
        for line in self.line_ids:
            line_cc = line.cost_center_id.sudo()
            if not line_cc:
                continue
            line_amounts.setdefault(line_cc.id, {"cc": line_cc, "amount": 0.0})
            line_amounts[line_cc.id]["amount"] += line.total_price

        exceeded_cost_centers = [
            item for item in line_amounts.values() if item["amount"] > item["cc"].budget_left
        ]

        if not exceeded_cost_centers:
            raise ValidationError(
                _("All cost center lines are within budget. Budget increase request is not required.")
            )

        custom_pr = self.env["custom.pr"].sudo().search([("name", "=", self.name)], limit=1)

        request = self.env["budget.increase.request"].create({
            "custom_pr_id": custom_pr.id,
            "requisition_id": self.id,
            "reason": _("Budget increase requested for PR %s") % self.name,
            "line_ids": [
                (0, 0, {
                    "cost_center_id": item["cc"].id,
                    "requested_increase": max(item["amount"] - item["cc"].budget_left, 1.0),
                })
                for item in exceeded_cost_centers
            ],
        })

        return {
            "type": "ir.actions.act_window",
            "name": _("Budget Increase Request"),
            "res_model": "budget.increase.request",
            "res_id": request.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_supervisor_approve(self):
        for rec in self:
            if rec.approval != "pending":
                continue
            rec.write({"approval": "approved"})

    def action_supervisor_reject_wizard(self):
        self.ensure_one()
        if self.approval != "pending":
            return False
        return {
            "type": "ir.actions.act_window",
            "name": _("Reject Purchase Requisition"),
            "res_model": "purchase.requisition.reject.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_requisition_id": self.id},
        }

    # sending activity to configured supervisor when PR is created
    def _notify_supervisor(self):
        for rec in self:
            try:
                requester = rec.requested_user_id.sudo() if rec.requested_user_id else self.env.user.sudo()
                supervisor_user = requester.supervisor_user_id if requester else False

                if not supervisor_user:
                    _logger.warning("No supervisor configured for requester on PR=%s", rec.name)
                    continue

                rec.activity_schedule(
                    activity_type_id=self.env.ref("mail.mail_activity_data_todo").id,
                    user_id=supervisor_user.id,
                    summary="Review New PR",
                    note=_("Please review the new Purchase Requisition: <b>%s</b>.") % rec.name,
                )
                if supervisor_user.email:
                    self.env["mail.mail"].sudo().create({
                        "email_from": "hr@petroraq.com",
                        "email_to": supervisor_user.email,
                        "subject": _("Purchase Requisition %s waiting for approval") % rec.name,
                        "body_html": _(
                            "<p>Dear Approver,</p><p>Please review Purchase Requisition <b>%s</b>.</p>") % rec.name,
                    }).send()
                _logger.info("Activity created for supervisor %s on PR=%s", supervisor_user.login, rec.name)

            except Exception as e:
                _logger.error("Error creating supervisor activity for PR=%s: %s", rec.name, str(e))

    # sending approved PR activity to procurment admin
    def _notify_procurement_admins(self):
        for pr in self:
            try:
                group = self.env.ref(
                    "pr_custom_purchase.procurement_admin"
                )  # 🔁 Replace
                procurement_users = (
                    self.env["res.users"].sudo().search([("groups_id", "in", group.id)])
                )
                activity_type_id = self.env.ref("mail.mail_activity_data_todo").id

                for user in procurement_users:
                    pr.activity_schedule(
                        activity_type_id=activity_type_id,
                        user_id=user.id,
                        summary="New Approved PR",
                        note=_(
                            "A new Purchase Requisition <b>%s</b> has been approved."
                        )
                             % pr.name,
                    )
                    if user.email:
                        self.env["mail.mail"].sudo().create({
                            "email_from": "hr@petroraq.com",
                            "email_to": user.email,
                            "subject": _("Approved Purchase Requisition %s") % pr.name,
                            "body_html": _(
                                "<p>Purchase Requisition <b>%s</b> is approved and ready for processing.</p>") % pr.name,
                        }).send()

                requester_email = pr.requested_user_id.email if pr.requested_user_id else False
                if requester_email:
                    self.env["mail.mail"].sudo().create({
                        "email_from": "hr@petroraq.com",
                        "email_to": requester_email,
                        "subject": _("Your Purchase Requisition %s is approved") % pr.name,
                        "body_html": _(
                            "<p>Your Purchase Requisition <b>%s</b> has been approved and sent to Procurement.</p>") % pr.name,
                    }).send()

                _logger.info(
                    "Activities scheduled for Procurement Admins on PR=%s", pr.name
                )

            except Exception as e:
                _logger.error(
                    "Error creating procurement admin activities for PR=%s: %s",
                    pr.name,
                    str(e),
                )

    # create RFQ PR
    # def action_create_rfq(self):
    #     """Create RFQ (purchase.order) from this PR and populate Custom Lines tab."""
    #     PurchaseOrder = self.env["purchase.order"]

    #     for pr in self:
    #         if not pr.line_ids:
    #             raise UserError(_("This PR has no line items to create an RFQ."))

    #         matched_project = self.env["project.project"].search(
    #             [
    #                 ("budget_type", "=", pr.budget_type),
    #                 ("budget_code", "=", pr.budget_details),
    #             ],
    #             limit=1,
    #         )

    #         # Create RFQ without normal order_line
    #         rfq_vals = {
    #             "origin": pr.name,
    #             "partner_id": pr.vendor_id.id if pr.vendor_id else False,
    #             'pr_name': self.name,
    #             "date_planned": pr.required_date,
    #             "budget_type": pr.budget_type,
    #             "budget_code": pr.budget_details,
    #             "order_line": [],  # Populate custom tab instead
    #             "date_request": pr.date_request,
    #             "requested_by": pr.requested_by,
    #             "department": pr.department,
    #             "supervisor": pr.supervisor,
    #             "supervisor_partner_id": pr.supervisor_partner_id,
    #         }

    #         # Fill custom_line_ids from PR lines
    #         for line in pr.line_ids:
    #             line_vals = (
    #                 0,
    #                 0,
    #                 {
    #                     "name": line.description,
    #                     "quantity": line.quantity,
    #                     "type": line.type,
    #                     "unit": line.unit,  # ✅ Added this
    #                     "price_unit": line.unit_price,
    #                 },
    #             )
    #             rfq_vals["custom_line_ids"].append(line_vals)

    #         # Create RFQ
    #         rfq = PurchaseOrder.sudo().create(rfq_vals)

    #         # sequence for Rfq
    #         if rfq.state == "draft":
    #             rfq.name = (
    #                 self.env["ir.sequence"].next_by_code("purchase.order.rfq")
    #                 or "RFQ0001"
    #             )

    #         # Update PR status
    #         pr.status = "rfq"

    #         # Log in PR chatter
    #         pr.message_post(
    #             body=_("RFQ %s created from this PR and populated in Custom Lines tab.")
    #             % rfq.name,
    #             message_type="notification",
    #         )

    #     return {
    #         "type": "ir.actions.act_window",
    #         "name": _("Purchase Order"),
    #         "res_model": "purchase.order",
    #         "res_id": rfq.id,
    #         "view_mode": "form",
    #         "target": "current",
    #     }
    def action_view_related_rfqs(self):
        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "name": "RFQs",
            "res_model": "purchase.order",
            "view_mode": "tree,form",
            "domain": [("requisition_id", "=", self.id)],
            "context": {
                "default_requisition_id": self.id,
                "default_pr_name": self.name,
            },
        }

    def _ensure_no_purchase_order_exists(self):
        self.ensure_one()
        existing_po = self.env["purchase.order"].sudo().search_count([
            ("requisition_id", "=", self.id),
            ("state", "in", ["pending", "purchase", "done"]),
        ])
        if existing_po:
            raise UserError(_("A Purchase Order already exists for requisition %s.") % self.name)

    def action_create_rfq(self):
        """Create Custom RFQ from this PR and keep PO sequencing independent."""
        CustomRFQ = self.env["purchase.order"]

        rfq = False
        for pr in self:
            if pr.approval != "approved":
                raise UserError(_("Supervisor approval is required before creating RFQ."))
            pr._ensure_no_purchase_order_exists()
            if not pr.line_ids:
                raise UserError(_("This PR has no line items to create an RFQ."))

            line_amounts = {}
            for line in pr.line_ids:
                line_cc = line.cost_center_id.sudo()
                if not line_cc:
                    raise UserError(_("Please set a cost center on every PR line."))
                line_amounts.setdefault(line_cc.id, {"cc": line_cc, "amount": 0.0})
                line_amounts[line_cc.id]["amount"] += line.total_price

            for item in line_amounts.values():
                cc = item["cc"]
                if cc.budget_left < item["amount"]:
                    raise UserError(
                        _("Insufficient budget for cost center %s. Remaining: %s, Required: %s")
                        % (cc.display_name, cc.budget_left, item["amount"])
                    )

            rfq_vals = {
                "name": self.env["ir.sequence"].sudo().next_by_code("purchase.order.rfq") or _("New"),
                "origin": pr.name,
                "requisition_id": pr.id,
                "partner_id": pr.vendor_id.id if pr.vendor_id else False,
                "pr_name": pr.name,
                "date_planned": pr.required_date,
                "order_line": [],
                "date_request": pr.date_request,
                "requested_by": pr.requested_by,
                "department": pr.department,
                "supervisor": pr.supervisor,
                "supervisor_partner_id": pr.supervisor_partner_id,
                "project_id": pr.project_id.id if pr.project_id else False,
                "budget_type": pr.budget_type,
                "budget_code": pr.budget_details,
            }

            for line in pr.line_ids:
                analytic_distribution = (
                    {str(line.cost_center_id.id): 100.0}
                    if line.cost_center_id
                    else False
                )
                rfq_vals["order_line"].append((0, 0, {
                    "name": line.description.display_name,
                    "product_id": line.description.id,
                    "product_qty": line.quantity,
                    "price_unit":0.0,
                    "date_planned": fields.Datetime.now(),
                    "analytic_distribution": analytic_distribution,
                }))

            rfq = CustomRFQ.sudo().create(rfq_vals)
            if not rfq.name or rfq.name == "New" or "RFQ" not in (rfq.name or ""):
                rfq.sudo().write({
                    "name": self.env["ir.sequence"].sudo().next_by_code("purchase.order.rfq") or "RFQ0001"
                })

            pr.status = "rfq"
            pr.message_post(
                body=_("Custom RFQ %s created from this PR.") % rfq.name,
                message_type="notification",
            )

        return {
            "type": "ir.actions.act_window",
            "name": _("Custom RFQ"),
            "res_model": "purchase.order",
            "res_id": rfq.id,
            "view_mode": "form",
            "target": "current",
        }

    # create cash PR
    def action_create_purchase_order(self):
        """Create a PO from cash PR using the same approval entry point as RFQ-selected POs."""
        PurchaseOrder = self.env["purchase.order"]

        for pr in self:
            if pr.approval != "approved":
                raise UserError(_("Supervisor approval is required before creating Purchase Order."))
            pr._ensure_no_purchase_order_exists()
            if not pr.line_ids:
                raise UserError(
                    _("This PR has no line items to create a Purchase Order.")
                )

            line_amounts = {}
            for line in pr.line_ids:
                line_cc = line.cost_center_id.sudo()
                if not line_cc:
                    raise UserError(_("Please set a cost center on every PR line."))
                line_amounts.setdefault(line_cc.id, {"cc": line_cc, "amount": 0.0})
                line_amounts[line_cc.id]["amount"] += line.total_price

            for item in line_amounts.values():
                cc = item["cc"]
                if cc.budget_left < item["amount"]:
                    raise UserError(
                        _("Insufficient budget for cost center %s. Remaining: %s, Required: %s")
                        % (cc.display_name, cc.budget_left, item["amount"])
                    )

            # Create PO values aligned with action_create_po_from_rfq (pending + approval flags)
            po_name = self.env["ir.sequence"].sudo().next_by_code("purchase.order") or "PO0001"
            po_vals = {
                "name": po_name,
                "state": "pending",
                "origin": pr.name,
                "pr_name": pr.name,
                "requisition_id": pr.id,
                "partner_id": pr.vendor_id.id if pr.vendor_id else False,
                "date_planned": pr.required_date or fields.Datetime.now(),
                "project_id": pr.project_id.id if pr.project_id else False,
                "budget_type": pr.budget_type,
                "budget_code": pr.budget_details,
                "order_line": [],
                "date_request": pr.date_request,
                "requested_by": pr.requested_by,
                "department": pr.department,
                "supervisor": pr.supervisor,
                "supervisor_partner_id": pr.supervisor_partner_id,
                "pe_approved": False,
                "pm_approved": False,
                "od_approved": False,
                "md_approved": False,
            }

            for line in pr.line_ids:
                analytic_distribution = (
                    {str(line.cost_center_id.id): 100.0}
                    if line.cost_center_id
                    else False
                )
                line_vals = (
                    0,
                    0,
                    {
                        "name": line.description.display_name,
                        "product_id": line.description.id,
                        "product_qty": line.quantity,
                        "product_uom": line.description.uom_po_id.id if line.description.uom_po_id else False,
                        "price_unit": line.unit_price,
                        "date_planned": fields.Datetime.now(),
                        "analytic_distribution": analytic_distribution,
                    },
                )
                po_vals["order_line"].append(line_vals)

            po = PurchaseOrder.sudo().create(po_vals)

            amount = po.subtotal
            if amount <= 10000:
                po._schedule_activity_for_group(
                    "pr_custom_purchase.project_engineer",
                    "Review Purchase Order",
                    f"PO {po.name} created from cash PR {pr.name}. Please review.",
                )
            elif amount <= 100000:
                for group_xml_id in ["pr_custom_purchase.project_engineer", "pr_custom_purchase.project_manager"]:
                    po._schedule_activity_for_group(
                        group_xml_id,
                        "Review Purchase Order",
                        f"PO {po.name} created from cash PR {pr.name}. Please review.",
                    )
            elif amount <= 500000:
                for group_xml_id in [
                    "pr_custom_purchase.project_engineer",
                    "pr_custom_purchase.project_manager",
                    "pr_custom_purchase.operations_director",
                ]:
                    po._schedule_activity_for_group(
                        group_xml_id,
                        "Review Purchase Order",
                        f"PO {po.name} created from cash PR {pr.name}. Please review.",
                    )
            else:
                for group_xml_id in [
                    "pr_custom_purchase.project_engineer",
                    "pr_custom_purchase.project_manager",
                    "pr_custom_purchase.operations_director",
                    "pr_custom_purchase.managing_director",
                ]:
                    po._schedule_activity_for_group(
                        group_xml_id,
                        "Review Purchase Order",
                        f"PO {po.name} created from cash PR {pr.name}. Please review.",
                    )

            pr.status = "po"
            pr.message_post(
                body=_(
                    "Purchase Order %s created from this PR and moved to pending approval."
                )
                % po.name,
                message_type="notification",
            )

        return {
            "type": "ir.actions.act_window",
            "name": _("Purchase Order"),
            "res_model": "purchase.order",
            "res_id": po.id,
            "view_mode": "form",
            "target": "current",
        }

    # check user if he/she is supervisor
    @api.depends("supervisor_partner_id")
    def _compute_is_supervisor(self):
        for rec in self:
            try:
                supervisor_partner_id = (
                    int(rec.supervisor_partner_id) if rec.supervisor_partner_id else 0
                )
            except (ValueError, TypeError):
                supervisor_partner_id = 0

            current_user = rec.env.user
            current_partner_id = current_user.partner_id.id if current_user.partner_id else 0
            requester_supervisor = rec.requested_user_id.supervisor_user_id if rec.requested_user_id else False

            rec.is_supervisor = (
                    (requester_supervisor and requester_supervisor.id == current_user.id)
                    or (supervisor_partner_id == current_partner_id)
            )


class PurchaseRequisitionRejectWizard(models.TransientModel):
    _name = "purchase.requisition.reject.wizard"
    _description = "Purchase Requisition Rejection Wizard"

    requisition_id = fields.Many2one("purchase.requisition", string="Purchase Requisition", required=True)
    rejection_reason = fields.Text(string="Reason for Rejection", required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        if self.requisition_id.approval != "pending":
            return {"type": "ir.actions.act_window_close"}
        self.requisition_id.write({
            "approval": "rejected",
            "rejection_reason": self.rejection_reason,
        })
        return {"type": "ir.actions.act_window_close"}


class PurchaseRequisitionLine(models.Model):
    _name = "purchase.requisition.line"
    _description = "Purchase Requisition Line"

    requisition_id = fields.Many2one(
        "purchase.requisition", string="Requisition", ondelete="cascade"
    )
    description = fields.Many2one(
        'product.product',
        string="Product",
        required=True,
        ondelete="restrict",
        context={'display_default_code': False},
    )

    type = fields.Char(string="Type")
    quantity = fields.Float(string="Quantity")
    unit = fields.Char(string="Unit")
    unit_price = fields.Float(string="Unit Cost")
    cost_center_id = fields.Many2one(
        "account.analytic.account", string="Cost Center", required=True,
        domain="[('expense_bucket_id', '=', requisition_id.expense_bucket_id)]",
    )

    @api.constrains("cost_center_id", "requisition_id")
    def _check_cost_center_matches_bucket(self):
        for rec in self:
            if rec.cost_center_id and rec.requisition_id.expense_bucket_id and rec.cost_center_id.expense_bucket_id != rec.requisition_id.expense_bucket_id:
                raise ValidationError(_("Selected cost center must belong to the selected expense bucket."))

    total_price = fields.Float(string="Total", compute="_compute_total", store=True)

    @api.depends("quantity", "unit_price")
    def _compute_total(self):
        for rec in self:
            rec.total_price = rec.quantity * rec.unit_price

    @api.constrains("quantity", "unit_price")
    def _check_non_negative_values(self):
        for rec in self:
            if rec.quantity < 0:
                raise ValidationError("Quantity cannot be negative.")
            if rec.unit_price < 0:
                raise ValidationError("Unit Price cannot be negative.")

    def _get_wo_product_caps(self):
        self.ensure_one()

        if not self.cost_center_id or not self.description:
            return False

        if "pr.work.order.cost.center" not in self.env:
            return False

        wo_cc = self.env["pr.work.order.cost.center"].sudo().search([
            ("analytic_account_id", "=", self.cost_center_id.id),
            ("work_order_id.state", "in",
             ["ops_approval", "acc_approval", "final_approval", "approved", "in_progress", "done"]),
        ], limit=1)

        if not wo_cc:
            return False

        boq_lines = wo_cc.work_order_id.boq_line_ids.filtered(
            lambda l: l.display_type not in ("line_section", "line_note")
                      and l.section_name == wo_cc.section_name
                      and l.product_id
                      and l.product_id.id == self.description.id
        )

        if not boq_lines:
            return {
                "allowed_qty": 0.0,
                "allowed_unit_price": 0.0,
                "allowed_amount": 0.0,
                "work_order": wo_cc.work_order_id,
                "section_name": wo_cc.section_name,
            }

        return {
            "allowed_qty": sum(boq_lines.mapped("qty")),
            "allowed_unit_price": max(boq_lines.mapped("unit_cost") or [0.0]),
            "allowed_amount": sum(boq_lines.mapped("total")),
            "work_order": wo_cc.work_order_id,
            "section_name": wo_cc.section_name,
        }

    @api.constrains("cost_center_id", "description", "quantity", "unit_price", "requisition_id")
    def _check_work_order_product_limits(self):
        for rec in self:
            if not rec.cost_center_id or not rec.description:
                continue

            caps = rec._get_wo_product_caps()
            if not caps:
                continue

            if not caps["allowed_qty"]:
                raise ValidationError(_(
                    "Product '%(product)s' is not budgeted in Work Order '%(wo)s' section '%(section)s' for cost center '%(cc)s'."
                ) % {
                                          "product": rec.description.display_name,
                                          "wo": caps["work_order"].display_name,
                                          "section": caps["section_name"] or "-",
                                          "cc": rec.cost_center_id.display_name,
                                      })

            current_req_lines = rec.requisition_id.line_ids.filtered(
                lambda l: l.cost_center_id.id == rec.cost_center_id.id
                          and l.description.id == rec.description.id
            )
            current_req_amount = sum(current_req_lines.mapped("total_price"))

            other_pr_lines = self.env["purchase.requisition.line"].sudo().search([
                ("id", "not in", rec.requisition_id.line_ids.ids),
                ("cost_center_id", "=", rec.cost_center_id.id),
                ("description", "=", rec.description.id),
                ("requisition_id.approval", "!=", "rejected"),
            ])
            total_requested_amount = current_req_amount + sum(other_pr_lines.mapped("total_price"))

            if total_requested_amount > caps["allowed_amount"]:
                raise ValidationError(_(
                    "Requested amount for '%(product)s' exceeds Work Order amount for cost center '%(cc)s'. Allowed: %(allowed)s, Requested (including other PRs): %(requested)s."
                ) % {
                                          "product": rec.description.display_name,
                                          "cc": rec.cost_center_id.display_name,
                                          "allowed": caps["allowed_amount"],
                                          "requested": total_requested_amount,
                                      })


class PurchaseQuotation(models.Model):
    _inherit = "purchase.order"

    project_id = fields.Many2one("project.project", string="Project")
    budget_type = fields.Selection(
        [("opex", "Opex"), ("capex", "Capex")], string="Budget Type"
    )

    budget_code = fields.Char(string="Budget Code")


class PurchaseOrderCustomLine(models.Model):
    _name = "purchase.order.custom.line"
    _description = "Custom Purchase Order Line"

    order_id = fields.Many2one(
        "purchase.order", string="Purchase Order", ondelete="cascade"
    )
    name = fields.Char(string="Description")
    quantity = fields.Float(string="Quantity")
    unit = fields.Char(string="Unit")
    type = fields.Selection(
        [
            ('material', 'Material'),
            ('service', 'Service')
        ],
        string="Type",
        default='material',
        required=True
    )
    price_unit = fields.Float(string="Unit Price")
    cost_center_id = fields.Many2one("account.analytic.account", string="Cost Center", required=True)
    subtotal = fields.Float(string="Subtotal", compute="_compute_subtotal", store=True)

    @api.depends("quantity", "price_unit")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price_unit

    @api.constrains("quantity", "price_unit")
    def _check_non_negative_subtotal_inputs(self):
        for line in self:
            if line.quantity < 0:
                raise ValidationError("Quantity cannot be negative.")
            if line.price_unit < 0:
                raise ValidationError("Unit Price cannot be negative.")