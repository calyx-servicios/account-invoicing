from odoo import models, fields, _


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    agreement = fields.Integer(string='Agreement')