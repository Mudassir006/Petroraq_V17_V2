from odoo import api, models, fields, _
from odoo.exceptions import ValidationError
from datetime import timedelta
import re
from odoo.exceptions import UserError


class OrderInquiry(models.Model):
    _name = 'order.inq'
    _order = 'sequence, date_order, id'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(default="New", readonly=True, copy=False, tracking=True, string="Inquiry No")
    description = fields.Char(string="Inquiry Description", required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id.id, string='Company')
    contact_person = fields.Char(string="Contact Person", required=True)
    designation = fields.Char(string="Designation")
    user_id = fields.Many2one('res.users', string='Inquiry By',
                              domain=lambda self: self._get_salesperson_domain(), required=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, )
    email = fields.Char(string="Customer Email", related='partner_id.email')
    contact_person_email = fields.Char(string="Contact Person Email", required=True)
    contact_person_phone = fields.Char(string="Contact Person Phone", required=True)
    state = fields.Selection(
        [
            ('pending', 'Pending'),
            ('confirm', 'Submitted'),
            ('accept', 'Accepted'),
            ('estimation_created', 'Estimation Created'),
            ('quotation_created', 'Quotation Created'),
            ('closed', 'Closed'),
            ('cancel', 'Cancelled'),
            ('reject', 'Rejected'),
            ('expire', 'Expired'),
        ],
        default='pending', string='State', tracking=True)
    deadline_submission = fields.Date(string="Deadline", required=True, tracking=True)
    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    sale_order_ids = fields.Many2many('sale.order', string="Sale Order's")
    multi_order = fields.Boolean('Multi Orders')
    sale_count = fields.Integer(compute="compute_sale_count", store=True)
    estimation_id = fields.Many2one("petroraq.estimation", string="Estimation")
    estimation_ids = fields.One2many("petroraq.estimation", "order_inquiry_id", string="Estimations")
    estimation_count = fields.Integer(compute="_compute_estimation_count", store=False)

    date_order = fields.Datetime(string="Inquiry Date", required=True, readonly=False, copy=False, help="Inquiry Date",
                                 default=fields.Datetime.now)
    sequence = fields.Integer(string="Sequence", default=10)

    rejection_reason = fields.Text(string="Rejection Reason", tracking=True)
    inquiry_type = fields.Selection([('construction', 'Project'), ('trading', 'Trading')], string="Inquiry Type",
                                    default="construction", required=True)
    required_attachment_ids = fields.Many2many(
        "ir.attachment",
        "order_inq_required_attachment_rel",
        "order_inq_id",
        "attachment_id",
        string="Required Attachments",
    )

    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )

    quotation_main_id = fields.Many2one(
        "sale.order",
        string="Main Quotation",
        compute="_compute_quotation_main",
        store=True,
        readonly=True,
    )

    quotation_state = fields.Selection(
        related="quotation_main_id.state",
        string="Quotation Status",
        store=True,
        readonly=True,
    )

    quotation_approval_state = fields.Selection(
        related="quotation_main_id.approval_state",
        string="Quotation Approval Status",
        store=True,
        readonly=True,
    )

    quotation_amount_total = fields.Monetary(
        related="quotation_main_id.profit_grand_total",
        string="Quotation Total",
        currency_field="currency_id",
        store=True,
        readonly=True,
    )
    contact_partner_id = fields.Many2one(
        "res.partner",
        string="Contact Partner",
        help="Contact created/linked for this inquiry contact person."
    )

    def _get_or_create_contact_partner(self):
        self.ensure_one()
        if self.contact_partner_id:
            return self.contact_partner_id

        parent = self.partner_id
        email = (self.contact_person_email or "").strip().lower()
        phone = (self.contact_person_phone or "").strip()

        # 1) Try to find existing child contact by email (best key)
        domain = [("parent_id", "=", parent.id)]
        if email:
            domain += [("email", "=", email)]
        else:
            # fallback if no email: match by name + phone
            domain += [("name", "=", (self.contact_person or "").strip())]
            if phone:
                domain += [("phone", "=", phone)]

        contact = self.env["res.partner"].search(domain, limit=1)

        # 2) Create if not found
        if not contact:
            contact = self.env["res.partner"].create({
                "name": (self.contact_person or "").strip(),
                "parent_id": parent.id,
                "type": "contact",
                "email": email or False,
                "phone": phone or False,
                "function": (self.designation or "").strip() or False,
                # optional:
                # "mobile": phone or False,
            })

        self.contact_partner_id = contact.id
        return contact

    @api.depends("sale_order_id", "sale_order_ids")
    def _compute_quotation_main(self):
        for rec in self:
            if rec.sale_order_id:
                rec.quotation_main_id = rec.sale_order_id
            elif rec.sale_order_ids:
                rec.quotation_main_id = rec.sale_order_ids.sorted("id")[-1]
            else:
                rec.quotation_main_id = False

    def _inq_default_construction_sections(self):
        """Return section titles to create on quotation for construction inquiries."""
        return ["Material:", "Equipment/Tools", "Third Party Services", "Labor"]

    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        default.update({
            'sale_order_id': False,
            'sale_order_ids': [(6, 0, [])],
            'state': 'pending',
            'name': 'New',
            'inquiry_type': 'construction',
        })
        return super().copy(default)

    def _get_salesperson_domain(self):
        return [
            ('groups_id', 'in', (
                    self.env.ref('sales_team.group_sale_salesman').ids +
                    self.env.ref('sales_team.group_sale_manager').ids
            ))
        ]

    @api.model
    def _cron_expire_inquiries_without_quotation(self):
        today = fields.Date.today()

        inquiries = self.search([
            ('state', 'in', ['accept', 'confirm']),
            ('deadline_submission', '<', today),
            ('sale_order_ids', '=', False),
        ])

        for inquiry in inquiries:
            inquiry.write({
                'state': 'expire',
            })

    def _notify_inquiry_approvers(self):
        self.ensure_one()
        group = self.env.ref('sales_team.group_sale_manager', raise_if_not_found=False)
        if not group:
            return
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        record_url = f"{base_url}/web#id={self.id}&model=order.inq&view_type=form"
        summary = _("Inquiry %s requires review") % self.name
        note = _("Please review inquiry %s and take the needed approval action.") % self.name
        for user in group.users.filtered(lambda u: u.active):
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=user.id,
                summary=summary,
                note=note,
            )
            if user.email:
                self.env['mail.mail'].sudo().create({
                    'email_from': 'hr@petroraq.com',
                    'email_to': user.email,
                    'subject': summary,
                    'body_html': f"<p>Dear Approver,</p><p>{note}</p><p><a href='{record_url}'>Open Inquiry</a></p>",
                }).send()

    def action_reset_to_draft(self):
        self.write({
            'state': 'pending',
        })

    @api.constrains('contact_person_email', 'contact_person_phone')
    def _check_email_and_phone(self):
        email_regex = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
        phone_regex = r"^\+?[0-9\s\-]{7,15}$"

        for rec in self:
            if rec.contact_person_email:
                if not re.match(email_regex, rec.contact_person_email):
                    raise ValidationError(
                        _("Invalid email format. Example: name@example.com")
                    )

            if rec.contact_person_phone:
                if not re.match(phone_regex, rec.contact_person_phone):
                    raise ValidationError(
                        _("Invalid phone number. Use digits only, minimum 9 digits, optionally starting with +")
                    )

    @api.constrains('contact_person')
    def _check_contact_person_chars(self):

        pattern = r"^[a-zA-Z .'-]+$"

        for rec in self:
            if rec.contact_person and not re.match(pattern, rec.contact_person):
                raise ValidationError(
                    _("Contact Person name must contain letters only (no numbers or special characters).")
                )

    def _relink_required_attachments(self):
        """
        When using many2many_binary, attachments are created before the record exists,
        so they get res_id = 0. Relink them to this order.inq record after create/write.
        """
        for rec in self:
            atts = rec.required_attachment_ids.sudo().filtered(
                lambda a: a.res_model in (False, rec._name) and (not a.res_id or a.res_id == 0)
            )
            if atts:
                atts.write({
                    "res_model": rec._name,
                    "res_id": rec.id,
                })

    @api.constrains('deadline_submission', 'date_order')
    def _check_deadline_date(self):
        for rec in self:
            if rec.deadline_submission and rec.date_order:
                inquiry_date = rec.date_order.date()
                max_deadline = inquiry_date + timedelta(days=30)

                if rec.deadline_submission < inquiry_date:
                    raise ValidationError(
                        _("Deadline of Submission cannot be before the Inquiry Date.")
                    )

                if rec.deadline_submission > max_deadline:
                    raise ValidationError(
                        _("Deadline of Submission cannot exceed 30 days from the Inquiry Date.")
                    )

    @api.depends('sale_order_ids')
    def compute_sale_count(self):
        if self.sale_order_id:
            self.sale_count = len(self.sale_order_ids)
        else:
            self.sale_count = None

    def action_accept(self):
        self.state = 'accept'

    def write(self, vals):
        if "inquiry_type" in vals and vals.get("inquiry_type") == "trading":
            non_trading_records = self.filtered(lambda rec: rec.inquiry_type != "trading")
            if non_trading_records:
                raise UserError(
                    _("Trading inquiry type is temporarily disabled for new selections.")
                )

        res = super().write(vals)

        # if attachments changed, relink them
        if "required_attachment_ids" in vals:
            self._relink_required_attachments()

        return res

    def _has_required_attachments(self, vals):
        commands = vals.get("required_attachment_ids")
        if not commands:
            return False
        if isinstance(commands, (list, tuple)):
            for command in commands:
                if not isinstance(command, (list, tuple)) or not command:
                    continue
                if command[0] == 6 and command[2]:
                    return True
                if command[0] in (0, 1, 4):
                    return True
        return False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("inquiry_type") == "trading":
                raise UserError(
                    _("Trading inquiry type is temporarily disabled for new selections.")
                )
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('order.inq.sequence') or "New"

            if not self._has_required_attachments(vals):
                raise UserError(_("Please attach at least one file."))

        records = super().create(vals_list)

        records._relink_required_attachments()
        return records

    def button_cancel(self):
        if self.state == 'pending':
            self.state = 'cancel'

    def reset_pending(self):
        self.state = 'pending'

    def button_confirm(self, sales_list=None):
        self.state = 'confirm'
        self._notify_inquiry_approvers()

    def view_sale_order(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sale Order',
            'res_model': 'sale.order',
            'domain': [('id', 'in', self.sale_order_ids.ids)],
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def view_estimation(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Estimation",
            "res_model": "petroraq.estimation",
            "domain": [("id", "in", self.estimation_ids.ids)],
            "view_mode": "tree,form",
            "target": "current",
        }

    def action_create_quotation(self):
        self.ensure_one()
        if self.inquiry_type == "construction":
            self._get_or_create_contact_partner()
            if self.estimation_id:
                if self.state != "estimation_created":
                    self.state = "estimation_created"
                return {
                    "type": "ir.actions.act_window",
                    "name": "Estimation",
                    "res_model": "petroraq.estimation",
                    "view_mode": "form",
                    "res_id": self.estimation_id.id,
                }
            estimation = self.env["petroraq.estimation"].create({
                "partner_id": self.partner_id.id,
                "order_inquiry_id": self.id,
                "company_id": self.company_id.id,
            })
            self.estimation_id = estimation.id
            self.state = "estimation_created"
            return {
                "type": "ir.actions.act_window",
                "name": "Estimation Created",
                "res_model": "petroraq.estimation",
                "view_mode": "form",
                "res_id": estimation.id,
            }

        term = self.env.ref("petroraq_sale_workflow.payment_term_trading_advance", raise_if_not_found=False)

        contact = self._get_or_create_contact_partner()

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'order_inquiry_id': self.id,
            'inquiry_type': self.inquiry_type,
            "payment_term_id": term.id if term else False,
            # "partner_invoice_id": contact.id,  # optional but nice
            # "partner_shipping_id": contact.id,
            "user_id": self.user_id.id,
        })

        self.sale_order_id = sale_order.id
        self.sale_order_ids = [(4, sale_order.id)]
        self.state = "quotation_created"

        return {
            'type': 'ir.actions.act_window',
            'name': 'Quotation Created',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': sale_order.id,
        }

    def action_extend_deadline(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'order.inq.extend.deadline.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_inquiry_id': self.id,
            }
        }

    @api.depends("estimation_ids")
    def _compute_estimation_count(self):
        for record in self:
            record.estimation_count = len(record.estimation_ids)

    def action_open_reject_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "order.inq.reject.reason.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_inquiry_id": self.id,
            },
        }


