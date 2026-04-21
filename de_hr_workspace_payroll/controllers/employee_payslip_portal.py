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


class EmployeePayslipPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'my_payslip_count' in counters:
            my_payslip_c = request.env['hr.payslip'].search_count([("employee_id.user_id", "=", request.env.user.id)])
            if my_payslip_c == 0:
                my_payslip_count = 1
            else:
                my_payslip_count = my_payslip_c
            values['my_payslip_count'] = my_payslip_count
        return values

    def _prepare_my_payslip_domain(self):
        return [("employee_id.user_id", "=", request.env.user.id)]

    def _prepare_my_payslip_searchbar_sortings(self):
        return {
            'date_from': {'label': _('Newest'), 'order': 'date_from desc'},
            'date_to': {'label': _('Oldest'), 'order': 'date_from asc'},
        }

    @http.route(['/my/payslips', '/my/payslips/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_payslips(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        Payslip = request.env['hr.payslip'].sudo()
        domain = self._prepare_my_payslip_domain()

        searchbar_sortings = self._prepare_my_payslip_searchbar_sortings()
        if not sortby:
            sortby = 'date_from'
        order = searchbar_sortings[sortby]['order']

        if date_begin and date_end:
            domain += [('date_from', '>', date_begin), ('date_from', '<=', date_end)]

        # projects count
        payslip_count = Payslip.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/payslips",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=payslip_count,
            page=page,
            step=self._items_per_page
        )

        # content according to pager and archive selected
        payslips = Payslip.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_payslips_history'] = payslips.ids[:100]

        values.update({
            'date': date_begin,
            'date_end': date_end,
            'payslips': payslips,
            'page_name': 'payslip',
            'default_url': '/my/payslips',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby
        })
        return request.render("de_hr_workspace_payroll.portal_my_payslips", values)

    @http.route(['/my/payslips/<model("hr.payslip"):payslip_id>'], type='http', auth="user", website=True)
    def portal_my_payslips_payslip_info(self, payslip_id, **kw):
        values = {"payslip_id": payslip_id}
        return request.render("de_hr_workspace_payroll.employee_payslip_info_portal", values)
