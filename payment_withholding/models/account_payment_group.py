from odoo import models, _

class AccountPaymentGroup(models.Model):
    _inherit = "account.payment.group"

    def compute_withholdings(self):
        for rec in self:
            if rec.partner_type != 'supplier':
                continue

            for move in rec.to_pay_move_line_ids:
                if move.move_id.l10n_latam_document_type_id.doc_code_prefix not in ['FA-M', 'ND-M', 'NC-M']:
                    super(AccountPaymentGroup, self).compute_withholdings()

                income_tax_withholding = self.env.ref('payment_withholding.income_tax_withholding').id
                vat_withholding = self.env.ref('payment_withholding.vat_withholding').id

                withholding_ganancias = move.move_id.amount_untaxed * 0.06
                withholding_iva = move.move_id.amount_tax

                payment_withholding_ganancias = self.env['account.payment'].search([
                    ('payment_group_id', '=', rec.id),
                    ('tax_withholding_id', '=', income_tax_withholding),
                    ('automatic', '=', True),
                ], limit=1)

                payment_withholding_iva = self.env['account.payment'].search([
                    ('payment_group_id', '=', rec.id),
                    ('tax_withholding_id', '=', vat_withholding),
                    ('automatic', '=', True),
                ], limit=1)

                if withholding_ganancias:
                    if payment_withholding_ganancias:
                        payment_withholding_ganancias.write({
                            'amount': withholding_ganancias,
                        })
                    else:
                        vals = {
                            'payment_group_id': rec.id,
                            'tax_withholding_id': income_tax_withholding,
                            'automatic': True,
                            'amount': withholding_ganancias,
                        }
                        self.env['account.payment'].create(vals)

                if withholding_iva:
                    if payment_withholding_iva:
                        payment_withholding_iva.write({
                            'amount': withholding_iva,
                        })
                    else:
                        vals = {
                            'payment_group_id': rec.id,
                            'tax_withholding_id': vat_withholding,
                            'automatic': True,
                            'amount': withholding_iva,
                        }
                        self.env['account.payment'].create(vals)

        return True
