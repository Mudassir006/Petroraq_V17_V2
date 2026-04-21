# -*- coding: utf-8 -*-
{
    'name': "Payroll Workspace - Self Service",
    'summary': """
        Self-Service Payroll
    """,
    'description': """
        The Self-Service Payroll Requests 
    """,
    'author': 'Dynexcel',
    'website': 'https://www.dynexcel.com',
    'version': '0.1',
    'category': 'Human Resources',

    # any module necessary for this one to work correctly
    'depends': ['de_hr_workspace','pr_hr_payroll'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/hr_payslip_views.xml',
        'views/hr_payslip_run.xml',
        'views/hr_payslip_portal.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'license': 'LGPL-3',
    'images': ['static/description/banner.jpg'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
