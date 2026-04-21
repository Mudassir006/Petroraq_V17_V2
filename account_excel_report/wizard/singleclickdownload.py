# -*- coding: utf-8 -*-
#################################################################################
#
#Copyright (c) 2013-Present IctPack Solutions LTD. (<http://ictpack.com>)
#
#################################################################################


from odoo import models, fields


class SingleClickDownloadXLS(models.TransientModel):
    _name = "single.click.download.xls"
    _description = "Finished"

    file = fields.Binary('File', readonly=True)
    fname = fields.Char('Text')
