##############################################################################
#
#    Copyright (C) 2020 Calyx Servicios S.A. (https://odoo.calyx-cloud.com.ar)
#    All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Account Invoice Line Origin',
    'summary': """Adds origin field in account invoice line views.""",
    'author': 'Calyx Servicios S.A.',
    'website': 'https://odoo.calyx-cloud.com.ar',
    'category': 'Tools',
    'version': '11.0.1.0.0',
    'development_status': 'Production/Stable',
    'application': False,
    'installable': True,
    'depends': [
        'account',
        'account_extension',
        'sale',
    ],
    'data': [
        'views/invoice_analysis.xml',
    ],
}