class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    order_inquiry_id = fields.Many2one('order.inq', string='Order Inquiry ID')
    inquiry_type = fields.Selection(related='order_inquiry_id.inquiry_type')
    inquiry_contact_person = fields.Char(related='order_inquiry_id.contact_person', store=True)
    inquiry_contact_person_phone = fields.Char(related='order_inquiry_id.contact_person_phone', store=True)
    inquiry_contact_person_email = fields.Char(related='order_inquiry_id.contact_person_email', store=True)
    inquiry_contact_person_designation = fields.Char(related='order_inquiry_id.designation', store=True)

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            if order.order_inquiry_id:
                order.order_inquiry_id.state = "closed"
        return res

    def _so_renumber_lines_with_gaps(self):
        self.ensure_one()
        seq = 10
        for l in self.order_line.sorted("sequence"):
            l.sequence = seq
            seq += 10

    def _so_next_line_after(self, line):
        self.ensure_one()
        lines = self.order_line.sorted("sequence")
        return lines.filtered(lambda l: l.sequence > line.sequence)[:1]

    def action_add_line_under_section(self, section_line_id, mode="product"):
        """
        mode: 'product' | 'section' | 'note'
        """
        self.ensure_one()

        section = self.env["sale.order.line"].browse(section_line_id).exists()
        if not section or section.order_id.id != self.id:
            raise UserError(_("Invalid section line."))
        if section.display_type != "line_section":
            raise UserError(_("Target is not a section."))

        next_line = self._so_next_line_after(section)

        if next_line and (next_line.sequence - section.sequence) > 1:
            new_seq = section.sequence + 1
        else:
            self._so_renumber_lines_with_gaps()
            new_seq = section.sequence + 10

        vals = {"order_id": self.id, "sequence": new_seq}

        if mode == "section":
            vals.update({"display_type": "line_section", "name": _("New Section")})
        elif mode == "note":
            vals.update({"display_type": "line_note", "name": _("New Note")})
        # else product: keep empty -> user selects product

        line = self.env["sale.order.line"].create(vals)
        return line.id


