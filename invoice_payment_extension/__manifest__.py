# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Invoice Payment Report",
    "summary": """
        This module adds payments name in the report.
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
        "account_invoicing",
    ],
    "data": [
        "views/report_invoice.xml",
    ],
}
