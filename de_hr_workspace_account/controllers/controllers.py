# -*- coding: utf-8 -*-
# from odoo import http


# class DeHrWorkspaceTimeoff(http.Controller):
#     @http.route('/de_hr_workspace_timeoff/de_hr_workspace_timeoff', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/de_hr_workspace_timeoff/de_hr_workspace_timeoff/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('de_hr_workspace_timeoff.listing', {
#             'root': '/de_hr_workspace_timeoff/de_hr_workspace_timeoff',
#             'objects': http.request.env['de_hr_workspace_timeoff.de_hr_workspace_timeoff'].search([]),
#         })

#     @http.route('/de_hr_workspace_timeoff/de_hr_workspace_timeoff/objects/<model("de_hr_workspace_timeoff.de_hr_workspace_timeoff"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('de_hr_workspace_timeoff.object', {
#             'object': obj
#         })
