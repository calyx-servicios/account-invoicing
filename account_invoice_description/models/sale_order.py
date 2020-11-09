from odoo import fields, models, api


class SaleOrder(models.Model):

    _inherit = "sale.order"

    @api.depends("description")
    def get_description(self):
        for eas in self:
            eas.description = ""
            for rec in eas.order_line:
                eas.description =  eas.description + rec.name + "\n"

    description = fields.Text(string="Description", compute="get_description")