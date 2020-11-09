from odoo import fields, models, api


class AccountInvoice(models.Model):

    _inherit = "account.invoice"

    @api.depends("description")
    def get_description(self):
        for eas in self:
            eas.description = ""
            for rec in eas.invoice_line_ids:
                eas.description =  eas.description + rec.name + "\n"

    description = fields.Text(string="Description", compute="get_description")

