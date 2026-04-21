from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from hijri_converter import Gregorian
from datetime import date


class HREmployeeIqamaCheckWizard(models.Model):
    """
    """

    # region [Initial]
    _name = 'hr.employee.iqama.check.wizard'
    _description = 'Iqama Check Expiry'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    # endregion [Initial]

    # region [Fields]

    from_date = fields.Date(string="From", required=True)
    to_date = fields.Date(string="To")
    search_notes = fields.Text(string="Search Notes", readonly=True)
    line_ids = fields.One2many("hr.employee.iqama.check.line.wizard", "wizard_id")

    # endregion [Fields]

    def action_search(self):
        for wizard in self:
            domain = [("expiry_date", ">=", wizard.from_date)]
            if wizard.to_date:
                domain.append(("expiry_date", "<=", wizard.to_date))

            iqama_ids = self.env["hr.employee.iqama.line"].search(domain)
            if iqama_ids:
                line_ids = []
                for iqama in iqama_ids:
                    line_ids.append((0, 0, {
                        "wizard_id": wizard.id,
                        "iqama_id": iqama.id,
                        "employee_id": iqama.employee_id.id,
                        "name": iqama.name,
                        "identification_id": iqama.identification_id,
                        "place_of_issue": iqama.place_of_issue,
                        "expiry_date": iqama.expiry_date,
                        "expiry_date_hijri": iqama.expiry_date_hijri,
                        "state": iqama.state,
                    }))
                wizard.line_ids = line_ids
            else:
                wizard.search_notes = f"There Is No Iqamas Expire In These Dates"
            view = self.env.ref("pr_hr.hr_employee_iqama_check_expiry_wizard_view_form")
            action = {
                "name": _("Iqama Check Expiry"),
                "type": "ir.actions.act_window",
                "res_model": "hr.employee.iqama.check.wizard",
                "views": [[view.id, "form"]],
                "res_id": wizard.id,
                "target": "new",
            }
            return action


class HREmployeeIqamaCheckLineWizard(models.Model):
    """
    """

    # region [Initial]
    _name = 'hr.employee.iqama.check.line.wizard'
    _description = 'Iqama Check Expiry Line'
    # endregion [Initial]

    # region [Fields]
    wizard_id = fields.Many2one('hr.employee.iqama.check.wizard', string='Wizard', required=True)
    iqama_id = fields.Many2one("hr.employee.iqama", readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, readonly=True)
    relation_id = fields.Many2one('hr.employee.dependent.relation', string='Relation', required=True, readonly=True)
    identification_id = fields.Char(string='Iqama No.', required=True, readonly=True)
    name = fields.Char(string='Description', required=False, readonly=False)
    place_of_issue = fields.Char(string="Place Of Issue", tracking=True, readonly=False)
    expiry_date = fields.Date(string="Expiry Date", required=True, readonly=False)
    expiry_date_hijri = fields.Char(string="Expiry Date Hijri", required=False, readonly=True)
    state = fields.Selection([('valid', 'Valid'), ('expired', 'Expired')], required=True, string="Status",
                             tracking=True, readonly=False)
    # endregion [Fields]

    def action_edit(self):
        """
        """
        self.ensure_one()
        view = self.env.ref("pr_hr.hr_employee_iqama_check_expiry_line_wizard_view_form")
        return {
            'name': "Iqama Check Expiry Editing",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.employee.iqama.check.line.wizard',
            "views": [[view.id, "form"]],
            'res_id': self.id,
            'target': 'new',
        }

    def action_renew(self):
        """
        """
        self.ensure_one()
        view = self.env.ref("pr_hr.hr_employee_iqama_line_add_wizard_view_form")
        return {
            'name': "IQAMA RENEW",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.employee.iqama.line.add.wizard',
            "views": [[view.id, "form"]],
            "context": {'default_iqama_id': self.iqama_id.id,
                        'default_employee_id': self.employee_id.id,
                        'default_relation_id': self.relation_id.id,
                        'default_identification_id': self.identification_id,
                        },
            'target': 'new',
        }

    @api.onchange("expiry_date")
    def _compute_expiry_date_hijri(self):
        for line in self:
            if line.expiry_date:
                # Convert it to Hijri date
                gregorian_date_obj = Gregorian(line.expiry_date.year, line.expiry_date.month,
                                               line.expiry_date.day)
                hijri_date = gregorian_date_obj.to_hijri()
                line.expiry_date_hijri = f'{hijri_date}'
            else:
                line.expiry_date_hijri = False

    def action_apply(self):
        for line in self:
            iqama_id = line.iqama_id.sudo()
            iqama_id.write({
                "name": line.name,
                "place_of_issue": line.place_of_issue,
                "expiry_date": line.expiry_date,
                "expiry_date_hijri": line.expiry_date_hijri,
                "state": line.state,
            })
            view = self.env.ref("pr_hr.hr_employee_iqama_check_expiry_wizard_view_form")
            action = {
                "name": _("Iqama Check Expiry"),
                "type": "ir.actions.act_window",
                "res_model": "hr.employee.iqama.check.wizard",
                "views": [[view.id, "form"]],
                "res_id": line.wizard.id,
                "target": "new",
            }
            return action


