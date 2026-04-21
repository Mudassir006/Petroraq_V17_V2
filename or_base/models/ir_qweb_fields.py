import re

from odoo import api, models

from odoo.addons.base.models.ir_qweb_fields import nl2br


class BarcodeConverter(models.AbstractModel):
    _inherit = 'ir.qweb.field.barcode'

    @api.model
    def value_to_html(self, value, options=None):
        """
        Print only barcodes coded in code 128 format when it has non code 128
        hide it from print report
        This implement base on https://github.com/odoo/odoo/pull/168324
        """
        # TODO: remove me in 18/master+ https://github.com/odoo/odoo/pull/168324
        if not value:
            return super().value_to_html(value=value, options=options)
        if not bool(re.match(r'^[\x00-\x7F]+$', value)):
            return nl2br(value)
        return super().value_to_html(value=value, options=options)
