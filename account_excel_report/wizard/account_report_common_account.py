# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools.misc import get_lang


class AccountCommonAccountReport(models.TransientModel):
    _inherit = "account.common.report"
    _description = 'Account Common Account Report'

    def _print_report_excel(self, data):
        raise NotImplementedError()

    def check_report_excel(self):
        self.ensure_one()
        self.prepare_account_ids()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        # data['form'] = self.read(['date_from', 'date_to', 'journal_ids', 'target_move', 'company_id'])[0]
        data['form'] = self.read(['date_from', 'date_to', 'journal_ids', 'account_ids', 'target_move', 'company_id', 'asset_id', 'project_id', 'division_id', 'department_id'])[0]
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=get_lang(self.env).code)
        return self.with_context(discard_logo_check=True)._print_report_excel(data)
