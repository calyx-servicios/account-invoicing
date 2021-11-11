from odoo import models,fields,api,_

class AccountMove(models.Model):
    _inherit = "account.move"

    company_country_id = fields.Char(string="Country_id",related='company_id.country_id.code', help='Technical field used to hide/show fields regarding the localization')