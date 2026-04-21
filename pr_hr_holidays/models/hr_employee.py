from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import random
from datetime import datetime, date, timedelta
import calendar
from odoo.tools import date_utils


class HrEmployee(models.Model):
    # region [Initial]
    _inherit = "hr.employee"
    # endregion [Initial]

    # region [Fields]


    # endregion [Fields]

    def check_annual_leave_balance(self):
        employee_ids = self.env["hr.employee"].search([("active", "=", True), ("company_id", "=", self.env.company.id)])
        for employee in employee_ids:
            annual_days = 0
            contract_id = employee.contract_id
            start_date = contract_id.date_start
            end_date = date(2025, 4, 30)
            months_dict = self.split_dates(start_date, end_date)
            for key_date, dict_value in months_dict.items():
                start_of_month = date_utils.start_of(key_date, 'month')
                end_of_month = date_utils.end_of(key_date, 'month')
                month_days = (end_of_month - start_of_month).days + 1
                balance_days = (dict_value.get("to_date") - dict_value.get("from_date")).days + 1
                annual_days += (1.75 * balance_days) / month_days
            if annual_days > 0:
                allocation_id = self.env["hr.leave.allocation"].create({
                    "name": f"Allocation For {employee.name} Until 30-04-2025",
                    "holiday_type": "employee",
                    "employee_id": employee.id,
                    "employee_ids": employee.ids,
                    "holiday_status_id": 1,
                    "allocation_type": "regular",
                    "date_from": contract_id.date_start,
                    "number_of_days": annual_days,
                    "number_of_days_display": annual_days,
                })
                if allocation_id:
                    allocation_id.action_validate()


    # Function to generate the date splits
    def split_dates(self, start_date, end_date):
        # Dictionary to hold the results
        date_dict = {}

        # Start iterating from the start month to the end month
        current_date = start_date

        while current_date <= end_date:
            month = current_date.month
            year = current_date.year

            # Get the first and last days of the current month
            first_day_of_month = datetime(year, month, 1).date()
            last_day_of_month = datetime(year, month, calendar.monthrange(year, month)[1]).date()

            # Ensure both are datetime objects for comparison
            from_date = max(first_day_of_month, current_date)
            to_date = min(last_day_of_month, end_date)

            # Add the data to the dictionary if 'from_date' is before or equal to 'to_date'
            if from_date <= to_date:
                # Key is "YYYY-MM"
                key = f"{year}-{month:02d}"
                # date_dict[key] = {
                #     "from_date": from_date.strftime("%d/%m/%Y"),
                #     "to_date": to_date.strftime("%d/%m/%Y")
                # }

                date_dict[first_day_of_month] = {
                    "from_date": from_date,
                    "to_date": to_date
                }

            # Move to the first day of the next month, adjusting for year transition
            if current_date.month == 12:
                current_date = datetime(current_date.year + 1, 1, 1).date()
            else:
                current_date = datetime(current_date.year, current_date.month + 1, 1).date()

        return date_dict