from odoo import api, fields, models, _


class AccountCashPaymentLine(models.Model):
    # region [Initial]
    _inherit = 'pr.account.cash.payment.line'
    # endregion [Initial]

    # region [Fields]

    cs_employee_id = fields.Many2one("account.analytic.account", string="Employee",
                                     domain="[('analytic_plan_type', '=', 'employee')]", tracking=True)

    # endregion [Fields]

    # region [Onchange Methods]

    @api.onchange("account_id")
    def _onchange_account_id(self):
        res = super()._onchange_account_id()
        for line in self:
            if line.account_id:
                line.cs_employee_id = False
        return res

    @api.onchange("cs_project_id")
    def _onchange_cs_project_id(self):
        for line in self:

            analytic_distribution = {}
            if line.cs_project_id:
                # Analytic Distribution
                if line.cs_project_id.department_id:
                    analytic_distribution.update({
                        str(line.cs_project_id.department_id.id): 100.0
                    })
                if line.cs_project_id.section_id:
                    analytic_distribution.update({
                        str(line.cs_project_id.section_id.id): 100.0
                    })
                analytic_distribution.update({
                    str(line.cs_project_id.id): 100.0
                })

                if line.cs_project_id.employee_id:
                    analytic_distribution.update({
                        str(line.cs_project_id.employee_id.id): 100.0
                    })

                # Project Manager
                if line.cs_project_id.project_partner_id:
                    line.partner_id = line.cs_project_id.project_partner_id.id
            line.analytic_distribution = analytic_distribution
            # Analytic Distribution

    @api.onchange("cs_employee_id")
    def _onchange_cs_employee_id(self):
        for line in self:
            employee_ids = self.env["account.analytic.account"].sudo().search(
                [("analytic_plan_type", "=", "employee")]).mapped("id")

            analytic_distribution = {}
            if line.analytic_distribution:
                for key, value in line.analytic_distribution.items():
                    key_list = key.split(",")
                    for k_l in key_list:
                        if int(k_l) not in employee_ids:
                            analytic_distribution.update({
                                str(k_l): value
                            })

            if line.cs_employee_id:
                # Analytic Distribution
                if line.cs_employee_id.project_id and str(
                        line.cs_employee_id.project_id.id) not in analytic_distribution:
                    analytic_distribution.update({
                        str(line.cs_employee_id.project_id.id): 100.0
                    })
                if line.cs_employee_id.section_id and str(
                        line.cs_employee_id.section_id.id) not in analytic_distribution:
                    analytic_distribution.update({
                        str(line.cs_employee_id.section_id.id): 100.0
                    })

                if line.cs_employee_id.department_id and str(
                        line.cs_employee_id.department_id.id) not in analytic_distribution:
                    analytic_distribution.update({
                        str(line.cs_employee_id.department_id.id): 100.0
                    })

                analytic_distribution.update({
                    str(line.cs_employee_id.id): 100.0
                })

                # Project Manager
                if line.cs_project_id and line.cs_project_id.project_partner_id:
                    line.partner_id = line.cs_project_id.project_partner_id.id
            line.analytic_distribution = analytic_distribution
            # Analytic Distribution

    # endregion [Onchange Methods]

    def prepare_debit_move_line_vals(self, move_id=False):
        line_vals = super().prepare_debit_move_line_vals(move_id)
        if self.cs_employee_id:
            line_vals.update({"cs_employee_id": self.cs_employee_id.id})
        return line_vals

    def prepare_debit_tax_move_line_vals(self, move_id=False):
        line_vals = super().prepare_debit_tax_move_line_vals(move_id)
        if self.cs_employee_id:
            line_vals.update({"cs_employee_id": self.cs_employee_id.id})
        return line_vals