from odoo import api, fields, models, _
from odoo.tools.safe_eval import safe_eval
from odoo.tools import pycompat
from odoo.exceptions import UserError, ValidationError
import datetime

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.multi
    @api.onchange('journal_id', 'partner_id', 'company_id')
    def onchange_available_journal_document_types(self):
        res = super(AccountInvoice, self).onchange_available_journal_document_types()
        default_journal_document_type_id = self._context.get('default_journal_document_type_id', False)
        if default_journal_document_type_id:
            self.journal_document_type_id = default_journal_document_type_id
    
    # CAMPO PARA SABER SI EL INVOICE TIENE AL MENOS UNA CUOTA VENCIDA
    account_due_calc = fields.Boolean(string="Existen deudas vencidas?", compute="_compute_dates_dues", store=True)
    @api.one
    def _compute_dates_dues(self):
        d = datetime.datetime.now().date()
        related_recordset = self.env['account.move.line'].search([('invoice_id', '=', self.id), ('amount_residual','!=',0), ('date_maturity','<', d)])
        if related_recordset:
            self.account_due_calc = True
        else:
            self.account_due_calc = False

class InvoiceInterestDue(models.Model):
    _inherit = 'account.move.line'

    # SE DEBE PROBAR OTRA MANERA DE MOSTRAR EL NOMBRE
    # SE MOSTRARA LA FECHA DE VENCIMIENTO DEL APUNTE CONTABLE EN LUGAR DEL NOMBRE DEL ASIENTO
    # SI NO TIENE REPERCUSION EN OTRO MODELO SE DEJARA DE ESA MANERA
    @api.multi
    def name_get(self):
        result = []
        for record in self:
            # if self.env.context.get('invoice_account_interest', False):
            #     name = str(record.move_id.name)
            #     result.append((record.id,"{}".format(name)))
            # else:
            date_expired = datetime.datetime.strptime(record.date_maturity,'%Y-%m-%d').strftime('%d/%m/%y')
            due_expired = str(date_expired)
            result.append((record.id, due_expired))
        return result