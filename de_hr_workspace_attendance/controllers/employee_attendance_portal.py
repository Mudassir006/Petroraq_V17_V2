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


class EmployeeAttendancePortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'my_attendance_count' in counters:
            values['my_attendance_count'] = request.env['hr.attendance'].search_count([("employee_id.user_id", "=", request.env.user.id)])
        return values

    def _prepare_my_attendance_domain(self):
        return [("employee_id.user_id", "=", request.env.user.id)]

    def _prepare_my_attendance_searchbar_sortings(self):
        return {
            'check_in': {'label': _('Newest'), 'order': 'check_in desc'},
            'check_out': {'label': _('Oldest'), 'order': 'check_in asc'},
        }

    @http.route(['/my/attendances', '/my/attendances/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_attendances(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        Attendance = request.env['hr.attendance'].sudo()
        domain = self._prepare_my_attendance_domain()

        searchbar_sortings = self._prepare_my_attendance_searchbar_sortings()
        if not sortby:
            sortby = 'check_in'
        order = searchbar_sortings[sortby]['order']

        if date_begin and date_end:
            domain += [('check_in', '>', date_begin), ('check_in', '<=', date_end)]

        # projects count
        attendance_count = Attendance.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/attendances",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=attendance_count,
            page=page,
            step=self._items_per_page
        )

        # content according to pager and archive selected
        attendances = Attendance.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_attendances_history'] = attendances.ids[:100]

        values.update({
            'date': date_begin,
            'date_end': date_end,
            'attendances': attendances,
            'page_name': 'attendance',
            'default_url': '/my/attendances',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby
        })
        return request.render("de_hr_workspace_attendance.portal_my_attendances", values)