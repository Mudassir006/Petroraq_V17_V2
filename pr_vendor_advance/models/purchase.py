from odoo import api, fields, models, _
from odoo.tools import float_is_zero
from itertools import groupby
from odoo.exceptions import UserError
from odoo.fields import Command


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def copy_data(self, default=None):
        if default is None:
            default = {}
        if "order_line" not in default:
            default["order_line"] = [
                (0, 0, line.copy_data()[0])
                for line in self.order_line.filtered(
                    lambda order_line: not order_line.is_downpayment
                )
            ]
        return super().copy_data(default)

    @api.model
    def _nothing_to_invoice_error(self):
        """Function to showing user error while there is no products are received for the purchase order"""
        return UserError(_(
            "There is nothing to bill!\n\n"
            "Reason(s) of this behavior could be:\n"
            "- You should recieve your products before billing them: Click on the \"truck\" icon "
            "(top-right of your screen) and follow instructions.\n"
            "- You should modify the control policy of your product: Open the product, go to the "
            "\"Purchase\" tab and modify control policy from \"On received quantities\" to \"On ordered "
            "quantities\"."
        ))

    def _advance_bill_payment(self, grouped=False, final=False, date=None):
        """
        Create the Bill associated to the PO.
        :returns: list of created invoices
        """
        bill_vals_list = []
        bill_item_sequence = 0  # Incremental sequencing to keep the lines order on the invoice.
        for order in self:
            order = order.with_company(order.company_id)
            bill_vals = order._prepare_invoice()
            billable_lines = order._get_billable_lines(final)
            if not any(not line.display_type for line in billable_lines):
                continue
            bill_line_vals = []
            down_payment_section_added = False
            for line in billable_lines:
                if not down_payment_section_added and line.is_downpayment:
                    bill_line_vals.append(
                        (0, 0, order._prepare_down_payment_section_line(
                            sequence=bill_item_sequence,
                        )),
                    )
                    down_payment_section_added = True
                    bill_item_sequence += 1
                bill_line_vals.append(
                    (0, 0, line.with_context(sequence=bill_item_sequence)._prepare_account_move_line()),
                )
                bill_item_sequence += 1
            bill_vals['invoice_line_ids'] += bill_line_vals
            bill_vals_list.append(bill_vals)
        if not bill_vals_list:
            raise self._nothing_to_invoice_error()
        if not grouped:
            new_bill_vals_list = []
            invoice_grouping_keys = self._get_invoice_grouping_keys()
            bill_vals_list = sorted(
                bill_vals_list,
                key=lambda x: [
                    x.get(grouping_key) for grouping_key in invoice_grouping_keys
                ]
            )
            for grouping_keys, bills in groupby(bill_vals_list,
                                                key=lambda x: [x.get(grouping_key) for grouping_key in
                                                               invoice_grouping_keys]):
                origins = set()
                payment_refs = set()
                refs = set()
                ref_bill_vals = None
                for bill_vals in bills:
                    if not ref_bill_vals:
                        ref_bill_vals = bill_vals
                    else:
                        ref_bill_vals['invoice_line_ids'] += bill_vals['invoice_line_ids']
                    origins.add(bill_vals['invoice_origin'])
                    payment_refs.add(bill_vals['payment_reference'])
                    refs.add(bill_vals['ref'])
                ref_bill_vals.update({
                    'ref': ', '.join(refs)[:2000],
                    'invoice_origin': ', '.join(origins),
                    'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
                })
                new_bill_vals_list.append(ref_bill_vals)
            bill_vals_list = new_bill_vals_list
        if len(bill_vals_list) < len(self):
            PurchaseOrderLine = self.env['purchase.order.line']
            for invoice in bill_vals_list:
                sequence = 1
                for line in invoice['invoice_line_ids']:
                    line[2]['sequence'] = PurchaseOrderLine._get_bill_line_sequence(new=sequence,
                                                                                    old=line[2]['sequence'])
                    sequence += 1
        moves = self.env['account.move'].sudo().with_context(default_move_type='in_invoice').create(bill_vals_list)
        if final:
            moves.sudo().filtered(lambda m: m.amount_total < 0).action_switch_move_type()
        return moves

    @api.model
    def _prepare_down_payment_section_line(self, **optional_values):
        """
        Prepare the dict of values to create a new down payment section for a purchase order line.
        :param optional_values: any parameter that should be added to the returned down payment section
        """
        context = {'lang': self.partner_id.lang}
        down_payments_section_line = {
            'display_type': 'line_section',
            'name': _('Pre Payments'),
            'product_id': False,
            'product_uom_id': False,
            'quantity': 0,
            'discount': 0,
            'price_unit': 0,
            'account_id': False
        }
        del context
        if optional_values:
            down_payments_section_line.update(optional_values)
        return down_payments_section_line

    def _get_invoice_grouping_keys(self):
        """Return invoice grouping keys"""
        return ['company_id', 'partner_id', 'currency_id']

    def _get_billable_lines(self, final=False):
        """Return the invoiceable lines for order `self`."""
        down_payment_line_ids = []
        billable_line_ids = []
        pending_section = None
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        # Keep service receipt based quantities in sync before deciding billable lines.
        # The service_receipt_note module updates `qty_received` for service PO lines
        # when SRN is validated; forcing a refresh here guarantees "Regular bill"
        # behaves the same as delivered-quantity billing.
        self.order_line.filtered(
            lambda line: not line.display_type and line.product_id.detailed_type == 'service'
        )._update_qty_received_from_srn()

        for line in self.order_line:
            # line.display_type = ''
            if line.display_type == 'line_section':
                pending_section = line
                continue
            if line.display_type != 'line_note' and float_is_zero(line.qty_to_invoice, precision_digits=precision):
                continue
            if line.qty_to_invoice > 0 or (line.qty_to_invoice < 0 and final) or line.display_type == 'line_note':
                if line.is_downpayment:
                    down_payment_line_ids.append(line.id)
                    continue
                if pending_section:
                    billable_line_ids.append(pending_section.id)
                    pending_section = None
                billable_line_ids.append(line.id)
        return self.env['purchase.order.line'].browse(billable_line_ids + down_payment_line_ids)

    @api.depends("state", "order_line.qty_to_invoice")
    def _get_invoiced(self):
        """
        Sodexis override to skip the downpayment line
        in the vendor bill status calculation.
        """
        precision = self.env["decimal.precision"].precision_get(
            "Product Unit of Measure"
        )
        for order in self:
            if order.state not in ("purchase", "done"):
                order.invoice_status = "no"
                continue

            if any(
                    not float_is_zero(line.qty_to_invoice, precision_digits=precision)
                    for line in order.order_line.filtered(
                        lambda order_line: not order_line.display_type
                                           and not order_line.is_downpayment
                    )
                    # Sodexis Override: added and not l.is_downpayment here
            ):
                order.invoice_status = "to invoice"
            elif (
                    all(
                        float_is_zero(line.qty_to_invoice, precision_digits=precision)
                        for line in order.order_line.filtered(
                            lambda order_line: not order_line.display_type
                        )
                    )
                    and order.invoice_ids
            ):
                order.invoice_status = "invoiced"
            else:
                order.invoice_status = "no"

    def extra_advance_bill_vals(self):
        """Function to Add the extra advance bill values"""
        # Your logic here to extra advance bill values based on the order
        res = {}
        try:
            res = super().extra_advance_bill_vals()
        except AttributeError:
            pass
        return res


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    is_downpayment = fields.Boolean(
        string="Is a down payment", help="Down payments are made when creating Bills from a purchase order."
                                         " They are not copied when duplicating a purchase order.")

    def _prepare_account_move_line(self, move=False):
        """
        Prepare the dict of values to create the new bill line for a purchase order line.
        :param qty: float quantity to bill
        :param optional_values: any parameter that should be added to the returned bill line
        """
        res = super()._prepare_account_move_line(move)
        sequence = self._context.get('sequence')
        if sequence is not None:
            res.update({
                'sequence': sequence
            })
        if self.display_type:
            res['account_id'] = False

        return res

    def _get_bill_line_sequence(self, new=0, old=0):
        """
        Method intended to be overridden in third-party module if we want to prevent the resequencing
        of bill lines.

        :param int new:   the new line sequence
        :param int old:   the old line sequence

        :return:          the sequence of the PO line, by default the new one.
        """
        return new or old
