# -*- coding: utf-8 -*-
{
    'name': "l10n_ar_arca_transparencia_fiscal",
    'summary': """
    """,
    'author': "Calyx Servicios S.A",
    "maintainers": ["estebansam21", "enzogonzalezdev"],
    "website": "https://odoo.calyx-cloud.com.ar/",
    "license": "AGPL-3",
    "category": "Account",
    "version": "11.0.1.0.0",
    "application": False,
    'depends': [
            'account',
            'l10n_ar_aeroo_einvoice',
            'account_invoice_custom_report'
        ],
    'data': [
        # 'views/res_config_settings.xml',
        'views/report_invoice.xml',
        'views/report_action.xml',
        'data/account_tax_group_data.xml'
    ],
}
