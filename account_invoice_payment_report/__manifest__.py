# coding: utf-8
# Copyright 2018 Eficent Business and IT Consulting Services S.L.
#   (http://www.eficent.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    'name': 'Account Invoice Payment Report',
    'version': '11.0.1.0.0',
    'category': 'Account',
    'summary': ' ',
    'author': "Calyx, Odoo Community Association (OCA)",
    'website': 'https://www.calyxservicios.com.ar',
    'license': 'AGPL-3',
    'depends': [
        'report_xlsx'
    ],
    'data': [
        'wizard/invoice_payment_report_wizard.xml',
        'reports/invoice_payment_report_action.xml'
    ],
    'installable': True,
    'application': False,
}
