# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import OrderedDict
from operator import itemgetter
from markupsafe import Markup

from odoo import conf, http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.tools import groupby as groupbyelem

from odoo.osv.expression import OR, AND


class EmployeeShortageRequestsApprovalPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'my_shortage_request_approval_count' in counters:
            values['my_shortage_request_approval_count'] = request.env['pr.hr.shortage.request'].search_count([("employee_manager_id.user_id", "=", request.env.user.id), ("state", "=", "draft")])
        return values

    def _prepare_my_shortage_request_approval_domain(self):
        return [("employee_manager_id.user_id", "=", request.env.user.id), ("state", "=", "draft")]

    def _prepare_my_shortage_request_approval_searchbar_sortings(self):
        return {
            'date': {'label': _('Newest'), 'order': 'date desc'},
            'check_out': {'label': _('Oldest'), 'order': 'date asc'},
        }

    @http.route(['/my/shortage_requests_approval', '/my/shortage_requests_approval/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_shortage_requests_approval(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        ShortageRequestApproval = request.env['pr.hr.shortage.request'].sudo()
        domain = self._prepare_my_shortage_request_approval_domain()

        searchbar_sortings = self._prepare_my_shortage_request_approval_searchbar_sortings()
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        if date_begin and date_end:
            domain += [('date', '>', date_begin), ('date', '<=', date_end)]

        # projects count
        shortage_request_approval_count = ShortageRequestApproval.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/shortage_requests_approval",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=shortage_request_approval_count,
            page=page,
            step=self._items_per_page
        )

        # content according to pager and archive selected
        shortage_requests_approvals = ShortageRequestApproval.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_shortage_requests_approvals_history'] = shortage_requests_approvals.ids[:100]

        values.update({
            'date': date_begin,
            'date_end': date_end,
            'shortage_requests_approvals': shortage_requests_approvals,
            'page_name': 'shortage',
            'default_url': '/my/shortage_requests_approval',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby
        })
        return request.render("de_hr_workspace_attendance.portal_my_shortage_requests_approvals", values)

    @http.route(['/my/shortage_requests_approval/<model("pr.hr.shortage.request"):shortage_request_id>'], type='http', auth="user", website=True)
    def portal_my_shortage_request_approval_info(self, shortage_request_id, **kw):
        shortage_request_obj = request.env["pr.hr.shortage.request"].sudo().browse(int(shortage_request_id))
        values = {"shortage_request_id": shortage_request_obj}
        return request.render("de_hr_workspace_attendance.employee_shortage_request_approval_info_portal", values)

    @http.route(['/my/shortage_requests_approved/<model("pr.hr.shortage.request"):shortage_request_id>'], type='http',
                auth="user", website=True)
    def portal_my_shortage_request_approved(self, shortage_request_id, **kw):
        shortage_request_obj = request.env["pr.hr.shortage.request"].sudo().browse(int(shortage_request_id))
        shortage_request_obj.sudo().action_manager_approve()
        return request.redirect('/my/shortage_requests_approval')

    @http.route(['/my/shortage_requests_rejected/<model("pr.hr.shortage.request"):shortage_request_id>'], type='http',
                auth="user", website=True)
    def portal_my_shortage_request_rejected(self, shortage_request_id, **kw):
        shortage_request_obj = request.env["pr.hr.shortage.request"].sudo().browse(int(shortage_request_id))
        shortage_request_obj.sudo().state = 'reject'
        shortage_request_obj.sudo().approval_state = 'reject'
        return request.redirect('/my/shortage_requests_approval')