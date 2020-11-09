##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
import re
import logging
_logger = logging.getLogger(__name__)



class AccountInvoice(models.Model):
	_inherit = "account.invoice"

	@api.depends('origin')
	def _get_sale_order(self):
	    self.sale_id = self.env['sale.order'].search([('name', '=', self.origin)])

	sale_id = fields.Many2one('sale.order', string='Sale Orders', readonly=True, compute='_get_sale_order')

