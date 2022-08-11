# pylint: disable=missing-module-docstring,pointless-statement
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Account Follow Up Templates",
    "summary": """
        This module adds shipping templates in Portuguese and English for Follow up levels.
    """,
    "author": "Calyx Servicios S.A.",
    "maintainers": ["DeykerGil"],
    "website": "https://odoo.calyx-cloud.com.ar/",
    "license": "AGPL-3",
    "category": "Accounting",
    "version": "13.0.1.0.0",
    "development_status": "Production/Stable",
    "application": False,
    "installable": True,
    "depends": ["om_account_followup"],
    'data': [
        'data/data.xml',
    ],
}
