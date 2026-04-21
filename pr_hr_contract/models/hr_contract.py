from odoo import models, fields, api, _
from odoo.tools import date_utils
from odoo.osv import expression
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
import re
import json
import math
from random import randint
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class HrContract(models.Model):
    """
    """
    # region [Initial]
    _inherit = 'hr.contract'
    # endregion [Initial]

    # region [Fields]
    is_special_gosi = fields.Boolean(
        string="Special GOSI (12.75%)",
        help="Enable special company GOSI rate for this employee"
    )

    special_company_gosi_rate = fields.Float(
        string="Special Company GOSI %",
        default=12.75
    )

    joining_date = fields.Date(string="Joining Date", required=True,
                               tracking=True)

    # region [Total Amounts]
    gosi_amount = fields.Float('GOSI Amount', compute='_compute_amount', store=True, tracking=True,
                               help='Amount Deducted from Saudi Employees based on GOSI Configuration')
    gross_amount = fields.Float('Gross Amount', compute='_compute_amount', store=True, tracking=True,
                                help='Amount Deducted from Saudi Employees based on GOSI Configuration')
    net_amount = fields.Float('Net Amount', compute='_compute_amount', store=True, tracking=True,
                              help="Sum of Wage + all amounts of salary rules - GOSI\n"
                                   "NET means total package of the employee, whatever it is paid or company paid")
    # endregion [Total Amounts]

    # region [GOSI Fields]
    is_automatic_gosi = fields.Boolean(string='GOSI Automatic', default=True, tracking=True,
                                       help='If True: GOSI Salary Will be Calculated Automatic'
                                            'If False: GOSI Salary Will Be Manually Added')
    gosi_salary = fields.Float('GOSI Salary', tracking=True,
                               help="Employee Salary as recorded in GOSI, it may different from actual salary, "
                                    "it may added manually")
    company_portion = fields.Float('Company Portion', compute='_compute_amount', store=True, tracking=True,
                                   help='Amount paid to GOSI by company based on GOSI Configuration')
    employee_portion = fields.Float('Employee Portion', compute='_compute_amount', store=True, tracking=True,
                                    help='Amount paid to GOSI by Saudi Employee based on GOSI Configuration')
    # endregion [GOSI Fields]

    # region [Contract Data]
    contract_employment_type = fields.Selection([('employment', 'Employment'),
                                                 ('recruitment', 'Recruitment'),
                                                 ('transfer', 'Transfer')],
                                                string='Employment Type',
                                                help='The Type Of Contract Employment\n'
                                                     'Employment: Employee Join Company Directly\n'
                                                     'Recruitment: Employee Join Company through a recruitment process\n'
                                                     'Transfer: Employee Join Company by transferring his kafala')
    contract_period = fields.Integer(string='Period', tracking=True, default=0.0,
                                     help='Contract Period For This Employee In Months')

    # Trial Period Dates
    trial_period = fields.Integer(string='Trial Period', tracking=True, default=3,
                                  help='Trial Period For This Employee Contract In Months')
    trial_end_date = fields.Date(string='Trial End Date', compute="_compute_trial_end_date", store=True,
                                 tracking=True, help='Trial End Date For This Employee Contract')

    # Notice Periods
    notice_period = fields.Integer(string='Notice Period', tracking=True, default=2, required=True,
                                   help='Notice Period For This Employee Contract In Months')
    notice_end_date = fields.Date(string='Notice Period End Date',
                                  compute="_compute_notice_end_date", store=True, tracking=True,
                                  help='Notice Period End Date For This Employee Contract')

    # Contract End Dates
    expected_end_date = fields.Date(string='Expected End Date',
                                    compute="_compute_expected_end_date", tracking=True, store=True,
                                    help='Expected End Date For This Employee Contract')

    # endregion [Contract Data]

    # region [Count Fields]
    # endregion [Count Fields]

    # region [One 2 many Fields]
    contract_salary_rule_ids = fields.One2many('hr.contract.salary.rule', 'contract_id', 'Salary Rule', tracking=True)

    # endregion [One2many Fields]

    # endregion [Fields]

    # region [Methods]
    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        self.ensure_one()
        if self.employee_id:
            if self.employee_id.job_id:
                self.job_id = self.employee_id.job_id.id
            if self.employee_id.department_id:
                self.department_id = self.employee_id.department_id.id
        else:
            self.job_id = self.department_id = False

    @api.depends('employee_id', 'wage', 'contract_salary_rule_ids', 'contract_salary_rule_ids.pay_in_payslip',
                 'gosi_salary')
    def _compute_amount(self):
        """
        This Method Calculates Contract Total Amounts
        1- Gosi Amount: Deducted Amount of GOSI from Employee (Saudi Employee) and Company paid portion (All Employees)
            Based on GOSI Salary and GOSI Configuration
        2- All Advantages given to employee (company provided or money provided) based on contract salary rules
        3- Paid Amount: Only money provided given to employee (based on contract salary rules)
                        = Wage + pay in payslip amounts - GOSI
        4- Net Amount: Employee package (Wage + all amounts - GOSI)
        :return:
        """
        for rec in self:
            # region [Compute GOSI Amount]
            # Fetch the GOSI configuration once, instead of repeatedly for each record
            gosi_configuration_id = self.env['hr.contract.gosi'].search([], order='id', limit=1)

            # Initialize gosi_amount to 0 by default
            rec.gosi_amount = 0

            if gosi_configuration_id:
                # Determine if the employee is a citizen or a resident
                is_homeland = rec.employee_id.country_id.is_homeland if rec.employee_id.country_id else False

                if is_homeland:
                    emp_gosi = gosi_configuration_id.citizen_employee_portion
                else:
                    emp_gosi = gosi_configuration_id.resident_employee_portion

                # Calculate GOSI amount if both gosi_salary and emp_gosi are defined
                if rec.gosi_salary and emp_gosi:
                    rec.gosi_amount = (-1 * rec.gosi_salary) * (emp_gosi / 100)
            # endregion [Compute GOSI Amount]

            # region [Compute Other Amounts]
            gross_amount = 0
            if rec.contract_salary_rule_ids:
                for rule in rec.contract_salary_rule_ids:
                    if rule.pay_in_payslip:
                        gross_amount += rule.amount

            # Assign the calculated values to the corresponding fields
            rec.gross_amount = rec.wage + gross_amount
            rec.net_amount = rec.wage + gross_amount + rec.gosi_amount
            # endregion [Compute Other Amounts]

    @api.onchange('is_automatic_gosi', 'contract_salary_rule_ids', 'contract_salary_rule_ids.salary_rule_id')
    @api.constrains('is_automatic_gosi', 'contract_salary_rule_ids', 'contract_salary_rule_ids.salary_rule_id')
    def _check_gosi_salary(self):
        """
        Method applied to calculate GOSI Salary, it cals another method (set_gosi_salary)
        :return:
        """
        for contract in self:
            contract._set_gosi_salary()

    def _set_gosi_salary(self):
        """
        Calculates GOSI Salary and portions.
        Supports special company GOSI rate for specific employees (e.g. 12.75%).
        """
        for contract in self:
            gosi_salary = 0.0

            if not contract.is_automatic_gosi:
                contract.gosi_salary = 0.0
                contract.company_portion = 0.0
                contract.employee_portion = 0.0
                continue

            # Fetch GOSI configuration (single active record)
            gosi_configuration = self.env['hr.contract.gosi'].search([], limit=1)
            if not gosi_configuration:
                continue

            # --- Compute GOSI Salary (Base) ---
            contract_salary_rule_ids = contract.contract_salary_rule_ids.mapped("salary_rule_id")
            basic_salary_rule_id = self.env.ref("hr_payroll.default_basic_salary_rule")

            if contract_salary_rule_ids:
                gosi_salary_rule_ids = contract_salary_rule_ids + basic_salary_rule_id
            else:
                gosi_salary_rule_ids = basic_salary_rule_id

            if gosi_salary_rule_ids:
                gosi_salary = contract._compute_amount_of_salary_rules(gosi_salary_rule_ids)

            # --- Determine Rates ---
            is_citizen = contract.employee_id.country_id.is_homeland if contract.employee_id.country_id else False

            if is_citizen:
                employee_rate = gosi_configuration.citizen_employee_portion

                # ⭐ SPECIAL CASE HANDLING (Shahd)
                if contract.is_special_gosi:
                    company_rate = contract.special_company_gosi_rate
                else:
                    company_rate = gosi_configuration.citizen_company_portion

            else:
                employee_rate = gosi_configuration.resident_employee_portion
                company_rate = gosi_configuration.resident_company_portion

            # --- Apply Calculations ---
            contract.gosi_salary = gosi_salary
            contract.employee_portion = gosi_salary * employee_rate / 100
            contract.company_portion = gosi_salary * company_rate / 100

            # Recompute totals
            contract._compute_amount()

    def _compute_amount_of_salary_rules(self, salary_rule_ids):
        """
        This method calculates the total amount based on the provided salary rules
        and contract-specific salary rules.

        Args:
            salary_rule_ids (list): List of salary rule records to be processed.

        Returns:
            float: The total amount calculated for the specified salary rules.
        """
        for contract in self:
            salary_rule_amount = 0
            for salary_rule in salary_rule_ids:
                # If the rule is 'BASIC', use the wage as the base salary
                if salary_rule.code == 'BASIC':
                    salary_rule_amount += contract.wage
                else:
                    # if salary_rule.code not in ["TRANSPORTATION", "FOOD"]:
                    if salary_rule.code == "ACCOMMODATION":
                        # Filter the contract-specific salary rules that match the current salary rule
                        matched_salary_rules = contract.contract_salary_rule_ids.filtered(
                            lambda r: r.salary_rule_id == salary_rule
                        ) if contract.contract_salary_rule_ids else []

                        # Sum the monthly amounts of the matched salary rules
                        if matched_salary_rules:
                            salary_rule_amount += sum(rule.amount for rule in matched_salary_rules)

            return salary_rule_amount

    # endregion [Methods]

    # region [Dates Methods]
    @api.depends('date_start', 'trial_period')
    def _compute_trial_end_date(self):
        """
        Compute the trial end date based on the start date, trial period, and any extended trial period.
        This updates the trial_end_date field accordingly.
        """
        for contract in self:
            # Ensure both trial period and start date are available
            if contract.trial_period and contract.date_start:
                # Calculate a trial period in days
                total_trial_days = contract.trial_period * 30

                # Compute the trial end date by adding the total days to the start date
                contract.trial_end_date = contract.date_start + relativedelta(days=total_trial_days)
            else:
                # If Not set → Set as False
                contract.trial_end_date = False

    @api.depends("date_start", "contract_period")
    def _compute_expected_end_date(self):
        """
        This Code should be inherited somewhere else (For Document type)
        :return:
        """
        for contract in self:
            # Initialize expected_end_date as False
            expected_end_date = False

            # Determine the relevant start date: Max of date_start and renewal_date
            start_date = contract.date_start
            # Calculate expected_end_date only if start_date and contract_period are valid
            if start_date and contract.contract_period:
                # Compute the expected end date by adding the contract period to the start date
                expected_end_date = start_date + relativedelta(months=int(contract.contract_period))

            # Assign the computed expected_end_date to the contract record
            contract.expected_end_date = expected_end_date

        return True

    @api.depends('notice_period', 'expected_end_date')
    def _compute_notice_end_date(self):
        """
        ** This Method computes notice_end_date
        *** in case of limited contracts, we need to set notice end date
        *** we run cron method to send notifications to managers to evaluate employees and decide if they will renew their contract or not
        *** depending on this we will take our decision
        :return: notice_end_date
        """
        notice_end_date = False
        for contract in self:
            if contract.notice_period and contract.expected_end_date:
                notice_end_date = contract.expected_end_date - relativedelta(months=contract.notice_period)
            contract.notice_end_date = notice_end_date

    # endregion [Dates Methods]

    # region [Actions]

    def action_running(self):
        for contract in self:
            contract.write({'state': 'open'})

    def action_set_to_draft(self):
        for contract in self:
            contract.write({'state': 'draft'})

    def _action_send_mail(self, subject, body, user_id, author_id, activity_to_do=False):
        '''
        Method To Send Mail And Activity TO Do
        '''
        mail_values = {
            'subject': f'{self.name} - {subject}',
            'body': body,
            'partner_ids': user_id.partner_id.ids,
            'recipient_ids': user_id.partner_id.ids,
            'author_id': author_id.id,  # partner
            'email_from': author_id.email,
            'email_to': user_id.partner_id.email if user_id.partner_id.email else False,
            'message_type': 'email',
        }
        mail_sudo = self.env['mail.mail'].sudo().create(mail_values)
        date_deadline = fields.date.today()
        if activity_to_do:
            self.with_context(mail_activity_quick_update=True).sudo().activity_schedule(
                'mail.mail_activity_data_todo',
                summary=subject,
                note=body,
                date_deadline=date_deadline,
                user_id=user_id.id)
        if mail_sudo:
            return True
        else:
            return False

    def _html_url(self, text):
        """ Transform the url into a clickable link with <a/> tag """
        """ My Edit Is To Add Name As Name Of Link Instead Of The Link Itself"""
        idx = 0
        final = ''
        link_tags = re.compile(
            r"""(?<!["'])((ftp|http|https):\/\/(\w+:{0,1}\w*@)?([^\s<"']+)(:[0-9]+)?(\/|\/([^\s<"']))?)(?![^\s<"']*["']|[^\s<"']*</a>)""")
        for item in re.finditer(link_tags, text):
            final += text[idx:item.start()]
            final += '<a href="%s" target="_blank" rel="noreferrer noopener">Open Contract</a>' % (item.group(0))
            idx = item.end()
        final += text[idx:]
        return final

    def _get_clickable_link(self, record):
        for contract in self:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            record_url = base_url + "/web#id=" + str(
                record.id) + "&view_type=form&model=%s&view_type=form" % record._name
            baseurl = contract._html_url(record_url)
            # request.note_url = baseurl
            return baseurl

    # endregion [Actions]

    # region [Cron Methods]
    @api.model
    def _cron_hr_contract_periods_check(self):
        cron_id = self.env.ref('pr_hr_contract.cron_hr_contract_periods_check')
        cron_update_vals = {
            'description': 'Hr contract periods check',
            'implement_date': fields.Datetime.now(),
        }
        # cron_update_id = self.env['bof.cron.update'].sudo().create(cron_update_vals)
        try:
            today = fields.Date.today()
            # Check Contracts That After 3 Weeks Trial Period Ends,
            # We Send Mail To Employee Manager To Make A Decision He Wants Him Or Not
            trial_end_contract_ids = self.env['hr.contract'].search([('state', '=', 'open'),
                                                                     ('trial_end_date', '=',
                                                                      (today - relativedelta(weeks=3)))])
            for trial_contract in trial_end_contract_ids:
                contract_notification_id = self.env['bof.hr.contract.notification'].sudo().create({
                    'employee_id': trial_contract.employee_id.id,
                    'notification_type': 'trial',
                    'end_date': trial_contract.trial_end_date,
                })
                odoobot = self.env.ref('base.partner_root')
                notification_clickable_url = trial_contract._get_clickable_link(contract_notification_id)
                subject = f'{trial_contract.name} - Trial Period State'
                body = f'Dear {trial_contract.employee_id.manager_id.name}\n' \
                       f'We Would Like To Inform You That:\n' \
                       f'Trial Period Of This Employee {trial_contract.employee_id.name} Finishes Within 3 Weeks \n\n ' \
                       f'You Should Make A Decision You Want This Employee With You Or Not \n\n Contract Notification {notification_clickable_url} \n\n Thanks'

                # Department Manager
                self._action_send_mail(subject=subject, body=body,
                                       user_id=trial_contract.employee_id.department_id.manager_id.user_id,
                                       author_id=odoobot)

                # HR Manager
                hr_manager_ids = self.env['res.users'].sudo().search(
                    [('groups_id', 'in', self.env.ref('hr_contract.group_hr_contract_manager').id)])
                for hr_manager in hr_manager_ids:
                    self._action_send_mail(subject=subject, body=body,
                                           user_id=hr_manager,
                                           author_id=odoobot)

                # Employee
                self._action_send_mail(subject=subject, body=body,
                                       user_id=trial_contract.employee_id.user_id,
                                       author_id=odoobot)

            # Check Contracts That After a Month Notice Period Ends
            # We Send Mail To Employee Manager To Evaluate This Employee
            notice_period_contract_ids = self.env['hr.contract'].search([('state', '=', 'open'),
                                                                         ('notice_end_date', '=',
                                                                          (today - relativedelta(months=1)))])
            for notice_contract in notice_period_contract_ids:
                contract_notification_id = self.env['bof.hr.contract.notification'].sudo().create({
                    'employee_id': notice_contract.employee_id.id,
                    'notification_type': 'end_contract',
                    'end_date': notice_contract.expected_end_date,
                })
                odoobot = self.env.ref('base.partner_root')
                notification_clickable_url = notice_contract._get_clickable_link(contract_notification_id)
                subject = f'{notice_contract.name} - Evaluation'
                body = f'Dear {notice_contract.employee_id.manager_id.name}\n' \
                       f'We Would Like To Inform You That:\n' \
                       f'Notice Period Of This Employee {notice_contract.employee_id.name} Finishes Within 1 Month \n\n ' \
                       f'You Should Evaluate This Employee \n\n Contract Notification {notification_clickable_url} \n\n Thanks'

                # Department Manager
                self._action_send_mail(subject=subject, body=body,
                                       user_id=notice_contract.employee_id.department_id.manager_id.user_id,
                                       author_id=odoobot)

            # HR Manager
            hr_manager_ids = self.env['res.users'].sudo().search(
                [('groups_id', 'in', self.env.ref('hr_contract.group_hr_contract_manager').id)])
            for hr_manager in hr_manager_ids:
                self._action_send_mail(subject=subject, body=body,
                                       user_id=hr_manager,
                                       author_id=odoobot)
            # Employee
            self._action_send_mail(subject=subject, body=body,
                                   user_id=notice_contract.employee_id.user_id,
                                   author_id=odoobot)
        except Exception as e:
            # raise UserError(f'{e}')
            cron_update_id.write({
                'failed_error': e,
                'model': self._name,
                # 'ir_cron': cron_id.id,
                'nextcall': cron_id.nextcall,
            })

    # endregion [Cron Methods]

    # region [System Methods]

    # endregion [System Methods]


