# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    'name': "Account_invoice_line_date",
    'summary': """
This module adds fields in account invoice line views, begining date of invoice and end of it""",
    'author': "Calyx Servicios S.A.",
    "maintainers": ["Lolstalgia"],
    'website': "http://www.calyxservicios.com.ar",
    "license": "AGPL-3",	
    'category': 'Tools',
    "version": "11.0.1.0.0",
    'depends': ['account', 'account_extension', 'sale'],
    'data': [
        "views/invoice_analysis.xml"
    ],
}
