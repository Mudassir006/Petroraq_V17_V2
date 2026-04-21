import re

from odoo import models, fields, api


code_description = [
    ('n/a', 'N/A'),
    ('0', 'Success'),
    ('-1', 'Invalid parameter'),
    ('-2', 'Mismatch between transmitted user photo data and given Size'),
    ('-3', 'Read/write error'),
    ('-9', 'Mismatch between transmitted template data and given Size'),
    ('-10', 'User specified by PIN does not exist in the device'),
    ('-11', 'Illegal fingerprint template format'),
    ('-12', 'Illegal fingerprint template'),
    ('-1001', 'Capacity limit'),
    ('-1002', 'Device not supported'),
    ('-1003', 'Command execution timeout'),
    ('-1004', 'Data inconsistent with device configuration'),
    ('-1005', 'Device busy'),
    ('-1006', 'Data too long'),
    ('-1007', 'Memory error'),
    ('-1008', 'Failed to fetch data from the server'),
    ('2', '[Enroll fingerprint] Fingerprint corresponding to the user already exists'),
    ('4', '[Enroll fingerprint] Registration failed, usually due to poor fingerprint quality or inconsistent fingerprints pressed three times'),
    ('5', '[Enroll fingerprint] Registered fingerprint already exists in the fingerprint database'),
    ('6', '[Enroll fingerprint] Cancel registration'),
    ('7', '[Enroll fingerprint] Device busy, unable to register')
]


class CommandToDevice(models.Model):
    _name = 'attendance.command.device'
    _description = 'Attendance Command To Device'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date DESC'

    device_id = fields.Many2one(
        'attendance.device',
        string='Attendance Machine',
        required=True,
        readonly=True,
        ondelete='cascade'
    )
    name = fields.Char(
        string='Command Name',
        readonly=True,
        help="Command name for sending to the device"
    )
    data = fields.Char(
        string='Data Transfer To Device',
        readonly=True,
        help="Data is sent down to the device."
    )
    # This is sensitive information. Therefore, only display basic information.
    data_view = fields.Char(
        string='Data Transfer',
        compute='_compute_data_view',
        help="Data is sent down to the device."
    )
    transfer_time = fields.Datetime(
        string='Transfer Time',
        readonly=True,
        help="The time the command is sent.")
    return_time = fields.Datetime(
        string='Return Time',
        readonly=True,
        help="Feedback time of the command"
    )
    return_value = fields.Char(
        string='Return Value Code',
        readonly=True,
        help="Feedback value of the command from the device"
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('error', 'Error'),
        ('done', 'Done')],
        string='Status',
        required=True,
        copy=False,
        readonly=True,
        default='draft',
        help="When the record is created, the status is 'Draft'.\n"
            "When a record is sent, the status is 'Pending'.\n"
            "When the status is returned as completed, the status is 'completed'.\n"
            "When the status sent is error, the status is 'Error'."
    )
    number = fields.Integer(
        string='Number',
        compute='_compute_number',
        store=True,
        help="Order number of the sent command"
    )
    description = fields.Selection(
        code_description,
        string='Description Code',
        compute='_compute_description',
        store=True
    )

    @api.depends('name')
    def _compute_number(self):
        num = self.env['attendance.command.device'].search([('state', '=', 'draft')])
        for r in self:
            num_device = num.filtered(lambda d: d.device_id == r.device_id).mapped('number')
            if num_device:
                r.number = max(num_device) + 1
            else:
                r.number = 1

    def _compute_data_view(self):
        for r in self:
            if r.data:
                pin = re.search(r'PIN=([^\t]+)', r.data)
                if pin:
                    r.data_view = 'PIN = {} \t'.format(pin.group(1))

                name = re.search(r'Name=([^\t]+)', r.data)
                if name:
                    r.data_view += 'Name = {}'.format(name.group(1))
            else:
                r.data_view = r.data

    @api.depends('return_value')
    def _compute_description(self):
        description = self.env['attendance.command.device']._fields['description'].get_values(self.env)
        for r in self:
            if r.return_value in description:
                r.description = r.return_value
            else:
                r.description = 'n/a'
