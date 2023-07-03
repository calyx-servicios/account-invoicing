from odoo import models, _
from odoo.exceptions import UserError


class AccountTax(models.Model):
    _inherit = "account.tax"


    def create_payment_withholdings(self, payment_group):
        withholding_config = [
            {
                'tax_withholding_id': self.env.ref('payment_withholding.income_tax_withholding').id,
                'field_name': 'amount_untaxed',
                'withholding_rate': 0.06,
            },
            {
                'tax_withholding_id': self.env.ref('payment_withholding.vat_withholding').id,
                'field_name': 'amount_tax',
                'withholding_rate': 1.0,
            },
        ]

        withholding_totals = {}

        for move in payment_group.to_pay_move_line_ids:
            if move.move_id.l10n_latam_document_type_id.doc_code_prefix in ['FA-M', 'ND-M', 'NC-M']:
                for config in withholding_config:
                    withholding_amount = move.move_id[config['field_name']] * config['withholding_rate']

                    if withholding_amount:
                        tax_withholding_id = config['tax_withholding_id']
                        if tax_withholding_id in withholding_totals:
                            withholding_totals[tax_withholding_id] += withholding_amount
                        else:
                            withholding_totals[tax_withholding_id] = withholding_amount

        for tax_withholding_id, amount in withholding_totals.items():
            payment_withholding = self.env['account.payment'].search([
                ('payment_group_id', '=', payment_group.id),
                ('tax_withholding_id', '=', tax_withholding_id),
                ('automatic', '=', True),
            ], limit=1)

            if payment_withholding:
                payment_withholding.write({
                    'amount': amount,
                })
            else:
                move = payment_group.to_pay_move_line_ids[0].move_id
                journal = self.env['account.journal'].search([
                    ('company_id', '=', move.company_id.id),
                    ('outbound_payment_method_line_ids.payment_method_id.code', '=', 'withholding'),
                    ('type', 'in', ['cash', 'bank']),
                ], limit=1)

                if not journal:
                    raise UserError(_('No journal for withholdings found on company %s') % move.company_id.name)

                payment_method_line_id = journal.outbound_payment_method_line_ids.filtered(
                    lambda x: x.code == 'withholding').mapped('id')[0]

                vals = {
                    'payment_group_id': payment_group.id,
                    'tax_withholding_id': tax_withholding_id,
                    'automatic': True,
                    'amount': amount,
                    'journal_id': journal.id,
                    'payment_method_line_id': payment_method_line_id,
                    'payment_type': 'outbound',
                    'partner_type': payment_group.partner_type,
                    'partner_id': payment_group.partner_id.id,
                }
                self.env['account.payment'].create(vals)

        return True