class HrContractSalaryRule(models.Model):
    """
    """

    # region [Initial]
    _name = 'hr.contract.salary.rule'
    _description = 'Hr Employee Salary Rule'
    _rec_name = 'contract_id'
    # endregion [Initial]

    # region [Fields]
    contract_id = fields.Many2one('hr.contract', 'Contract', ondelete='cascade',
                                  help="Contract Of Employee")
    employee_id = fields.Many2one(related='contract_id.employee_id', string='Employee')
    salary_rule_id = fields.Many2one('hr.salary.rule', 'Salary Rule',
                                     domain="[('code', '!=', 'BASIC')]",
                                     ondelete='restrict', required=True)
    pay_in_payslip = fields.Boolean('Pay Payslip',
                                    help="True: Money will be paid to the employee\n"
                                         "False: Money will not be paid to the employee (as a package)")
    amount_type = fields.Selection([('fixed', 'Fixed'), ('percentage', 'Percentage')], 'Amount Type', default='fixed',
                                   help="How to calculate line amount:\n"
                                        "Fixed: Fixed Calculation\n"
                                        "Percentage: Calculated as a percentage from basic (wage)")
    amount_value = fields.Float('Value',
                                help='In case of percent will compute from basic salary,\n '
                                     'In Case of fixed amount ampunt will be same as value ')
    amount = fields.Float('Amount', compute='_compute_amount', store=True,
                          help="Total Paid Amount")
    sequence_ref = fields.Integer('No', compute="_sequence_ref_contract", copy=False)
    salary_rule_domain = fields.Char(compute='_compute_salary_rule_domain')

    # endregion [Fields]

    # region [methods]
    @api.depends('amount_type', 'amount_value', 'contract_id.wage')
    def _compute_amount(self):
        """
        This method computes the amount based on the amount type (percentage or fixed),
        the contract wage, the pay period, and the payment schedule.
        It also calculates monthly and one-time amounts accordingly.
        """

        for rec in self:

            # Check if the contract has a valid wage and amount type
            if rec.contract_id and rec.contract_id.wage and rec.amount_value:
                if rec.amount_type == 'percentage':
                    # Calculate the amount based on a percentage of the contract wage
                    rec.amount = rec.contract_id.wage * (rec.amount_value / 100)
                else:
                    # Fixed amount logic
                    rec.amount = rec.amount_value

            else:
                # Handle cases where data is missing or invalid
                rec.amount = 0

    @api.depends('contract_id.contract_salary_rule_ids')
    def _sequence_ref_contract(self):
        for line in self:
            count = 0
            if line.contract_id.contract_salary_rule_ids:
                for ln in line.contract_id.contract_salary_rule_ids:
                    count += 1
                    ln.sequence_ref = count
            else:
                line.sequence_ref = 0

    @api.depends('contract_id', 'contract_id.contract_salary_rule_ids')
    def _compute_salary_rule_domain(self):
        for rec in self:
            salary_rule_domain = "[('code', '!=', 'BASIC')]"
            if rec.contract_id and rec.contract_id.contract_salary_rule_ids:
                salary_rule_ids = rec.contract_id.contract_salary_rule_ids.mapped('salary_rule_id')
                if salary_rule_ids:
                    salary_rule_domain = json.dumps([('id', 'not in', salary_rule_ids.ids), ('code', '!=', 'BASIC')])
            rec.salary_rule_domain = salary_rule_domain

    # endregion [methods]
