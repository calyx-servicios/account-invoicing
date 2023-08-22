# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Export ARBA",
    "summary": """
        This module generates the ARBA file for 
        withholdings and perceptions.
    """,
    "author": "Calyx Servicios S.A.",
    "maintainers": ["PerezGabriela"],
    "website": "http://odoo.calyx-cloud.com.ar/",
    "license": "AGPL-3",
    "category": "Account",
    "version": "13.0.2.0.0",
    "installable": True,
    "application": False,
    "depends": [
        "l10n_ar_ux",
        "account_payment_group",
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/account_view.xml',
    ],
}
