# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    'name': "Account Invoice Description",
    'summary': """
This module add a field in account invoice tree view, description """,
    'author': "Calyx Servicios S.A.",
    "maintainers": ["Lolstalgia"],
    'website': "http://www.calyxservicios.com.ar",
    "license": "AGPL-3",	
    'category': 'Tools',
    "version": "11.0.1.0.0",
    'depends': ['account', 'account_extension', 'sale'],
    'data': [
        "views/sale_order_view.xml",
        "views/account_invoice_view.xml"
    ],
}
