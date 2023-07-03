from odoo import models, _


class AccountPaymentGroup(models.Model):
    _inherit = "account.payment.group"


    def compute_withholdings(self):
        for rec in self:
            if rec.partner_type != 'supplier':
                continue

            withholding_totals = {}

            for move in rec.to_pay_move_line_ids:
                if move.move_id.l10n_latam_document_type_id.doc_code_prefix not in ['FA-M', 'ND-M', 'NC-M']:
                    super(AccountPaymentGroup, self).compute_withholdings()

                income_tax_withholding = self.env.ref('payment_withholding.income_tax_withholding').id
                vat_withholding = self.env.ref('payment_withholding.vat_withholding').id

                withholding_ganancias = move.move_id.amount_untaxed * 0.06
                withholding_iva = move.move_id.amount_tax

                if withholding_ganancias:
                    if income_tax_withholding in withholding_totals:
                        withholding_totals[income_tax_withholding] += withholding_ganancias
                    else:
                        withholding_totals[income_tax_withholding] = withholding_ganancias

                if withholding_iva:
                    if vat_withholding in withholding_totals:
                        withholding_totals[vat_withholding] += withholding_iva
                    else:
                        withholding_totals[vat_withholding] = withholding_iva

            for withholding_id, amount in withholding_totals.items():
                payment_withholding = self.env['account.payment'].search([
                    ('payment_group_id', '=', rec.id),
                    ('tax_withholding_id', '=', withholding_id),
                    ('automatic', '=', True),
                ], limit=1)

                if payment_withholding:
                    payment_withholding.write({
                        'amount': amount,
                    })
                else:
                    vals = {
                        'payment_group_id': rec.id,
                        'tax_withholding_id': withholding_id,
                        'automatic': True,
                        'amount': amount,
                    }
                    self.env['account.payment'].create(vals)

        return True
