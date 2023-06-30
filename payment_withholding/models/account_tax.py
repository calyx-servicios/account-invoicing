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
        for move in payment_group.to_pay_move_line_ids:
            if move.move_id.l10n_latam_document_type_id.doc_code_prefix in ['FA-M', 'ND-M', 'NC-M']:
                journal = self.env['account.journal'].search([
                    ('company_id', '=', move.move_id.company_id.id),
                    ('outbound_payment_method_line_ids.payment_method_id.code', '=', 'withholding'),
                    ('type', 'in', ['cash', 'bank']),
                ], limit=1)
                if not journal:
                    raise UserError(_('No journal for withholdings found on company %s') % move.move_id.company_id.name)

                for config in withholding_config:
                    withholding_amount = move.move_id[config['field_name']] * config['withholding_rate']

                    payment_withholding = self.env['account.payment'].search([
                        ('payment_group_id', '=', payment_group.id),
                        ('tax_withholding_id', '=', config['tax_withholding_id']),
                        ('automatic', '=', True),
                    ], limit=1)

                    if withholding_amount:
                        if payment_withholding:
                            payment_withholding.write({
                                'amount': withholding_amount,
                            })
                        else:
                            payment_method_line_id = journal.outbound_payment_method_line_ids.filtered(
                                lambda x: x.code == 'withholding').mapped('id')[0]

                            vals = {
                                'payment_group_id': payment_group.id,
                                'tax_withholding_id': config['tax_withholding_id'],
                                'automatic': True,
                                'amount': withholding_amount,
                                'journal_id': journal.id,
                                'payment_method_line_id': payment_method_line_id,
                                'payment_type': 'outbound',
                                'partner_type': payment_group.partner_type,
                                'partner_id': payment_group.partner_id.id,
                            }
                            self.env['account.payment'].create(vals)
            else: 
                super().create_payment_withholdings(payment_group)
        
        return True
