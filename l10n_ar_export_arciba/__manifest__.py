# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Export Arciba",
    "summary": """
        This module generates the Arciba file for withholdings, perceptions and credit notes.
    """,
    "author": "Calyx Servicios S.A.",
    "maintainers": ["Zamora, Javier"],
    "website": "http://odoo.calyx-cloud.com.ar/",
    "license": "AGPL-3",
    "category": "Account",
    "version": "15.0.1.3.2",
    "installable": True,
    "application": False,
    "depends": [
        "l10n_ar_ux",
        "account_payment_group",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/export_arciba.xml",
    ],
}
