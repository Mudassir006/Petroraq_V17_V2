from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import random
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import calendar
from odoo.tools import date_utils
from collections import defaultdict  # make sure this import exists at top


class HrHolidays(models.Model):
    # region [Initial]
    _inherit = "hr.leave"
    # endregion [Initial]

    # region [Fields]

    is_paid = fields.Boolean(string="Is Paid ?",
                             related="holiday_status_id.is_paid",
                             store=True)
    holiday_status_id = fields.Many2one(
        "hr.leave.type",
        domain="""[
                ('company_id', 'in', [employee_company_id, False]),
                    ('has_valid_allocation', '=', True),
            ]""",
        tracking=True)
    leave_amount = fields.Float(string="Amount", compute="compute_leave_amount", store=True)
    leave_request_id = fields.Many2one("pr.hr.leave.request", string="Leave Request", readonly=True)
    allocation_override_applied = fields.Boolean(
        string="Allocation Override Applied",
        default=False,
        readonly=True,
        help="Checked when this leave was approved using allocation-limit override.",
    )
    allocation_override_note = fields.Text(
        string="Allocation Override Note",
        readonly=True,
    )
    # leave_amount = fields.Float(string="Amount")

    # endregion [Fields]

    # region [Compute Methods]

    # @api.depends('date_from', 'date_to', 'resource_calendar_id', 'holiday_status_id.request_unit', 'request_date_from', 'request_date_to')
    # def _compute_duration(self):
    #     for holiday in self:
    #         days, hours = holiday._get_duration()
    #         holiday.number_of_hours = hours
    #         if holiday.holiday_status_id.request_unit == "day":
    #             holiday.number_of_days = (holiday.request_date_to - holiday.request_date_from).days + 1
    #         else:
    #             holiday.number_of_days = days

    @api.depends("holiday_status_id",
                 "request_date_from",
                 "request_date_to",
                 "holiday_status_id.is_paid",
                 "holiday_status_id.leave_type",
                 "number_of_days",
                 "employee_id",
                 "employee_id.contract_id",
                 "employee_id.contract_id.gross_amount",
                 )
    def compute_leave_amount(self):
        for leave in self:
            if leave.holiday_status_id and leave.holiday_status_id.is_paid:
                employee_net_salary = leave.employee_id.contract_id.gross_amount if (
                            leave.employee_id and leave.employee_id.contract_id) else 0
                if leave.holiday_status_id.leave_type != "sick_leave":
                    leave.leave_amount = leave._calculate_leave_amount()
                elif leave.holiday_status_id.leave_type == "sick_leave":
                    sick_leave_ids = self.search([
                        ("holiday_status_id.leave_type", "=", "sick_leave"),
                        ("employee_id", "=", leave.employee_id.id),
                        ("state", "=", "validate"),
                    ])
                    if sick_leave_ids:
                        sick_leave_days = sum(sick_leave_ids.mapped("number_of_days"))
                    else:
                        sick_leave_days = 0
                    days_dict = leave.split_dates(start_date=leave.request_date_from, end_date=leave.request_date_to)
                    leave.leave_amount = leave._calculate_sick_leave_amount(days_dict=days_dict, sick_leave_days=sick_leave_days, employee_net_salary=employee_net_salary)


    def _calculate_sick_leave_amount(self, days_dict, sick_leave_days, employee_net_salary):
        for leave in self:
            sick_leave_days = sick_leave_days  # Track sick leave days taken
            leave_amount = 0

            for month_key, month_values in days_dict.items():
                start_of_month = date_utils.start_of(month_key, 'month')
                end_of_month = date_utils.end_of(month_key, 'month')
                month_days = (end_of_month - start_of_month).days + 1

                # Calculate leave days for the current month
                leave_days = (month_values.get("to_date") - month_values.get("from_date")).days + 1

                # While there are still sick leave days remaining
                while leave_days > 0:
                    # Handle days from 0 to 30 days at 100% rate
                    if sick_leave_days <= 30:
                        si_30_days = min(30 - sick_leave_days, leave_days)
                        leave_amount += (si_30_days * employee_net_salary) / month_days if employee_net_salary > 0 else 0
                        sick_leave_days += si_30_days
                        leave_days -= si_30_days

                    # Handle days from 31 to 60 days at 75% rate
                    elif 31 <= sick_leave_days <= 60:
                        si_60_days = min(60 - sick_leave_days, leave_days)
                        leave_amount += (((si_60_days * employee_net_salary) / month_days) * 0.75) if employee_net_salary > 0 else 0
                        sick_leave_days += si_60_days
                        leave_days -= si_60_days

                    # Handle days from 61 to 90 days at 50% rate
                    elif 61 <= sick_leave_days <= 90:
                        si_90_days = min(90 - sick_leave_days, leave_days)
                        # leave_amount += (((si_90_days * employee_net_salary) / month_days) * 0.50) if employee_net_salary > 0 else 0
                        leave_amount += (((si_90_days * employee_net_salary) / month_days) * 0) if employee_net_salary > 0 else 0
                        sick_leave_days += si_90_days
                        leave_days -= si_90_days

            return leave_amount

    def _calculate_leave_amount(self):
        for leave in self:
            employee_net_salary = leave.employee_id.contract_id.gross_amount if (
                    leave.employee_id and leave.employee_id.contract_id) else 0
            if leave.holiday_status_id.request_unit == "day":
                days = (leave.request_date_to - leave.request_date_from).days + 1
                days_dict = leave.split_dates(start_date=leave.request_date_from, end_date=leave.request_date_to)
                leave_amount = 0
                for month_key, month_values in days_dict.items():
                    start_of_month = date_utils.start_of(month_key, 'month')
                    end_of_month = date_utils.end_of(month_key, 'month')
                    month_days = (end_of_month - start_of_month).days + 1
                    leave_days = (month_values.get("to_date") - month_values.get("from_date")).days + 1
                    leave_amount += ((leave_days * employee_net_salary) / month_days) if employee_net_salary > 0 else 0
                return leave_amount
            elif leave.holiday_status_id.request_unit == "hour":
                average_hours_per_day = leave.employee_id.resource_calendar_id.hours_per_day if leave.employee_id.resource_calendar_id else 0
                start_of_month = date_utils.start_of(leave.request_date_from, 'month')
                end_of_month = date_utils.end_of(leave.request_date_from, 'month')
                month_days = (end_of_month - start_of_month).days + 1
                day_amount = (1 * employee_net_salary) / month_days
                leave_amount = 0
                if leave.request_unit_half:
                    leave_amount = day_amount / 2
                elif leave.request_unit_hours:
                    hours = leave.number_of_days_display
                    leave_amount = (hours * day_amount) / average_hours_per_day
                return leave_amount
            return 0

    # Function to generate the date splits
    def split_dates(self, start_date, end_date):
        for leave in self:
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


    # endregion [Compute Methods]

    # region [Onchange Methods]

    @api.onchange("employee_id")
    def _onchange_employee_id_set_employee_ids(self):
        self.ensure_one()
        if self.employee_id:
            self.employee_ids = self.employee_id.ids

    def _is_allocation_override_enabled(self):
        return (
                self.env.context.get("pr_leave_allocation_override")
                or self.env.user.has_group('pr_hr_holidays.group_leave_allocation_limit_override')
        )

    @staticmethod
    def _is_allocation_validation_error(error):
        message = (error.args[0] if error.args else "")
        if not isinstance(message, str):
            message = str(message)
        lowered_message = message.lower()

        exact_markers = (
            "there is no valid allocation to cover that request.",
            "you do not have any allocation for this time off type.",
        )
        if any(marker in lowered_message for marker in exact_markers):
            return True
        return False

    # endregion [Onchange Methods]

    @api.constrains('holiday_status_id', 'request_date_from')
    def _check_annual_leave_start_date(self):
        today = fields.Date.context_today(self)
        has_start_date_override = self.env.user.has_group(
            'pr_hr_holidays.group_leave_allocation_limit_override'
        )
        for leave in self:
            if not leave.holiday_status_id or not leave.request_date_from:
                continue
            if has_start_date_override:
                continue
            if leave.holiday_status_id.leave_type == 'annual_leave' and leave.request_date_from <= today:
                raise ValidationError(_("Annual Leave requests must start from tomorrow onward."))

    def _check_holidays(self):
        try:
            return super()._check_holidays()
        except ValidationError as error:
            if not self._is_allocation_override_enabled():
                raise

            if self._is_allocation_validation_error(error):
                return
            raise

    def _check_validity(self):
        if not self._is_allocation_override_enabled():
            return super()._check_validity()

        # Allocation override flow:
        # Keep all standard validations from parent _check_holidays (date/order/overlap/etc.)
        # but bypass allocation-cap checks only.
        sorted_leaves = defaultdict(lambda: self.env['hr.leave'])
        for leave in self:
            sorted_leaves[(leave.holiday_status_id, leave.date_from.date())] |= leave

        for (leave_type, date_from), leaves in sorted_leaves.items():
            if leave_type.requires_allocation == 'no':
                continue

            employees = self.env['hr.employee']
            for leave in leaves:
                employees |= leave._get_employees_from_holiday_type()

            leave_data = leave_type.get_allocation_data(employees, date_from)

            # Community/Enterprise variants:
            # - one variant raises when not leave_data[employee]
            # - another variant skips that raise.
            # For this override group/context, both "missing allocation" and
            # "insufficient remaining allocation" checks are intentionally bypassed.
            if leave_type.allows_negative:
                continue

            previous_leave_data = leave_type.with_context(
                ignored_leave_ids=leaves.ids
            ).get_allocation_data(employees, date_from)

            for employee in employees:
                previous_emp_data = previous_leave_data[employee] and previous_leave_data[employee][0][1].get(
                    'virtual_excess_data')
                emp_data = leave_data[employee] and leave_data[employee][0][1].get('virtual_excess_data')

                if not previous_emp_data and not emp_data:
                    continue

                # Standard behavior would raise "There is no valid allocation..."
                # Skip for the dedicated override group/context only.
                if previous_emp_data != emp_data and len(emp_data or []) >= len(previous_emp_data or []):
                    continue

        return
