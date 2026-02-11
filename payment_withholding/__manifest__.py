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
    "version": "18.0.2.1.0",
    "development_status": "Production/Stable",
    "application": False,
    "installable": False,  # TODO: needs refactoring for Odoo 18
    "depends": [
        'l10n_ar_withholding',
        'l10n_ar_tax',
        'account_payment_group',
    ],
    "data": [
        'data/tax_withholding.xml',
        'views/account_tax.xml',
    ],
}
