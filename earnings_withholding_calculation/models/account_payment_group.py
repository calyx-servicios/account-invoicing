from odoo import models, _


class AccountPaymentGroup(models.Model):
    _inherit = 'account.payment.group'
    
    def compute_earnings_withholding(self):
        if self.partner_id and self.partner_id.imp_ganancias_padron:
            if self.partner_id.imp_ganancias_padron not in ["EX", "NC"]:
                regimen_ganancias = self.partner_id.default_regimen_ganancias_id
                if self.partner_id.imp_ganancias_padron == "AC":
                    percentage = regimen_ganancias.porcentaje_inscripto
                elif self.partner_id.imp_ganancias_padron == "NI":
                    percentage = regimen_ganancias.porcentaje_no_inscripto
                else:
                    percentage = -1.0
                
                pay_amount = self.to_pay_amount - regimen_ganancias.montos_no_sujetos_a_retencion
                if percentage != -1.00:
                    amount = (pay_amount * percentage) / 100
                else:
                    withholding = self.env["afip.tabla_ganancias.escala"].search([("importe_desde", "<", pay_amount),("importe_hasta", ">", pay_amount)])
                    diff_pay = pay_amount - withholding.importe_excedente
                    amount_percentage = (diff_pay * withholding.porcentaje) / 100
                    amount = withholding.importe_fijo + amount_percentage

                vals = {
                    "journal_id": self.env.ref("earnings_withholding_calculation.earnings_withholding").id,
                    "amount": amount,
                    "tax_withholding_id": self.env.ref("earnings_withholding_calculation.tax_earnings_withholding").id,
                    "withholding_base_amount": pay_amount,
                    "payment_group_id": self.id,
                    "payment_type": 'outbound',
                    "payment_method_id": self.env.ref("account_withholding.account_payment_method_out_withholding").id,
                    "payment_method_line_id": self.env.ref("earnings_withholding_calculation.payment_method_line_out_withholding").id,
                    "payment_method_description": _("Withholding")
                }
                self.env["account.payment"].create(vals)

