from odoo import models, api


class AccountInvoiceRefund(models.TransientModel):
    """Credit Notes"""
    _inherit = "account.invoice.refund"

    @api.multi
    def compute_refund(self, mode='refund'):
        # Saving the currency_rate of current invoice
        currency_rate = self.invoice_id.currency_rate

        # When the method compute_refund is executed, it gets the current currency rate
        res = super().compute_refund(mode=mode)

        # We look for the credit note created id, and modify the currency rate to the one we saved
        refund = self.env['account.invoice'].browse(res['domain'][1][2][0])
        refund.update({
            'computed_currency_rate': currency_rate,
            'currency_rate': currency_rate
        })
        return res
