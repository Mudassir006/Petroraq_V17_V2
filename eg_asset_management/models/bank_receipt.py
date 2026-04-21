from odoo import api, fields, models, _


class AccountBankReceipt(models.Model):
    # region [Initial]
    _inherit = 'pr.account.bank.receipt'
    # endregion [Initial]

    # region [Fields]

    asset_id = fields.Many2one("account.analytic.account", string="Asset",
                               domain="[('analytic_plan_type', '=', 'asset')]", tracking=True)

    # endregion [Fields]

    def _prepare_debit_move_line_vals(self):
        line_vals = super()._prepare_debit_move_line_vals()
        if self.asset_id:
            line_vals.update({"asset_id": self.asset_id.id})
        return line_vals


class AccountBankReceiptLine(models.Model):
    # region [Initial]
    _inherit = 'pr.account.bank.receipt.line'
    # endregion [Initial]

    # region [Fields]

    asset_id = fields.Many2one("account.analytic.account", string="Asset",
                               domain="[('analytic_plan_type', '=', 'asset')]", tracking=True)

    # endregion [Fields]

    # region [Onchange Methods]

    @api.onchange("account_id")
    def _onchange_account_id(self):
        res = super()._onchange_account_id()
        for line in self:
            if line.account_id:
                line.asset_id = False
        return res

    @api.onchange("asset_id")
    def _onchange_asset_id(self):
        for line in self:
            asset_ids = self.env["account.analytic.account"].sudo().search(
                [("analytic_plan_type", "=", "asset")]).mapped("id")

            analytic_distribution = {}
            if line.analytic_distribution:
                for key, value in line.analytic_distribution.items():
                    key_list = key.split(",")
                    for k_l in key_list:
                        if int(k_l) not in asset_ids:
                            analytic_distribution.update({
                                str(k_l): value
                            })

            if line.asset_id:
                # Analytic Distribution
                if line.asset_id.employee_id and str(
                        line.asset_id.employee_id.id) not in analytic_distribution:
                    analytic_distribution.update({
                        str(line.asset_id.employee_id.id): 100.0
                    })
                if line.asset_id.project_id and str(
                        line.asset_id.project_id.id) not in analytic_distribution:
                    analytic_distribution.update({
                        str(line.asset_id.project_id.id): 100.0
                    })
                if line.asset_id.section_id and str(
                        line.asset_id.section_id.id) not in analytic_distribution:
                    analytic_distribution.update({
                        str(line.asset_id.section_id.id): 100.0
                    })

                if line.asset_id.department_id and str(
                        line.asset_id.department_id.id) not in analytic_distribution:
                    analytic_distribution.update({
                        str(line.asset_id.department_id.id): 100.0
                    })

                analytic_distribution.update({
                    str(line.asset_id.id): 100.0
                })

                # Project Manager
                if line.cs_project_id and line.cs_project_id.project_partner_id:
                    line.partner_id = line.cs_project_id.project_partner_id.id
            line.analytic_distribution = analytic_distribution
            # Analytic Distribution

    # endregion [Onchange Methods]

    def prepare_credit_move_line_vals(self, move_id=False):
        line_vals = super().prepare_credit_move_line_vals(move_id)
        if self.asset_id:
            line_vals.update({"asset_id": self.asset_id.id})
        return line_vals

    def prepare_credit_tax_move_line_vals(self, move_id=False):
        line_vals = super().prepare_credit_tax_move_line_vals(move_id)
        if self.asset_id:
            line_vals.update({"asset_id": self.asset_id.id})
        return line_vals