class RejectReasonWizard(models.TransientModel):
    _name = 'order.inq.reject.reason.wizard'
    _description = 'Reject Reason Wizard'
    inquiry_id = fields.Many2one('order.inq', required=True)
    reason = fields.Text(string="Rejection Reason", required=True)

    def action_confirm_reject(self):
        self.inquiry_id.write({'state': 'reject', 'rejection_reason': self.reason})


class OrderInquiryExtendDeadlineWizard(models.TransientModel):
    _name = 'order.inq.extend.deadline.wizard'
    _description = 'Extend Inquiry Deadline'

    inquiry_id = fields.Many2one('order.inq', required=True, readonly=True)
    current_deadline = fields.Date(string="Current Deadline", readonly=True)
    new_deadline = fields.Date(string="New Deadline", required=True)

    def action_confirm_extend(self):
        self.inquiry_id.write({
            'deadline_submission': self.new_deadline,
            'state': 'confirm',
        })


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    is_locked_section = fields.Boolean(default=False)

    def unlink(self):
        for l in self:
            if l.display_type == "line_section" and l.is_locked_section:
                raise UserError(_("You cannot delete default sections."))
        return super().unlink()

    # def write(self, vals):
    #     for l in self:
    #         if l.display_type == "line_section" and l.is_locked_section:
    #             raise UserError(_("You cannot modify default sections"))
    #     return super().write(vals)
