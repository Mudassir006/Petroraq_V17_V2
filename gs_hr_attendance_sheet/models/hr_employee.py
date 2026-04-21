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
import pandas as pd


_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    """
    """
    # region [Initial]
    _inherit = 'hr.employee'
    # endregion [Initial]

    # region [Fields]

    compute_attendance = fields.Boolean(string="Check Attendance")

    # endregion [Fields]

