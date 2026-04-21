from datetime import datetime
from datetime import date
from odoo.tools.misc import formatLang
from collections import defaultdict
from contextlib import ExitStack, contextmanager



from odoo import models, fields, api, Command
from odoo.exceptions import UserError
import qrcode
import base64
from odoo import models, fields, api, _
from io import BytesIO
import binascii
from googletrans import Translator

try:
    from num2words import num2words
except ImportError:
    _logger.warning("The num2words python library is not installed, amount-to-text features won't be fully available.")
    num2words = None

class generateQrCode():

    # this method will return image of qr with relevent url
    def generate_qr_code(url):
        qr = qrcode.QRCode(
            version=4,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=20,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image()
        temp = BytesIO()
        img.save(temp, format="PNG")
        qr_img = base64.b64encode(temp.getvalue())
        return qr_img


class AccountMove(models.Model):
    _inherit = 'account.move'

    custom_qr_image = fields.Binary("QR Code", compute='_generate_qr_code')

    @api.model
    def translate_to_arabic(self, text, _logger=None):
        if not text:
            return ''

        translator = Translator()
        try:
            translation = translator.translate(text, dest='ar')
            if translation and hasattr(translation, 'text'):
                return translation.text
            return ''
        except Exception as e:
            _logger.error(f"Error in translating text to Arabic: {e}")
            return ''

    @api.model
    def translate_invoice_name(self, invoice_name):
        translated_name = invoice_name.replace('INV', 'فاتورة')
        numerals_map = str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩')
        return translated_name.translate(numerals_map)

    @api.model
    def convert_to_eastern_arabic_numerals(self, input_date):
        if not input_date or not isinstance(input_date, date):
            return ''

        date_string = input_date.strftime('%Y-%m-%d')
        numerals_map = str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩')
        return date_string.translate(numerals_map)

    @api.model
    def convert_phone_to_eastern_arabic_numerals(self, phone_number):
        if isinstance(phone_number, str):
            numerals_map = str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩')
            return phone_number.translate(numerals_map)
        else:
            return ''

    def amount_to_world(self, amount):
        integer_part, _, fractional_part = str(amount).partition('.')
        int_words_arabic = num2words(int(integer_part), lang="ar") + ' ريال سعودي'
        fractional_words_arabic = num2words(int(fractional_part), lang="ar") + ' هللة'
        if fractional_part != '0':
            return f"{int_words_arabic} و{fractional_words_arabic}"
        else:
            return int_words_arabic

    def amount_to_text(self, amount):
        integer_part, _, fractional_part = str(amount).partition('.')
        int_words_english = num2words(int(integer_part)).title() + ' Saudi Riyal'
        fractional_words_english = num2words(int(fractional_part)).title()

        if fractional_words_english == "Five":
            fractional_words_english = "fifty"

        return f"{int_words_english} And {fractional_words_english} Halala"

# ///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

    # conivert string value to hexa value
    def _string_to_hex(self, value):
        if value:
            string = str(value)
            string_bytes = string.encode("UTF-8")
            encoded_hex_value = binascii.hexlify(string_bytes)
            hex_value = encoded_hex_value.decode("UTF-8")
            return hex_value

    # for getting the hexa value
    def _get_hex(self, tag, length, value):
        if tag and length and value:
            hex_string = self._string_to_hex(value)
            length = len(value)
            conversion_table = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c', 'd', 'e', 'f']
            hexadecimal = ''
            while (length > 0):
                remainder = length % 16
                hexadecimal = conversion_table[remainder] + hexadecimal
                length = length // 16
            if len(hexadecimal) == 1:
                hexadecimal = "0" + hexadecimal
            return tag + hexadecimal + hex_string

    # Generate Qr Code In Binary Field
    def _generate_qr_code(self):
        if self.move_type in ('out_invoice', 'out_refund'):
            sellername = str(self.company_id.name)
            seller_vat_no = self.company_id.vat or ''
            if self.partner_id.company_type == 'company':
                customer_name = self.partner_id.name
                customer_vat = self.partner_id.vat
        else:
            sellername = str(self.partner_id.name)
            seller_vat_no = self.partner_id.vat
        seller_hex = self._get_hex("01", "0c", sellername) or ''
        vat_hex = self._get_hex("02", "0f", seller_vat_no) or ''
        time_stamp = str(self.create_date)
        date_hex = self._get_hex("03", "14", time_stamp) or ''
        total_with_vat_hex = self._get_hex("04", "0a", str(round(self.amount_total, 2))) or ''
        # total_with_vat_hex = self._get_hex("04", "0a", str(round(self.tax_totals["amount_total"], 2))) or ''
        # total_with_vat_hex = self._get_hex("04", "0a", str(round(self.tax_totals_amount_total, 2))) or ''
        total_vat_hex = self._get_hex("05", "09", str(round(self.amount_tax, 2))) or ''
        # total_vat_hex = self._get_hex("05", "09", str(round(self.tax_totals_amount_tax, 2))) or ''
        qr_hex = "".join((p for p in (seller_hex, vat_hex, date_hex, total_with_vat_hex, total_vat_hex) if p))
        qr_info = base64.b64encode(bytes.fromhex(qr_hex)).decode()
        self.custom_qr_image = generateQrCode.generate_qr_code(qr_info)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    arabic_name = fields.Char(string='Arabic Name', required=True)
    arabic_street = fields.Char(string='Arabic Street', required=True)
    arabic_street2 = fields.Char(string='Arabic Street', required=True)








