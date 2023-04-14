# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Account Invoice Custom Report",
    "summary": """
        This module adds the agreement field and also adds them to the report.
    """,
    "author": "Calyx Servicios S.A.",
    "maintainers": ["Zamora, Javier"],
    "website": "http://odoo.calyx-cloud.com.ar/",
    "license": "AGPL-3",
    "category": "Technical Settings",
    "version": "11.0.1.0.0",
    "application": False,
    "installable": True,
    "depends": [
        "l10n_ar_aeroo_einvoice",
        "account_invoicing",
    ],
    "data": [
        "views/account_invoice.xml",
        "report/report.xml",
    ],
}
