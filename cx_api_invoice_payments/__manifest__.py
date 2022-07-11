# pylint: disable=missing-module-docstring,pointless-statement
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Calyx Services Invoice Payments API",
    "summary": """
        This module allows to integrate external services to create Invoices and Payments into Odoo.
    """,
    "author": "Calyx Servicios S.A.",
    "maintainers": ["FedericoGregori"],
    "website": "https://odoo.calyx-cloud.com.ar/",
    "license": "AGPL-3",
    "category": "Accounting",
    "version": "13.0.1.0.0",
    "development_status": "Production/Stable",
    "application": False,
    "installable": True,
    "depends": ["base", "account", "auth_jwt", "l10n_ar", "account_payment_group"],
    "data": [
        "data/res_users_data.xml",
        "data/auth_jwt_validators.xml",
    ],
}
