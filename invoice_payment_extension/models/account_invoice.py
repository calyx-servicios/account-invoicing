from odoo import models, api, _


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.model
    def _get_payments_vals(self):
        account_move_line_obj = self.env['account.move.line']
        payment_vals = super()._get_payments_vals()
        for payment in payment_vals:
            payment_line = account_move_line_obj.browse(payment['payment_id'])
            payment['display_name'] = payment_line.display_name
        return payment_vals