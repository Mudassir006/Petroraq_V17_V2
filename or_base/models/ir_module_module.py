from odoo import fields, api, models, _
from odoo.exceptions import UserError

from odoo.addons.base.models.ir_module import assert_log_admin_access

MAP_TRANSLATION_KEY = {
    'shortdesc': 'name',
    'summary': 'summary',
    'description': 'description',
}


class IrModuleModule(models.Model):
    _inherit = 'ir.module.module'

    should_installed_but_not_installed = fields.Boolean(string='Should Have Been Installed',
        compute='_compute_should_installed_but_not_installed',
        search='_search_should_installed_but_not_installed',
        help="This indicates whether this module should be installed when it is marked as automatically installed"
        " and its dependencies are installed already but it itself is not installed."
    )

    @api.depends('state', 'dependencies_id.state', 'auto_install', 'dependencies_id.auto_install_required')
    def _compute_should_installed_but_not_installed(self):
        self.should_installed_but_not_installed = False
        for module in self:
            if module.state == 'uninstalled' and module.auto_install and \
                all(depend.state == 'installed' for depend in module.dependencies_id):
                module.should_installed_but_not_installed = True

    def _search_should_installed_but_not_installed(self, operator, value):
        if operator not in ['=', '!='] or not isinstance(value, bool):
            raise UserError(_('Operation is not supported'))
        if operator != '=':
            value = not value
        uninstalled_modules = self.env['ir.module.module'].search([('state', '=', 'uninstalled'), ('name', 'not like', 'test_%')])
        modules = uninstalled_modules.filtered(
            lambda md: md.auto_install
                and (
                    not any(depend.state != 'installed' for depend in md.dependencies_id)
                    or not any(depend.state != 'installed' for depend in md.dependencies_id if depend.auto_install_required)
                )
        )
        return [('id', 'in', modules.ids)]

    @assert_log_admin_access
    @api.model
    def update_list(self):
        res = super(IrModuleModule, self).update_list()
        self.env['ir.module.module'].search([])._update_module_infos_translation()
        return res

    def _update_module_infos_translation(self):
        langs_code = [lang[0] for lang in self.env['res.lang'].get_installed()]
        for r in self:
            terp = r.get_module_info(r.name)
            for key in MAP_TRANSLATION_KEY:
                vals = {}
                for lang_code in langs_code:
                    manifest_key = f'{MAP_TRANSLATION_KEY[key]}_{lang_code}'
                    if terp.get(manifest_key, False) and r.with_context(lang=lang_code)[key] != terp[manifest_key]:
                        vals.update({lang_code: terp[manifest_key]})
                if vals:
                    r.update_field_translations(key, vals)

    def write(self, vals):
        res = super(IrModuleModule, self).write(vals)

        if any(val in MAP_TRANSLATION_KEY.keys() for val in vals):
            self._update_module_infos_translation()
        return res
