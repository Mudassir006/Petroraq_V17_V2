# -*- coding: utf-8 -*-
{
    'name': "Petroraq Tax Invoice Report",
    'author': "Mahmoud Salah",
    'website': "http://www.petroraq.com",
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['l10n_sa'],
    'assets': {
        'web.report_assets.common': [
            '/tax_Invoice_report/static/src/scss/custom_font.scss'
        ]
    },

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'report/invoice_report_header.xml',
        'report/report_action.xml',
        'report/report_action_temp.xml',
        'views/views.xml',
    ],
}
