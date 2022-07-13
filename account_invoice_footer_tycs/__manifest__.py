{

    "name": "Invoice Footer TyC",
    "summary": """
        This module adds TyC to the footer, between qr and CAE info 
    """,
    "author": "Calyx Servicios S.A.",
    "maintainers": ["ParadisoCristian", "DeykerGil"],
    "website": "https://odoo.calyx-cloud.com.ar/",
    "license": "AGPL-3",
    "version": "13.0.1.0.0",
    "depends": ["l10n_ar_edi"],
    'data': [
        'views/report_invoice.xml',
    ],
}
