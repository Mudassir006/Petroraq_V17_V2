# -*- coding: utf-8 -*-

from odoo import fields, http
from odoo.exceptions import AccessError, AccessDenied
from odoo.http import request
import logging
logger = logging.getLogger(__name__)
import base64
from datetime import date


class TransferAccountingDataApiController(http.Controller):


    @http.route('/api/journal_entry/attachments', methods=["GET"], type='http', auth="none", csrf=False)
    def get_journal_entry_attachments(self):
        data = {}
        start_date = date(2025, 1, 1)
        journal_entry_ids = request.env["account.move"].sudo().search([("move_type", "=", "entry"), ("attachment_ids", "!=", False),
                                                                       "|",("invoice_date", ">=", start_date), ("date", ">=", start_date)])
        if journal_entry_ids:
            for journal_entry in journal_entry_ids:
                attachments_data_list = []
                if journal_entry.attachment_ids:
                    for journal_attachment in journal_entry.attachment_ids:
                        attachments = {
                            'res_name': journal_attachment.res_name,
                            'datas': journal_attachment.datas,
                            'type': 'binary',
                            "mimetype": journal_attachment.mimetype,
                            'name': journal_attachment.name,
                        }
                        attachments_data_list.append(attachments)
                data.update({str(journal_entry.id): attachments_data_list})

        if data:
            return request.make_json_response({
                "message": "Attachments Loaded Successfully",
                "result": data
            }, status=200)
        else:
            return request.make_json_response({
                "Error": f"No Attachments Founded"
            }, status=400)