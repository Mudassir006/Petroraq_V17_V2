# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Jumana Haseen (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
from odoo import models, api
from datetime import datetime, time
from collections import defaultdict
from dateutil.relativedelta import relativedelta
import pytz


class HrEmployee(models.Model):
    """Inherit the model hr.employee to add the functionality for retrieving
    public holiday information"""
    _inherit = 'hr.employee'

    def get_public_holidays(self, start_date, end_date):
        """The function get_public_holidays takes in a start date and end
        date as arguments and returns a dictionary with all the public
        holidays within that range. It does this by calling the
        _get_public_holidays method and then iterating through the results to
        add each holiday to the dictionary."""
        all_days = {}
        user = self or self.env.user.employee_id
        public_holidays = user._get_public_holidays(start_date, end_date)
        for holiday in public_holidays:
            num_days = (holiday.date_to - holiday.date_from).days
            for day in range(num_days + 1):
                all_days[str(holiday.date_from)] = day
        return all_days

    @api.model
    def get_public_holidays_data(self, date_start, date_end):
        self = self._get_contextual_employee()
        employee_tz = pytz.timezone(self._get_tz() if self else self.env.user.tz or 'utc')
        public_holidays = self._get_public_holidays(date_start, date_end).sorted('date_from')
        return list(map(lambda bh: {
            'id': -bh.id,
            'colorIndex': 0,
            # 'end': datetime.combine(bh.date_to.astimezone(employee_tz), datetime.max.time()).isoformat(),
            'end': datetime.combine(datetime.combine(bh.date_to, time.max).astimezone(employee_tz), datetime.max.time()).isoformat(),
            'endType': "datetime",
            'isAllDay': True,
            # 'start': datetime.combine(bh.date_from.astimezone(employee_tz), datetime.min.time()).isoformat(),
            'start': datetime.combine(datetime.combine(bh.date_from, time.min).astimezone(employee_tz), datetime.min.time()).isoformat(),
            'startType': "datetime",
            'title': bh.name,
        }, public_holidays))

    def _get_public_holidays(self, start_date, end_date):
        """The _get_public_holidays function searches for public holidays
        within a given date range, for all companies associated with the
        current environment's user. It returns a recordset of
        resource.calendar.leaves that match the search criteria."""
        # public_holidays = self.env['resource.calendar.leaves'].search([
        public_holidays = self.env['hr.public.holiday'].sudo().search([
            ('date_from', '<=', end_date),
            ('date_to', '>=', start_date),
            ('state', '=', 'active'),
        ])
        return public_holidays
