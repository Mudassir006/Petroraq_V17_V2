from collections import defaultdict
from datetime import datetime, time

import pytz
from dateutil.relativedelta import relativedelta
from odoo import api, models


class HrEmployeeDashboard(models.Model):
    _inherit = 'hr.employee'

    def get_public_holidays(self, start_date, end_date):
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
            'end': datetime.combine(datetime.combine(bh.date_to, time.max).astimezone(employee_tz), datetime.max.time()).isoformat(),
            'endType': "datetime",
            'isAllDay': True,
            'start': datetime.combine(datetime.combine(bh.date_from, time.min).astimezone(employee_tz), datetime.min.time()).isoformat(),
            'startType': "datetime",
            'title': bh.name,
        }, public_holidays))

    def _get_public_holidays(self, start_date, end_date):
        return self.env['hr.public.holiday'].sudo().search([
            ('date_from', '<=', end_date),
            ('date_to', '>=', start_date),
            ('state', '=', 'active'),
        ])
