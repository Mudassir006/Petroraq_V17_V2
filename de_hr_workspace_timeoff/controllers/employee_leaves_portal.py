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


class EmployeeLeavePortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'my_leave_count' in counters:
            leave_c = request.env['hr.leave'].search_count([("employee_id.user_id", "=", request.env.user.id)])
            if leave_c == 0:
                leave_count = 1
            else:
                leave_count = leave_c
            values['my_leave_count'] = leave_count
        return values

    def _prepare_my_leaves_domain(self):
        return [("employee_id.user_id", "=", request.env.user.id)]

    def _prepare_my_leaves_searchbar_sortings(self):
        return {
            'request_date_from': {'label': _('Newest'), 'order': 'request_date_from desc'},
            'request_date_to': {'label': _('Oldest'), 'order': 'request_date_from asc'},
        }

    @http.route(['/my/leaves', '/my/leaves/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_leaves(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        Leave = request.env['hr.leave'].sudo()
        domain = self._prepare_my_leaves_domain()

        searchbar_sortings = self._prepare_my_leaves_searchbar_sortings()
        if not sortby:
            sortby = 'request_date_from'
        order = searchbar_sortings[sortby]['order']

        if date_begin and date_end:
            domain += [('request_date_from', '>', date_begin), ('request_date_from', '<=', date_end)]

        # projects count
        leave_count = Leave.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/leaves",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=leave_count,
            page=page,
            step=self._items_per_page
        )

        # content according to pager and archive selected
        leaves = Leave.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_leaves_history'] = leaves.ids[:100]

        values.update({
            'date': date_begin,
            'date_end': date_end,
            'leaves': leaves,
            'page_name': 'leave',
            'default_url': '/my/leaves',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby
        })
        return request.render("de_hr_workspace_timeoff.portal_my_leaves", values)