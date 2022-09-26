from odoo import fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    sicore_tax_code = fields.Integer(string="Tax code")

