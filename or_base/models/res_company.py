import base64
import io
from random import randrange
from PIL import Image

from odoo import fields, models, api, tools
from odoo.tools.misc import file_path

from ..__init__ import viin_brand_manifest, _get_branding_module


class Company(models.Model):
    _inherit = 'res.company'

    def _get_default_favicon(self, original=False):
        # use viindoo's favicon if it exists in branding_module/static/img/favicon.ico
        if viin_brand_manifest.get('installable', False):
            viindoo_favicon_path = file_path(f'{_get_branding_module()}/static/img/favicon.ico')
            if viindoo_favicon_path:
                with tools.file_open(viindoo_favicon_path, 'rb') as f:
                    return base64.b64encode(f.read())
        else:
            img_path = file_path('web/static/img/favicon.ico')
            with tools.file_open(img_path, 'rb') as f:
                if original:
                    return base64.b64encode(f.read())
                # Modify the source image to add a colored bar on the bottom
                # This could seem overkill to modify the pixels 1 by 1, but
                # Pillow doesn't provide an easy way to do it, and this
                # is acceptable for a 16x16 image.
                color = (randrange(32, 224, 24), randrange(32, 224, 24), randrange(32, 224, 24))
                original = Image.open(f)
                new_image = Image.new('RGBA', original.size)
                height = original.size[1]
                width = original.size[0]
                bar_size = 1
                for y in range(height):
                    for x in range(width):
                        pixel = original.getpixel((x, y))
                        if height - bar_size <= y + 1 <= height:
                            new_image.putpixel((x, y), (color[0], color[1], color[2], 255))
                        else:
                            new_image.putpixel((x, y), (pixel[0], pixel[1], pixel[2], pixel[3]))
                stream = io.BytesIO()
                new_image.save(stream, format="ICO")
                return base64.b64encode(stream.getvalue())

    font = fields.Selection(selection_add=[('Times New Roman', 'Times New Roman')])
    favicon = fields.Binary(string="Company Favicon", help="This field holds the image used to display a favicon for a given company.", default=_get_default_favicon)

    @api.model_create_multi
    def create(self, vals_list):
        # add default favicon
        for vals in vals_list:
            if not vals.get('favicon'):
                vals['favicon'] = self._get_default_favicon()
        return super(Company, self).create(vals_list)
