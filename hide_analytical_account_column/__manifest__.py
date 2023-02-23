{
    'name': 'Hide Analytic Account Column',
    'summary': """Hide Analytic Account Column""",
    'author': 'Calyx Servicios S.A.',
    "maintainers": ["Georgina Guzman"],
    'website': 'https://odoo.calyx-cloud.com.ar',
    'category': 'Tools',
    'version': '11.0.1.0.0',
    'development_status': 'Production/Stable',
    'application': False,
    'installable': True,
    'depends': [
        'account',
    ],
    'data': [
        'views/account_view.xml',
    ],
}
