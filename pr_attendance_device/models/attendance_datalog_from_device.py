from odoo import models, fields, api

code_description = [
    ('-1', 'N/A'),
    ('0', 'Power On'),
    ('1', 'Power Off'),
    ('2', 'Authentication Failure'),
    ('3', 'Alarm'),
    ('4', 'Enter Menu'),
    ('5', 'Change Settings'),
    ('6', 'Enroll Fingerprint'),
    ('7', 'Enroll Password'),
    ('8', 'Enroll HID Card'),
    ('9', 'Delete User'),
    ('10', 'Delete Fingerprint'),
    ('11', 'Delete Password'),
    ('12', 'Delete RF Card'),
    ('13', 'Clear Data'),
    ('14', 'Create MF Card'),
    ('15', 'Enroll MF Card'),
    ('16', 'Register MF Card'),
    ('17', 'Delete MF Card Registration'),
    ('18', 'Clear MF Card Content'),
    ('19', 'Move Enrollment Data to Card'),
    ('20', 'Copy Data from Card to Machine'),
    ('21', 'Set Time'),
    ('22', 'Factory Reset'),
    ('23', 'Delete Entry/Exit Records'),
    ('24', 'Clear Administrator Permissions'),
    ('25', 'Modify Access Group Settings'),
    ('26', 'Modify User Access Settings'),
    ('27', 'Modify Access Time Zones'),
    ('28', 'Modify Unlocking Combination Settings'),
    ('29', 'Unlock'),
    ('30', 'Enroll New User'),
    ('31', 'Change Fingerprint Properties'),
    ('32', 'Forced Alarm'),
    ('33', 'Doorbell Call'),
    ('34', 'Anti-submarine'),
    ('35', 'Delete Attendance Photo'),
    ('36', 'Modify User Other Information'),
    ('37', 'Holiday'),
    ('38', 'Restore Data'),
    ('39', 'Backup Data'),
    ('40', 'Device Disk Upload'),
    ('41', 'Device Disk Download'),
    ('42', 'Device Disk Attendance Record Encryption'),
    ('43', 'Device Disk Download Success and Delete Records'),
    ('53', 'Door Opening Switch'),
    ('54', 'Door Magnetic'),
    ('55', 'Alarm'),
    ('56', 'Restore Parameters'),
    ('68', 'Register User Photo'),
    ('69', 'Modify User Photo'),
    ('70', 'Modify User Name'),
    ('71', 'Modify User Permissions'),
    ('76', 'Modify Network Settings IP'),
    ('77', 'Modify Network Settings Subnet Mask'),
    ('78', 'Modify Network Settings Gateway'),
    ('79', 'Modify Network Settings DNS'),
    ('80', 'Modify Connection Settings Password'),
    ('81', 'Modify Connection Settings Device ID'),
    ('82', 'Modify Cloud Server Address'),
    ('83', 'Modify Cloud Server Port'),
    ('87', 'Modify Access Control Record Settings'),
    ('88', 'Modify Face Parameter Flag'),
    ('89', 'Modify Fingerprint Parameter Flag'),
    ('90', 'Modify Finger Vein Parameter Flag'),
    ('91', 'Modify Palm Print Parameter Flag'),
    ('92', 'Device Disk Upgrade Flag'),
    ('100', 'Modify RF Card Information'),
    ('101', 'Enroll Face'),
    ('102', 'Modify Personnel Permissions'),
    ('103', 'Delete Personnel Permissions'),
    ('104', 'Add Personnel Permissions'),
    ('105', 'Delete Access Control Records'),
    ('106', 'Delete Face'),
    ('107', 'Delete Personnel Photo'),
    ('108', 'Modify Parameters'),
    ('109', 'Select WIFISSID'),
    ('110', 'Enable Proxy'),
    ('111', 'Modify Proxy IP'),
    ('112', 'Modify Proxy Port'),
    ('113', 'Modify Personnel Password'),
    ('114', 'Modify Face Information'),
    ('115', 'Modify Operator Password'),
    ('116', 'Restore Access Control Settings'),
    ('117', 'Operator Password Input Error'),
    ('118', 'Operator Password Lock'),
    ('120', 'Modify Legic Card Data Length'),
    ('121', 'Enroll Palm Vein'),
    ('122', 'Modify Palm Vein'),
    ('123', 'Delete Palm Vein'),
    ('124', 'Enroll Palm Print'),
    ('125', 'Modify Palm Print'),
    ('126', 'Delete Palm Print')
]


class DataLogDevice(models.Model):
    _name = 'attendance.data.log.device'
    _description = 'Data Log On Device'
    _order = 'op_time DESC'

    device_id = fields.Many2one(
        'attendance.device',
        string='Attendance Machine',
        required=True,
        readonly=True,
        ondelete='cascade'
    )
    op_type = fields.Char(
        string='Log Code',
        readonly=True,
        help="Log code sent from the device"
    )
    description = fields.Selection(
        code_description,
        string='Description Log Code',
        compute='_compute_description',
        store=True,
    )
    op_who = fields.Char(
        string='Operator',
        readonly=True,
        help="The value in the error code table."
        "Refer to the manufacturer's user guide documentation for more details."
    )
    op_time = fields.Datetime(
        string='Created On',
        readonly=True,
        help="Device log recording time."
    )
    # TODO: lack documentation for these 'value' field because the doc is already poor (Said author Trung Tuan)
    value_1 = fields.Char(
        string='Value 1',
        readonly=True,
        help="The value in the error code table."
        "Refer to the manufacturer's user guide documentation for more details."
    )
    value_2 = fields.Char(
        string='Value 2',
        readonly=True,
        help="The value in the error code table."
        "Refer to the manufacturer's user guide documentation for more details."
    )
    value_3 = fields.Char(
        string='Value 3',
        readonly=True,
        help="The value in the error code table."
        "Refer to the manufacturer's user guide documentation for more details."
    )
    reserved = fields.Char(
        string='Reserved',
        readonly=True,
        help="The value in the error code table."
        "Refer to the manufacturer's user guide documentation for more details."
    )

    @api.depends('op_type')
    def _compute_description(self):
        description = self.env['attendance.data.log.device']._fields['description'].get_values(self.env)
        for r in self:
            if r.op_type in description:
                r.description = r.op_type
            else:
                r.description = '-1'
