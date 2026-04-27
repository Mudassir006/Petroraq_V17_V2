from odoo import models, fields, tools, api, exceptions, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import date_utils


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    other_amount = fields.Float(string="Other Amount", default=0.0)
    salary_journal_entry_id = fields.Many2one("account.move", readonly=True)

    hold_salary = fields.Boolean(string="Hold Salary", tracking=True, copy=False)
    hold_reason = fields.Char(string="Hold Reason", tracking=True, copy=False)
    hold_date = fields.Date(string="Hold Date", tracking=True, copy=False)
    release_date = fields.Date(string="Release Date", tracking=True, copy=False)

    def action_hold_salary(self):
        for slip in self:
            if slip.state in ('paid', 'cancel'):
                raise UserError(_("You cannot hold a payslip that is already Paid/Cancelled."))
            slip.write({
                'hold_salary': True,
                'hold_date': fields.Date.today(),
            })

    def action_release_salary(self):
        for slip in self:
            if slip.state in ('paid', 'cancel'):
                continue
            slip.write({
                'hold_salary': False,
                'release_date': fields.Date.today(),
            })

    attendance_sheet_line_ids = fields.One2many(
        related='attendance_sheet_id.line_ids',
        string="Attendance Lines",
        readonly=True
    )
    no_overtime = fields.Integer(related="attendance_sheet_id.no_overtime", readonly=True)
    tot_overtime = fields.Float(related="attendance_sheet_id.tot_overtime", readonly=True)
    tot_overtime_amount = fields.Float(related="attendance_sheet_id.tot_overtime_amount", readonly=True)
    approved_overtime_hours = fields.Float(related="attendance_sheet_id.approved_overtime_hours", readonly=True)
    approved_overtime_amount = fields.Float(related="attendance_sheet_id.approved_overtime_amount", readonly=True)
    no_late = fields.Integer(related="attendance_sheet_id.no_late", readonly=True)
    tot_late_in_minutes = fields.Float(string="Total Late In Minutes", readonly=True)
    tot_late = fields.Float(related="attendance_sheet_id.tot_late", readonly=True)
    tot_late_amount = fields.Float(related="attendance_sheet_id.tot_late_amount", readonly=True)
    no_early_checkout = fields.Integer(string="No of Early Check Out", readonly=True)
    tot_early_checkout = fields.Float(string="Total Early Check Out", readonly=True)
    tot_early_checkout_amount = fields.Float(string="Total Early Check Out Amount", readonly=True)
    early_check_out_minutes = fields.Float(string="Total Early Checkout Minutes", readonly=True)
    no_absence = fields.Integer(related="attendance_sheet_id.no_absence", readonly=True)
    tot_absence = fields.Float(related="attendance_sheet_id.tot_absence", readonly=True)
    tot_absence_amount = fields.Float(related="attendance_sheet_id.tot_absence_amount", readonly=True)
    no_difftime = fields.Integer(related="attendance_sheet_id.no_difftime", readonly=True)
    tot_difftime = fields.Float(related="attendance_sheet_id.tot_difftime", readonly=True)
    tot_difftime_amount = fields.Float(related="attendance_sheet_id.tot_difftime_amount", readonly=True)
    carry_forward_absence_amount = fields.Float(related="attendance_sheet_id.carry_forward_absence_amount",
                                                readonly=True)
    carry_forward_late_amount = fields.Float(related="attendance_sheet_id.carry_forward_late_amount", readonly=True)
    carry_forward_diff_amount = fields.Float(related="attendance_sheet_id.carry_forward_diff_amount", readonly=True)
    carry_forward_overtime_amount = fields.Float(related="attendance_sheet_id.carry_forward_overtime_amount",
                                                 readonly=True)
    carry_forward_early_checkout_amount = fields.Float(
        related="attendance_sheet_id.carry_forward_early_checkout_amount", readonly=True)
    carry_forward_deduction = fields.Float(string="Carry Forward Deduction", readonly=True)

    @api.model
    def _compute_gross_net_amounts(self, line_vals, excluded_earning_codes=None):
        excluded_earning_codes = excluded_earning_codes or set()
        totals_by_code = {}
        for vals in line_vals:
            code = vals.get("code")
            if not code:
                continue
            totals_by_code[code] = totals_by_code.get(code, 0.0) + (vals.get("total", 0.0) or 0.0)

        gosi_company_add = totals_by_code.get("GOSI_COMP_ADD", 0.0) + totals_by_code.get("GOSIALLOW", 0.0)
        gosi_employee_ded = totals_by_code.get("GOSI_EMP", 0.0) + totals_by_code.get("GOSI", 0.0)
        gosi_company_ded = totals_by_code.get("GOSI_COMP_DED", 0.0)
        advance_allowances = totals_by_code.get("ADVALL", 0.0)
        reimbursement_amount = totals_by_code.get("REIMBURSEMENT199", 0.0)

        net_excluded = {"NET", "GROSS", "ADVALL", "GOSI_EMP", "GOSI", "GOSI_COMP_DED", "REIMBURSEMENT199"}
        gross_amount = sum(
            vals.get("total", 0.0) or 0.0
            for vals in line_vals
            if vals.get("code")
            and vals.get("code") not in net_excluded
        )
        # Keep formula explicit and in requested order
        net_amount = gross_amount + reimbursement_amount + advance_allowances + gosi_company_ded + gosi_employee_ded
        return gross_amount, net_amount, gosi_company_add

    def _sync_attendance_summary_fields(self):
        field_names = [
            "tot_late_in_minutes",
            "no_early_checkout",
            "tot_early_checkout",
            "tot_early_checkout_amount",
            "early_check_out_minutes",
        ]
        for payslip in self:
            update_vals = {}
            for field_name in field_names:
                value = 0.0
                if payslip.attendance_sheet_id and field_name in payslip.attendance_sheet_id._fields:
                    value = getattr(payslip.attendance_sheet_id, field_name, 0.0) or 0.0
                if field_name == "no_early_checkout":
                    value = int(value)
                update_vals[field_name] = value
            update_vals["carry_forward_deduction"] = (
                    (payslip.carry_forward_absence_amount or 0.0)
                    + (payslip.carry_forward_late_amount or 0.0)
                    + (payslip.carry_forward_diff_amount or 0.0)
                    + (payslip.carry_forward_early_checkout_amount or 0.0)
            )
            payslip.update(update_vals)

    def _upsert_attendance_deduction_line(self, line_vals, payslip, code, amount):
        """Ensure attendance deduction line exists and reflects latest attendance-sheet amount."""
        if abs(amount or 0.0) < 1e-6:
            return

        existing_line = None
        for vals in line_vals:
            if vals.get('code') == code:
                existing_line = vals
                break

        if existing_line:
            existing_line['amount'] = amount
            existing_line['total'] = amount
            existing_line['quantity'] = 1
            existing_line['rate'] = 100
            return

        salary_rule = self.env['hr.salary.rule'].search([
            ('code', '=', code),
            ('struct_id', '=', payslip.struct_id.id),
        ], limit=1)
        if not salary_rule:
            return

        line_vals.append({
            'sequence': salary_rule.sequence,
            'code': salary_rule.code,
            'name': salary_rule.name,
            'salary_rule_id': salary_rule.id,
            'contract_id': payslip.employee_id.contract_id.id if payslip.employee_id.contract_id else False,
            'employee_id': payslip.employee_id.id,
            'amount': amount,
            'quantity': 1,
            'rate': 100,
            'total': amount,
            'slip_id': payslip.id,
        })

    def _get_payslip_lines(self):
        line_vals = super()._get_payslip_lines()
        for payslip in self:
            payslip._sync_attendance_summary_fields()

            contract_id = payslip.employee_id.contract_id
            gosi_salary_rule = self.env.ref("pr_hr_payroll.hr_salary_rule_saudi_gosi")
            gosi_allow_salary_rule = self.env.ref("pr_hr_payroll.hr_salary_rule_saudi_gosi_allow")
            # ===============================
            # GOSI – single source of truth
            # ===============================
            company_gosi = contract_id.company_portion or 0.0
            employee_gosi = contract_id.employee_portion or 0.0

            if payslip.employee_id.country_id and payslip.employee_id.country_id.is_homeland and contract_id.is_automatic_gosi:
                start_of_month = date_utils.start_of(payslip.date_to, 'month')
                end_of_month = date_utils.end_of(payslip.date_to, 'month')
                month_days = (end_of_month - start_of_month).days + 1
                total_amount = 0
                if end_of_month > contract_id.date_start > payslip.date_from:
                    wage = contract_id.wage
                    salary_month_days = (end_of_month - contract_id.date_start).days + 1
                    total_amount = (salary_month_days * wage) / month_days
                elif payslip.date_from >= contract_id.date_start:
                    total_amount = contract_id.wage
                salary_rule_ids = contract_id.contract_salary_rule_ids
                if salary_rule_ids:
                    acc_salary_rule_id = salary_rule_ids.filtered(lambda l: l.salary_rule_id.code == "ACCOMMODATION")
                    if acc_salary_rule_id:
                        rule_total_amount = acc_salary_rule_id.amount
                        if end_of_month > contract_id.date_start > payslip.date_from:
                            salary_month_days = (end_of_month - contract_id.date_start).days + 1
                            rule_amount = (salary_month_days * rule_total_amount) / month_days
                            total_amount += rule_amount
                        elif payslip.date_from >= contract_id.date_start:
                            total_amount += rule_total_amount
                if gosi_salary_rule:
                    # line_vals.append({
                    #     'sequence': gosi_salary_rule.sequence,
                    #     'code': gosi_salary_rule.code,
                    #     'name': gosi_salary_rule.name,
                    #     'salary_rule_id': gosi_salary_rule.id,
                    #     'contract_id': payslip.employee_id.contract_id.id,
                    #     'employee_id': payslip.employee_id.id,
                    #     'amount': (total_amount * -1 * .0975) or 0,
                    #     'quantity': 1,
                    #     'rate': 100,
                    #     'total': (total_amount * -1 * .0975) or 0,
                    #     'slip_id': payslip.id,
                    # })
                    # 1) Company GOSI → ADD to GROSS
                    line_vals.append({
                        'sequence': 44,
                        'code': 'GOSI_COMP_ADD',
                        'name': 'GOSI Company Contribution',
                        'salary_rule_id': gosi_allow_salary_rule.id,
                        'contract_id': contract_id.id,
                        'employee_id': payslip.employee_id.id,
                        'amount': company_gosi,
                        'quantity': 1,
                        'rate': 100,
                        'total': company_gosi,
                        'slip_id': payslip.id,
                    })

                    # 2) Employee GOSI → DEDUCT from NET
                    line_vals.append({
                        'sequence': 45,
                        'code': 'GOSI_EMP',
                        'name': 'GOSI Employee Deduction',
                        'salary_rule_id': gosi_salary_rule.id,
                        'contract_id': contract_id.id,
                        'employee_id': payslip.employee_id.id,
                        'amount': -employee_gosi,
                        'quantity': 1,
                        'rate': 100,
                        'total': -employee_gosi,
                        'slip_id': payslip.id,
                    })

                    # 3) Company GOSI → DEDUCT from NET
                    line_vals.append({
                        'sequence': 46,
                        'code': 'GOSI_COMP_DED',
                        'name': 'GOSI Company Deduction',
                        'salary_rule_id': gosi_salary_rule.id,
                        'contract_id': contract_id.id,
                        'employee_id': payslip.employee_id.id,
                        'amount': -company_gosi,
                        'quantity': 1,
                        'rate': 100,
                        'total': -company_gosi,
                        'slip_id': payslip.id,
                    })


            else:
                start_of_month = date_utils.start_of(payslip.date_to, 'month')
                end_of_month = date_utils.end_of(payslip.date_to, 'month')
                month_days = (end_of_month - start_of_month).days + 1
                total_amount = 0
                if end_of_month > contract_id.date_start > payslip.date_from:
                    wage = contract_id.wage
                    salary_month_days = (end_of_month - contract_id.date_start).days + 1
                    total_amount = (salary_month_days * wage) / month_days
                elif payslip.date_from >= contract_id.date_start:
                    total_amount = contract_id.wage
                salary_rule_ids = contract_id.contract_salary_rule_ids
                if salary_rule_ids:
                    acc_salary_rule_id = salary_rule_ids.filtered(lambda l: l.salary_rule_id.code == "ACCOMMODATION")
                    if acc_salary_rule_id:
                        rule_total_amount = acc_salary_rule_id.amount
                        if end_of_month > contract_id.date_start > payslip.date_from:
                            salary_month_days = (end_of_month - contract_id.date_start).days + 1
                            rule_amount = (salary_month_days * rule_total_amount) / month_days
                            total_amount += rule_amount
                        elif payslip.date_from >= contract_id.date_start:
                            total_amount += rule_total_amount
                if gosi_salary_rule:
                    gosi_line_amount = total_amount * 1 * .02
                    line_vals.append({
                        'sequence': gosi_allow_salary_rule.sequence,
                        'code': gosi_allow_salary_rule.code,
                        'name': gosi_allow_salary_rule.name,
                        'salary_rule_id': gosi_allow_salary_rule.id,
                        'contract_id': payslip.employee_id.contract_id.id,
                        'employee_id': payslip.employee_id.id,
                        'amount': (gosi_line_amount if gosi_line_amount <= 900 else 900) or 0,
                        'quantity': 1,
                        'rate': 100,
                        'total': (gosi_line_amount if gosi_line_amount <= 900 else 900) or 0,
                        'slip_id': payslip.id,
                    })

                    line_vals.append({
                        'sequence': gosi_salary_rule.sequence,
                        'code': gosi_salary_rule.code,
                        'name': gosi_salary_rule.name,
                        'salary_rule_id': gosi_salary_rule.id,
                        'contract_id': payslip.employee_id.contract_id.id,
                        'employee_id': payslip.employee_id.id,
                        'amount': (gosi_line_amount * -1 if gosi_line_amount <= 900 else -900) or 0,
                        'quantity': 1,
                        'rate': 100,
                        'total': (gosi_line_amount * -1 if gosi_line_amount <= 900 else -900) or 0,
                        'slip_id': payslip.id,
                    })

            # Check Other Payment Like: First Payslip Days
            if contract_id.other_first_payslip and contract_id.joining_date:
                start_of_month = date_utils.start_of(contract_id.joining_date, 'month')
                end_of_month = date_utils.end_of(contract_id.joining_date, 'month')
                month_days = (end_of_month - start_of_month).days + 1
                extra_salary_days = (end_of_month - contract_id.joining_date).days + 1
                other_salary_rule = self.env.ref("pr_hr_payroll.hr_salary_rule_other_payments")
                gross_salary = contract_id.gross_amount
                extra_salary_amount = (extra_salary_days * gross_salary) / month_days
                if other_salary_rule and extra_salary_amount > 0:
                    line_vals.append({
                        'sequence': other_salary_rule.sequence,
                        'code': other_salary_rule.code,
                        'name': other_salary_rule.name,
                        'salary_rule_id': other_salary_rule.id,
                        'contract_id': payslip.employee_id.contract_id.id,
                        'employee_id': payslip.employee_id.id,
                        'amount': extra_salary_amount or 0,
                        'quantity': 1,
                        'rate': 100,
                        'total': extra_salary_amount or 0,
                        'slip_id': payslip.id,
                    })

                # Check GOSI Amount For These Days If Employee Is Saudi
                if payslip.employee_id.country_id and payslip.employee_id.country_id.is_homeland and contract_id.is_automatic_gosi:
                    gosi_salary_amount = contract_id.wage
                    salary_rule_ids = contract_id.contract_salary_rule_ids
                    if salary_rule_ids:
                        acc_salary_rule_id = salary_rule_ids.filtered(
                            lambda l: l.salary_rule_id.code == "ACCOMMODATION")
                        if acc_salary_rule_id:
                            gosi_salary_amount += acc_salary_rule_id.amount
                    extra_gosi_salary_amount = (extra_salary_days * gosi_salary_amount) / month_days
                    if gosi_salary_rule and extra_gosi_salary_amount > 0:
                        line_vals.append({
                            'sequence': gosi_salary_rule.sequence,
                            'code': gosi_salary_rule.code,
                            'name': gosi_salary_rule.name,
                            'salary_rule_id': gosi_salary_rule.id,
                            'contract_id': payslip.employee_id.contract_id.id,
                            'employee_id': payslip.employee_id.id,
                            'amount': (extra_gosi_salary_amount * -1 * .0975) or 0,
                            'quantity': 1,
                            'rate': 100,
                            'total': (extra_gosi_salary_amount * -1 * .0975) or 0,
                            'slip_id': payslip.id,
                        })

            # Contract Salary Rules
            if payslip.employee_id.contract_id and payslip.employee_id.contract_id.contract_salary_rule_ids:
                for salary_rule_line_id in payslip.employee_id.contract_id.contract_salary_rule_ids:
                    if salary_rule_line_id.pay_in_payslip:
                        salary_rule_id = salary_rule_line_id.sudo().salary_rule_id.sudo()
                        base_amount = salary_rule_line_id.sudo().amount or 0.0
                        eligible_amount = self._compute_attendance_eligible_amount(
                            payslip,
                            salary_rule_id,
                            base_amount,
                        )
                        line_vals.append({
                            'sequence': salary_rule_id.sequence,
                            'code': salary_rule_id.code,
                            'name': salary_rule_id.name,
                            'salary_rule_id': salary_rule_id.id,
                            'contract_id': payslip.employee_id.contract_id.id,
                            'employee_id': payslip.employee_id.id,
                            'amount': eligible_amount,
                            'quantity': 1,
                            'rate': 100,
                            'total': eligible_amount,
                            'slip_id': payslip.id,
                        })

            if payslip.attendance_sheet_id and payslip.employee_id.compute_attendance:
                att_sheet = payslip.attendance_sheet_id
                abs_amount = -((att_sheet.tot_absence_amount or 0.0) + (
                        getattr(att_sheet, 'carry_forward_absence_amount', 0.0) or 0.0))
                late_amount = -((att_sheet.tot_late_amount or 0.0) + (
                        getattr(att_sheet, 'carry_forward_late_amount', 0.0) or 0.0))
                eco_amount = -((getattr(att_sheet, 'tot_early_checkout_amount', 0.0) or 0.0) + (
                        getattr(att_sheet, 'carry_forward_early_checkout_amount', 0.0) or 0.0))
                diff_amount = -((att_sheet.tot_difftime_amount or 0.0) + (
                        getattr(att_sheet, 'carry_forward_diff_amount', 0.0) or 0.0))
                ovt_amount = ((att_sheet.approved_overtime_amount or 0.0) + (
                        getattr(att_sheet, 'carry_forward_overtime_amount',
                                0.0) or 0.0)) if payslip.employee_id.add_overtime else 0.0
                self._upsert_attendance_deduction_line(line_vals, payslip, 'OVT', ovt_amount)
                self._upsert_attendance_deduction_line(line_vals, payslip, 'ABS', abs_amount)
                self._upsert_attendance_deduction_line(line_vals, payslip, 'LATE', late_amount)
                self._upsert_attendance_deduction_line(line_vals, payslip, 'ECO', eco_amount)
                self._upsert_attendance_deduction_line(line_vals, payslip, 'DIFFT', diff_amount)
            elif payslip.attendance_sheet_id and not payslip.employee_id.compute_attendance:
                for vals in line_vals:
                    if vals.get('code') in ['ABS', 'LATE', 'ECO', 'DIFFT']:
                        vals['amount'] = 0.0
                        vals['total'] = 0.0

            gross_amount, net_amount, _gosi_company_add = self._compute_gross_net_amounts(
                line_vals,
            )

            for val_line in line_vals:
                code = val_line.get("code")
                if code == "NET":
                    val_line["amount"] = net_amount
                    val_line["total"] = net_amount
                elif code == "GROSS":
                    val_line["amount"] = gross_amount
                    val_line["total"] = gross_amount
        return line_vals

    def _compute_attendance_eligible_amount(self, payslip, salary_rule, base_amount):
        """Prorate contract rule amount based on attendance eligibility in the payslip period."""
        if not salary_rule.attendance_based_eligibility:
            return base_amount

        att_sheet = payslip.attendance_sheet_id
        if not att_sheet:
            return 0.0

        sheet_lines = att_sheet.line_ids.filtered(
            lambda l: payslip.date_from <= l.date <= payslip.date_to and (not l.status or l.status == 'ab')
        )
        considered_days = len(sheet_lines)
        if not considered_days:
            return 0.0

        min_hours = salary_rule.attendance_min_worked_hours or 0.0
        require_presence = salary_rule.attendance_require_presence

        eligible_days = 0
        for line in sheet_lines:
            is_absent = line.status == 'ab'
            if require_presence and is_absent:
                continue
            if line.worked_hours >= min_hours:
                eligible_days += 1

        return (base_amount * eligible_days / considered_days) if considered_days else 0.0

    def check_payslip_dates(self):
        for payslip in self:
            payslip._sync_attendance_summary_fields()

            payslip_days = (payslip.date_to - payslip.date_from).days + 1
            start_of_month = date_utils.start_of(payslip.date_to, 'month')
            end_of_month = date_utils.end_of(payslip.date_to, 'month')
            month_days = (end_of_month - start_of_month).days + 1
            for line in payslip.line_ids:
                if line.code not in ["GROSS", "NET"]:
                    amount = (line.total * payslip_days) / month_days
                    line.sudo().write({"amount": amount, "total": amount})
            # Calculate net and gross amounts, excluding "NET" and "GROSS" codes
            prepared_line_vals = [{"code": l.code, "total": l.total} for l in payslip.line_ids]
            gross_amount, net_amount, _gosi_company_add = self._compute_gross_net_amounts(
                prepared_line_vals,
            )

            for val_line in payslip.line_ids:
                code = val_line.code
                if code == "NET":
                    val_line.amount = net_amount
                    val_line.total = net_amount
                elif code == "GROSS":
                    val_line.amount = gross_amount
                    val_line.total = gross_amount

    def prepare_payslip_entry_vals_lines(self):
        for rec in self:
            payslip_entry_vals_lines = []
            if rec.state != 'done':
                # raise UserError(_('Cannot mark payslip as paid if not confirmed.'))
                raise UserError(_('Cannot pay the payslip if not confirmed.'))
            if not rec.employee_id.employee_cost_center_id:
                raise ValidationError(
                    f"This employee {rec.employee_id.name} does not have cost center, please check !!")
            if not rec.employee_id.employee_account_id:
                raise ValidationError(
                    f"This employee {rec.employee_id.name} does not have account, please check !!")
            for line in rec.line_ids:
                if not line.salary_rule_id.account_id:
                    raise ValidationError(
                        f"This salary rule {line.salary_rule_id.name} does not have account, please check !!")
                payslip_entry_line_vals = self.prepare_payslip_entry_line_vals(line=line)
                if payslip_entry_line_vals:
                    payslip_entry_vals_lines.append((0, 0, payslip_entry_line_vals))
            return payslip_entry_vals_lines

    def prepare_payslip_entry_line_vals(self, line):
        if (line.total != 0 or line.total > 0 or line.total < 0) and line.salary_rule_id.code not in ["GROSS", "NET"]:
            payslip_date_to = line.slip_id.date_to or self.date_to
            month_name = payslip_date_to.strftime('%B') if payslip_date_to else ""
            year_name = payslip_date_to.year if payslip_date_to else ""
            analytic_distribution = {}
            if self.employee_id.department_cost_center_id:
                analytic_distribution[str(self.employee_id.department_cost_center_id.id)] = 100
            if self.employee_id.section_cost_center_id:
                analytic_distribution[str(self.employee_id.section_cost_center_id.id)] = 100
            if self.employee_id.project_cost_center_id:
                analytic_distribution[str(self.employee_id.project_cost_center_id.id)] = 100
            if self.employee_id.employee_cost_center_id:
                analytic_distribution[str(self.employee_id.employee_cost_center_id.id)] = 100
            # if line.slip_id.employee_id.department_id and line.slip_id.employee_id.department_id.department_cost_center_id:
            #     analytic_distribution.update({str(line.slip_id.employee_id.department_id.department_cost_center_id.id): 100})
            line_vals = {
                "account_id": line.salary_rule_id.account_id.id,
                "analytic_distribution": analytic_distribution,
            }
            # Project Manager
            if self.employee_id.project_cost_center_id and self.employee_id.project_cost_center_id.project_partner_id:
                line_vals.update({"partner_id": self.employee_id.project_cost_center_id.project_partner_id.id})
            if line.salary_rule_id.code in ["LOAN", "ADVALL"]:
                line_vals["account_id"] = line.slip_id.employee_id.employee_account_id.id

            if line.category_id.code in ["BASIC", "ALW"]:
                line_vals.update({
                    "name": f"{line.slip_id.employee_id.code} - {line.slip_id.employee_id.name} {line.salary_rule_id.name} of Month {month_name} {year_name}",
                    "debit": abs(line.total),
                    "credit": 0.0,
                })
            elif line.category_id.code == "DED":
                line_vals.update({
                    "name": f"{line.slip_id.employee_id.code} - {line.slip_id.employee_id.name} {line.salary_rule_id.name} of Month {month_name} {year_name}",
                    "credit": abs(line.total),
                    "debit": 0.0,
                })
            return line_vals
        else:
            return False

    def action_open_salary_journal_entry(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": self.salary_journal_entry_id.id,
            "views": [[self.env.ref('account.view_move_form').id, "form"]],
            "target": "current",
            "name": self.name,
            "context": {"form_view_initial_mode": "readonly"}
        }
