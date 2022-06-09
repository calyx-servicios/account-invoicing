# pylint: disable=missing-module-docstring,pointless-statement
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Customer Follow Up Management (Fix Blocked mail)",
    "summary": """
        This module fixes the functionality of the om_account_followup module to correct email sending excluding the documents that were marked as blocked (without following).
    """,
    "author": "Calyx Servicios S.A.",
    "maintainers": ["gpperez"],
    "website": "https://odoo.calyx-cloud.com.ar/",
    "license": "AGPL-3",
    "category": "Accounting",
    "version": "13.0.1.0.0",
    "development_status": "Production/Stable",
    "application": False,
    "installable": True,
    "depends": ["om_account_followup"],
}
