from odoo import api, fields, models, _


class AccountMoveLine(models.Model):
    # region [Initial]
    _inherit = 'account.move.line'
    # endregion [Initial]

    cs_employee_id = fields.Many2one("account.analytic.account", string="Employee",
                                    domain="[('analytic_plan_type', '=', 'employee')]")

    # region [Onchange Methods]

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
                if line.cs_employee_id.project_id and str(line.cs_employee_id.project_id.id) not in analytic_distribution:
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
