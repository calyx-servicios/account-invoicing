# coding: utf-8
from datetime import datetime
from odoo import models, fields, api


class AccountInvoicePaymentReportWizard(models.TransientModel):
    _name = 'account.invoice.payment.report.wizard'

    date_from = fields.Date(
        string="From", required=True, default=datetime.now().strftime('%m 01 %Y'))
    date_to = fields.Date(
        string="To", required=True, default=fields.Date.today)

    @api.multi
    def generate_xls_report(self):
        self.ensure_one()

        data = self.read()[0]
        report = self.env.ref(
            'account_invoice_payment_report.invoice_payment_report_action')
        return report.report_action(self, data=data)
