from odoo import api, fields, models, _


class PaymentReceipt(models.Model):
    # region [Initial]
    _inherit = 'pr.payment.receipt'
    # endregion [Initial]

    # region [Fields]

    debit_cs_employee_id = fields.Many2one("account.analytic.account", string="Debit Employee",
                                     domain="[('analytic_plan_type', '=', 'employee')]", tracking=True)
    credit_cs_employee_id = fields.Many2one("account.analytic.account", string="Credit Employee",
                                           domain="[('analytic_plan_type', '=', 'employee')]", tracking=True)

    # endregion [Fields]

    # region [Onchange Methods]

    @api.onchange("debit_cs_employee_id")
    def _onchange_cs_employee_id(self):
        for line in self:
            analytic_distribution = {}
            if line.debit_cs_employee_id:
                # Analytic Distribution
                if line.debit_cs_employee_id.project_id and str(
                        line.debit_cs_employee_id.project_id.id) not in analytic_distribution:
                    analytic_distribution.update({
                        str(line.debit_cs_employee_id.project_id.id): 100.0
                    })
                if line.debit_cs_employee_id.section_id and str(
                        line.debit_cs_employee_id.section_id.id) not in analytic_distribution:
                    analytic_distribution.update({
                        str(line.debit_cs_employee_id.section_id.id): 100.0
                    })

                if line.debit_cs_employee_id.department_id and str(
                        line.debit_cs_employee_id.department_id.id) not in analytic_distribution:
                    analytic_distribution.update({
                        str(line.debit_cs_employee_id.department_id.id): 100.0
                    })

                analytic_distribution.update({
                    str(line.debit_cs_employee_id.id): 100.0
                })

            line.debit_analytic_distribution = analytic_distribution

    @api.onchange("credit_cs_employee_id")
    def _onchange_credit_cs_employee_id(self):
        for line in self:
            analytic_distribution = {}
            if line.credit_cs_employee_id:
                # Analytic Distribution
                if line.credit_cs_employee_id.cs_project_id and str(
                        line.credit_cs_employee_id.cs_project_id.id) not in analytic_distribution:
                    analytic_distribution.update({
                        str(line.credit_cs_employee_id.cs_project_id.id): 100.0
                    })
                if line.credit_cs_employee_id.section_id and str(
                        line.credit_cs_employee_id.section_id.id) not in analytic_distribution:
                    analytic_distribution.update({
                        str(line.credit_cs_employee_id.section_id.id): 100.0
                    })

                if line.credit_cs_employee_id.department_id and str(
                        line.credit_cs_employee_id.department_id.id) not in analytic_distribution:
                    analytic_distribution.update({
                        str(line.credit_cs_employee_id.department_id.id): 100.0
                    })

                analytic_distribution.update({
                    str(line.credit_cs_employee_id.id): 100.0
                })

            line.credit_analytic_distribution = analytic_distribution
            # Analytic Distribution

    # endregion [Onchange Methods]

    def _prepare_debit_move_line_vals(self):
        line_vals = super()._prepare_debit_move_line_vals()
        if self.debit_cs_employee_id:
            line_vals.update({"cs_employee_id": self.debit_cs_employee_id.id})
        return line_vals

    def _prepare_debit_tax_move_line_vals(self):
        line_vals = super()._prepare_debit_tax_move_line_vals()
        if self.debit_cs_employee_id:
            line_vals.update({"cs_employee_id": self.debit_cs_employee_id.id})
        return line_vals

    def _prepare_credit_move_line_vals(self):
        line_vals = super()._prepare_credit_move_line_vals()
        if self.credit_cs_employee_id:
            line_vals.update({"cs_employee_id": self.credit_cs_employee_id.id})
        return line_vals