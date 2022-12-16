# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    'name': 'Customer Follow Up Amount for multi-company',
    'summary': """
        This module fixes the amount of total due for multi-companies in the "Payment follow-up" tab.
    """,
    'author': 'Calyx Servicios S.A.',
    'maintainers': ['Zamora, Javier'],
    'website': 'https://odoo.calyx-cloud.com.ar/',
    'license': 'AGPL-3',
    'category': 'Accounting',
    'version': '13.0.1.0.0',
    'development_status': 'Production/Stable',
    'application': False,
    'installable': True,
    'depends': ['om_account_followup',],
    'data': [],
}