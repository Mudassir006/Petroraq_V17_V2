{
    "name": "Petroraq VAT Summary Report",
    "summary": "Quarter-style VAT Summary (Sales, Vated / Non-Vated Purchases)",
    "version": "17.0.1.0.3",
    "author": "Petroraq Engineering",
    "license": "LGPL-3",
    "depends": ["account", "report_xlsx"],
    "data": [
        "security/ir.model.access.csv",
        "reports/vat_summary_xlsx.xml",
        "views/vat_summary_wizard.xml",
        # "reports/vat_summary_report_templates.xml",
    ],
    "installable": True,
    "application": False,
}
