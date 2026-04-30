{
    "name": "Petroraq Custom Website",
    "version": "1.0",
    "category": "Website",
    "summary": "Custom full website for Petroraq Engineering built in Odoo.",
    "author": "Mudassir",
    "website": "https://petroraq.com",
    "license": "LGPL-3",

    # Required
    "depends": [
        "website",
        "hr_recruitment",            # for careers page
    ],

    # Data files (XML Views)
    "data": [
        # "views/assets.xml",          # CSS/JS
        "views/layout.xml",          # custom header/footer
        "views/footer.xml",
        "views/hero.xml",
        # "views/assets.xml",
        # "views/home.xml",
        # "views/about.xml",
        # "views/services.xml",
        # "views/projects.xml",
        # "views/careers.xml",
        "views/404.xml",
        # "views/job_detail.xml",
        # "views/contact.xml",
        "views/careers.xml",
        "views/404.xml",
    ],

    # QWeb templates (loaded globally)
    "assets": {
        "web.assets_frontend": [
            "pr_website/static/css/theme.css",
            "pr_website/static/js/theme.js",
        ],
    },

    "application": True,
    "installable": True,
}
