# -*- coding: utf-8 -*-
{
    'name': "Petroraq HR Recruitment",

    'summary': """
        This Module is created to manage hr recruitment""",

    'description': """
    """,

    'author': "Mahmoud Salah",
    'company': "Petroraq",
    'website': "https://webmail.petroraq.com/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Human Resources/Employees/Recruitment',
    'version': '17.0.1.0.0',
    # any module necessary for this one to work correctly
    'depends': ['pr_hr_account', 'website_hr_recruitment', 'de_hr_workspace', 'mail'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/hr_job.xml',
        'views/website_hr_recruitment_detail.xml',
        'views/hr_job_approvals.xml',
        'views/hr_applicant_onboarding.xml',
        'views/hr_applicant.xml',
        'views/hr_work_permit.xml',
        'views/hr_work_permit_approvals.xml',
        'views/bank_payment.xml',
        'data/ir_cron.xml',
    ],
    # only loaded in demonstration mode
    'demo': [],
    # 'assets': {}
}
