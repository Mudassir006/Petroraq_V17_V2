# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools


class ContractSalaryRule(models.Model):
    _name = "query.hr.contract.salary.rule"
    _description = "Contract Salary Rule Query"
    _auto = False
    # _order = 'employee_code'

    contract_id = fields.Many2one('hr.contract', 'Contract', readonly=True)
    employee_id = fields.Many2one('hr.employee', 'Employee', readonly=True)
    salary_rule_id = fields.Many2one('hr.salary.rule', 'Salary Rule', readonly=True)
    amount_type = fields.Selection([('fixed', 'Fixed'), ('percentage', 'Percentage')],
                                   'Amount Type', default='fixed', readonly=True)
    amount_value = fields.Float('Value', readonly=True)
    schedule_pay = fields.Selection([("monthly", "Monthly"),
                                     ("bi-monthly", "Bi-monthly"),
                                     ("quarterly", "Quarterly"),
                                     ("semi-annually", "Semi-annually"),
                                     ("annually", "Annually"), ],
                                    string="Scheduled Pay", readonly=True)
    pay_for_period = fields.Selection([("monthly", "Monthly"), ("annually", "Annually"), ],
                                      string="Pay For", default="monthly", readonly=True,
                                      help="Defines the amount is for which period.", )
    start_pay = fields.Selection(
        [('1', '01-January'), ('2', '02-February'), ('3', '03-March'),
         ('4', '04-April'), ('5', '05-May'), ('6', '06-June'),
         ('7', '07-July'), ('8', '08-August'), ('9', '09-September'),
         ('10', '10-October'), ('11', '11-November'), ('12', '12-December')], default='1', readonly=True)
    amount = fields.Float('Amount', readonly=True)
    monthly_amount = fields.Float('Monthly Amount', readonly=True)
    one_time_amount = fields.Float('One Time Amount', readonly=True)
    pay_in_payslip = fields.Boolean('Pay Payslip', readonly=True)


    def _select_contract(self):
        return """
            SELECT MIN(c.id) AS id, id as contract_id, (SELECT id from hr_salary_rule WHERE code = 'BASIC') as salary_rule_id, 
		    employee_id, true as pay_in_payslip, 'fixed' as amount_type,wage as amount_value,
		    'monthly' as pay_for_period,
		    wage as amount, 'monthly' as schedule_pay, wage as one_time_amount,
		    wage as monthly_amount, '1' as start_pay
        """

    def _select_salary_rule(self):
        return """
            SELECT 	 MIN(csr.id) AS id, contract_id, salary_rule_id,
		    (select employee_id from hr_contract where id = contract_id) as employee_id, 
		    pay_in_payslip, amount_type, amount_value, pay_for_period, amount, schedule_pay, one_time_amount,
		    monthly_amount, start_pay
        """

    def _from_contract(self):
        return """
            FROM  hr_contract as c
        """

    def _from_salary_rule(self):
        return """
            FROM 	hr_contract_salary_rule csr 
        """

    def _group_by_contract(self):
        return """
            GROUP BY
                c.id
        """

    def _group_by_salary_rule(self):
        return """
            GROUP BY
                csr.id
        """

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                %s
                %s
                %s
                UNION ALL
                %s
                %s
                %s
            )
        """ % (
            self._table,
            self._select_contract(), self._from_contract(), self._group_by_contract(),
            self._select_salary_rule(), self._from_salary_rule(), self._group_by_salary_rule())
                         )
