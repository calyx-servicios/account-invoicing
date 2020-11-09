# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    @api.onchange("account_analytic_id")
    def _onchange_account_analytic_id(self):
        """
            Set the analytic tags based in analytic account
        """
        for record in self:
            tag_ids = []
            acc_analytic = record.account_analytic_id
            if record.invoice_id.type in ("in_invoice", "in_refund"):
                if acc_analytic:
                    for tag in acc_analytic.tag_ids:
                        tag_ids.append(tag.id)
                    record.analytic_tag_ids = [(6, 0, tag_ids)]
