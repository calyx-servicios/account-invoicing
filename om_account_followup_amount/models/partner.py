from odoo import models, fields

class ResPartner(models.Model):
    _inherit = "res.partner"

    def _get_amounts_and_date(self):
        company = self.env.company
        current_date = fields.Date.today()
        for partner in self:
            worst_due_date = False
            amount_due = amount_overdue = 0.0
            for aml in partner.unreconciled_aml_ids:
                if (aml.company_id == company):
                    date_maturity = aml.date_maturity or aml.date
                    if not worst_due_date or date_maturity < worst_due_date:
                        worst_due_date = date_maturity
                    amount_due += aml.result
                    if (date_maturity <= current_date):
                        amount_overdue += aml.result
            partner.payment_amount_due = amount_due
            partner.payment_amount_overdue = amount_overdue
            partner.payment_earliest_due_date = worst_due_date