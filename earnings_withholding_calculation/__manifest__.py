# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Earnings Withholding Calculation",
    "summary": """
        This module performs the calculation of 
        earnings withholdings.
    """,
    "author": "Calyx Servicios S.A.",
    "maintainers": ["PerezGabriela"],
    "website": "http://odoo.calyx-cloud.com.ar/",
    "license": "AGPL-3",
    "category": "Account",
    "version": "18.0.1.1.0",
    "installable": False,  # TODO: needs refactoring for Odoo 18
    "application": False,
    "depends": [
        "l10n_ar_withholding",
        "l10n_ar_tax",
    ],
    "data": [
        "data/account_journal.xml",
        "data/account_tax.xml",
        "views/account_payment_group_view.xml"
    ],
}
