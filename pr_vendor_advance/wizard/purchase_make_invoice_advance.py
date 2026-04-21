
import time
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.fields import Command


class PurchaseOrderAdvancePayment(models.TransientModel):
    """The class is created to creating a new model purchase order advance payment. """
    _name = 'purchase.advance.payment.inv'
    _description = 'Purchase Order Advance Payment Bill'

    @api.model
    def _default_product_id(self):
        """Function to fetch the purchase down payment default product"""
        product_id = self.env['ir.config_parameter'].sudo().get_param(
            'pr_vendor_advance.po_deposit_default_product_id')
        return self.env['product.product'].browse(int(product_id)).exists()

    @api.model
    def _default_currency_id(self):
        """Function to fetch the currency_id from purchase order"""
        if self._context.get(
                'active_model') == 'purchase.order' and self._context.get(
            'active_id', False):
            purchase_order = self.env['purchase.order'].browse(
                self._context.get('active_id'))
            return purchase_order.currency_id

    @api.model
    def _default_has_down_payment(self):
        """Function to check the Purchase order has down payment or not"""
        if self._context.get(
                'active_model') == 'purchase.order' and self._context.get(
            'active_id', False):
            purchase_order = self.env['purchase.order'].browse(
                self._context.get('active_id'))
            return purchase_order.order_line.filtered(
                lambda purchase_order_line: purchase_order_line.is_downpayment
            )
        return False

    advance_payment_method = fields.Selection([
        ('delivered', 'Regular bill'),
        ('percentage', 'Down payment (percentage)'),
        ('fixed', 'Down payment (fixed amount)')
    ], string='Create Bill', default='delivered', required=True,
        help="A standard bill is issued with all the order lines ready for billing, \
        according to their billing policy (based on ordered or delivered quantity).")
    has_down_payments = fields.Boolean('Has down payments',
                                       default=_default_has_down_payment,
                                       readonly=True, help='To check the invoice in down payment or not')
    product_id = fields.Many2one('product.product',
                                 string='Down Payment Product',
                                 domain=[('type', '=', 'service')],
                                 default=_default_product_id, help='To add the down payment product')
    deduct_down_payments = fields.Boolean('Deduct down payments', default=True,
                                          help='To mention the down payment amount deduct to next invoice')
    amount = fields.Float('Down Payment Amount', digits='Account',
                          help="The percentage of amount to be bill in advance, taxes excluded.")
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=_default_currency_id, help='Default company currency')
    fixed_amount = fields.Monetary('Down Payment Amount (Fixed)',
                                   help="The fixed amount to be bill in advance, taxes excluded.")
    deposit_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Income Account",
        domain=[('deprecated', '=', False)],
        help="Account used for deposits")

    deposit_taxes_ids = fields.Many2many(
        comodel_name='account.tax',
        string="Customer Taxes",
        domain=[('type_tax_use', '=', 'purchase')],
        help="Taxes used for deposits")

    def _get_advance_amount_details(self, order):
        """Function to find get the down payment amount and purchase order"""
        context = {'lang': order.partner_id.lang}
        if self.advance_payment_method == 'percentage':
            if all(self.product_id.taxes_id.mapped('price_include')):
                amount = order.amount_total * self.amount / 100
            else:
                amount = order.amount_untaxed * self.amount / 100
            name = _("Pre payment of %s%%") % (self.amount)
        else:
            amount = self.fixed_amount
            name = _('Pre Payment')
        del context

        return amount, name

    def _prepare_po_line(self, order, tax_ids, amount):
        """Function to getting the purchase order line data"""
        context = {'lang': order.partner_id.lang}

        analytic_distributions = order.order_line.filtered(
                lambda order_line: not order_line.display_type
                and order_line.analytic_distribution
            ).mapped("analytic_distribution")

        po_values = {
            'name': _('Advance: %s / %s') % (time.strftime('%m-%Y-%d'), order.name),
            'price_unit': amount,
            'product_uom_qty': 0.0,
            'product_qty': 0.0,
            'order_id': order.id,
            'product_uom': self.product_id.uom_id.id,
            'product_id': self.product_id.id,
            'is_downpayment': True,
            'sequence': order.order_line and order.order_line[
                -1].sequence + 1 or 10,
            'date_planned': datetime.today(),
            "analytic_distribution": {
                    k: v for d in analytic_distributions for k, v in d.items()
                }
        }
        del context
        return po_values

    def _prepare_bill_values(self, order, name, amount, po_line):
        """Function for take invoice values"""
        invoice_vals = {
            'ref': order.partner_ref or '',
            'move_type': 'in_invoice',
            'invoice_origin': order.name,
            'invoice_user_id': order.user_id.id,
            'narration': order.notes,
            'partner_id': order.partner_id.id,
            'fiscal_position_id': (
                    order.fiscal_position_id or order.fiscal_position_id._get_fiscal_position(
                order.partner_id)).id,
            'currency_id': order.currency_id.id,
            'payment_reference': order.partner_ref or '',
            'invoice_payment_term_id': order.payment_term_id.id,
            'partner_bank_id': order.company_id.partner_id.bank_ids[:1].id,
            'prepayment_bill': True,
            'invoice_line_ids': [(0, 0, {
                'name': name,
                'price_unit': amount,
                'quantity': 1.0,
                'product_id': self.product_id.id,
                'purchase_line_id': po_line.id,
                'product_uom_id': po_line.product_uom.id,
                'tax_ids': [Command.set(po_line.taxes_id.ids)],
                "analytic_distribution": po_line.analytic_distribution,
            })],
        }

        # Update invoice_vals with advance bill values if they exist
        advance_bill_vals = order.extra_advance_bill_vals()
        if advance_bill_vals:
            invoice_vals.update(advance_bill_vals)

        return invoice_vals

    def _create_bill(self, order, po_line, amount):
        """Function for creating the purchase bill"""
        if (
                self.advance_payment_method == 'percentage' and self.amount <= 0.00) or (
                self.advance_payment_method == 'fixed' and self.fixed_amount <= 0.00):
            raise UserError(
                _('The value of the down payment amount must be positive.'))

        amount, name = self._get_advance_amount_details(order)

        invoice_vals = self._prepare_bill_values(order, name, amount,
                                                    po_line)

        if order.fiscal_position_id:
            invoice_vals['fiscal_position_id'] = order.fiscal_position_id.id

        invoice = self.env['account.move'].with_company(order.company_id) \
            .sudo().create(invoice_vals).with_user(self.env.uid)

        invoice.message_post_with_source('mail.message_origin_link',
                                       render_values={'self': invoice,
                                               'origin': order},
                                       subtype_xmlid="mail.mt_note",)
        return invoice

    def _prepare_down_payment_product_values(self):
        return {
            'name': _('Pre payment'),
            'type': 'service',
            'purchase_method': 'purchase',
            'company_id': False,
            'property_account_income_id': self.deposit_account_id.id,
            'supplier_taxes_id': [Command.clear()],
            'taxes_id': [Command.set(self.deposit_taxes_ids.ids)],
        }

    def create_advance_bill(self):
        """Function for creating purchase down payment bill"""
        purchase_order = self.env['purchase.order'].browse(
            self._context.get('active_ids', []))

        if self.advance_payment_method == 'delivered':
            # if self.deduct_down_payments:
            purchase_order._advance_bill_payment(final=self.deduct_down_payments)
            # else:
            #     purchase_order.action_create_invoice()
        else:
            if not self.product_id:
                vals = self._prepare_down_payment_product_values()
                self.product_id = self.env['product.product'].create(vals)
                self.env['ir.config_parameter'].sudo().set_param(
                    'pr_vendor_advance.po_deposit_default_product_id',
                    self.product_id.id)

            purchase_line_obj = self.env['purchase.order.line']
            for order in purchase_order:
                if not any(
                    line.display_type and line.is_downpayment
                    for line in order.order_line
                ):
                    purchase_line_obj.create(
                        self._prepare_down_payment_section_values(order)
                    )
                amount, name = self._get_advance_amount_details(order)
                if self.product_id.purchase_method != 'purchase':
                    raise UserError(
                        _('The product used to invoice a down payment should have an invoice policy set to "Ordered quantities". Please update your deposit product to be able to create a deposit invoice.'))
                if self.product_id.type != 'service':
                    raise UserError(
                        _("The product used to invoice a down payment should be of type 'Service'. Please use another product or update this product."))
                taxes = self.product_id.taxes_id.filtered(
                    lambda
                        r: not order.company_id or r.company_id == order.company_id)
                tax_ids = order.fiscal_position_id.map_tax(taxes).ids

                po_line_values = self._prepare_po_line(order,
                                                       tax_ids, amount)
                po_line = purchase_line_obj.create(po_line_values)
                self._create_bill(order, po_line, amount)
                if self._context.get('open_invoices', False):
                    return purchase_order.action_view_invoice()
            return {'type': 'ir.actions.act_window_close'}

        if self._context.get('open_invoices', False):
            return purchase_order.action_view_invoice()
        return {'type': 'ir.actions.act_window_close'}

    def _prepare_down_payment_section_values(self, order):
        context = {"lang": order.partner_id.lang}

        po_values = {
            "name": _("Pre Payments"),
            "product_uom_qty": 0.0,
            "product_qty": 0.0,
            "order_id": order.id,
            "display_type": "line_section",
            "is_downpayment": True,
            "sequence": order.order_line and order.order_line[-1].sequence + 1 or 10,
        }

        del context
        return po_values
