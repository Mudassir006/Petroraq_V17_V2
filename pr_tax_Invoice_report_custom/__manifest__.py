# -*- coding: utf-8 -*-
{
    'name': "Petroraq Tax Invoice Report Custom",
    'author': "Petroraq",
    'website': "http://www.petroraq.com",
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['l10n_sa', 'pr_base','petroraq_sale_workflow','petro_retention'],
    'assets': {
        'web.report_assets.common': [
            '/pr_tax_Invoice_report_custom/static/src/scss/custom_font.scss'
        ]
    },

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        # 'report/invoice_report_header.xml',
        # 'report/report_action.xml',
        # 'report/report_action_temp.xml',
        'report/custom_invoice.xml',
        'report/custom_invoice_header_footer.xml',
        'views/views.xml',
        'data/custom_mail.xml',

    ],
}
