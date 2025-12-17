# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.tools.misc import formatLang



class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    def get_tax_detail_ar(self):
        involved_tax_group_ids = []
        for line in self.tax_line_ids:
            involved_tax_group_ids.append(line.tax_id.tax_group_id.id)
        involved_tax_groups = self.env['account.tax.group'].browse(involved_tax_group_ids)
        nat_tax_groups = involved_tax_groups.filtered(lambda tax_group: tax_group.afip_code in (1, 4))
        vat_tax_groups = involved_tax_groups.filtered(lambda tax_group: tax_group.afip_code != 0)

        # RG 5614/2024: Show ARCA VAT and Other National Internal Taxes
        if self.journal_document_type_id.document_type_id.code in ['6', '7', '8']:
            # Prepare the subtotals to show in the report
            currency_symbol = self.currency_id.symbol
            detail_info = {}

            for line in self.tax_line_ids:
                if line.tax_id.tax_group_id in nat_tax_groups:
                    key = 'other_taxes'
                    name = _("Other National Ind. Taxes %s") % currency_symbol
                elif line.tax_id.tax_group_id in vat_tax_groups:
                    key = 'vat_taxes'
                    name = _("VAT Content %s") % currency_symbol
                else:
                    continue

                if key not in detail_info:
                    if line.amount_total != 0.0:
                        detail_info[key] = {"name": name, "tax_amount": line.amount_total}
                else:
                    detail_info[key]["tax_amount"] += line.amount_total

            # Format the amounts to show in the report
            for _item, values in detail_info.items():
                values["formatted_amount_tax"] = formatLang(self.env, values["tax_amount"])

            return list(detail_info.values())

