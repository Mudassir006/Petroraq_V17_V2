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


class EmployeeShortageRequestsPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'my_shortage_request_count' in counters:
            shortage_request_c = request.env['pr.hr.shortage.request'].search_count([("employee_id.user_id", "=", request.env.user.id)])
            if shortage_request_c == 0:
                shortage_request_count = 1
            else:
                shortage_request_count = shortage_request_c
            values['my_shortage_request_count'] = shortage_request_count
        return values

    def _prepare_my_shortage_request_domain(self):
        return [("employee_id.user_id", "=", request.env.user.id)]

    def _prepare_my_shortage_request_searchbar_sortings(self):
        return {
            'date': {'label': _('Newest'), 'order': 'date desc'},
            'check_out': {'label': _('Oldest'), 'order': 'date asc'},
        }

    @http.route(['/my/shortage_requests', '/my/shortage_requests/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_shortage_requests(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        ShortageRequest = request.env['pr.hr.shortage.request'].sudo()
        domain = self._prepare_my_shortage_request_domain()

        searchbar_sortings = self._prepare_my_shortage_request_searchbar_sortings()
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        if date_begin and date_end:
            domain += [('date', '>', date_begin), ('date', '<=', date_end)]

        # projects count
        shortage_request_count = ShortageRequest.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/shortage_requests",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=shortage_request_count,
            page=page,
            step=self._items_per_page
        )

        # content according to pager and archive selected
        shortage_requests = ShortageRequest.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_shortage_requests_history'] = shortage_requests.ids[:100]

        values.update({
            'date': date_begin,
            'date_end': date_end,
            'shortage_requests': shortage_requests,
            'page_name': 'shortage',
            'default_url': '/my/shortage_requests',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby
        })
        return request.render("de_hr_workspace_attendance.portal_my_shortage_requests", values)