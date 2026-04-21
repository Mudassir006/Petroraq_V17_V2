from odoo import http
from odoo.http import request, Response


class Icloud(http.Controller):

    @http.route('/iclock/cdata', type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def returned_data_from_device(self, SN, **kw):
        method = request.httprequest.method
        table = kw.get('table', None)
        try:
            data = request.httprequest.data.decode('utf-8')
        except Exception:
            data = request.httprequest.data.decode('gb18030')
        res = request.env['attendance.device'].sudo().process_data_from_device(method, SN, data, table)
        return Response(res)

    @http.route('/iclock/getrequest', type='http', auth='public', methods=['GET'], csrf=False)
    def getrequest(self, SN, **kw):
        res = request.env['attendance.device'].sudo().process_getrequest(SN)
        return Response(res)

    @http.route('/iclock/devicecmd', type='http', auth='public', methods=['POST'], csrf=False)
    def returned_cmd_from_device(self, SN, **kw):
        try:
            data = request.httprequest.data.decode('utf-8')
        except Exception:
            data = request.httprequest.data.decode('gb18030')
        res = request.env['attendance.device'].sudo().process_returned_command_results(SN, data)
        return Response(res)
