{
    "name": "Payment Witholding",
    "summary": """
        This module  Automates tax withholdings on M-type documents for income taxes.
    """,
    "author": "Calyx Servicios S.A.",
    "maintainers": ["Zamora, Javier"],
    "website": "https://odoo.calyx-cloud.com.ar/",
    "license": "AGPL-3",
    "category": "Purchase",
    "version": "15.0.2.0.0",
    "development_status": "Production/Stable",
    "application": False,
    "installable": True,
    "depends": [
        'account_withholding_automatic',
        'account_payment_group',
    ],
    "data": [
        'data/tax_withholding.xml',
        'views/account_tax.xml',
    ],
}
