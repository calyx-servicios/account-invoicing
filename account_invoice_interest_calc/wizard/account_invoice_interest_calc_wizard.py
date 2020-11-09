from odoo import api, fields, models, _
from odoo.tools.safe_eval import safe_eval
from odoo.tools import pycompat
from odoo.exceptions import UserError, ValidationError
import datetime
import logging
_logger = logging.getLogger(__name__)

# mapping invoice type to journal type
TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale',
    'in_refund': 'purchase',
}
class InvoiceInterestCalcWizard(models.TransientModel):

    _name = "account.invoice.interest.calc.wizard"
    _description = "Account Invoice Calculator Wizard"
    
    @api.onchange('multi')
    def _onchange_multi(self):
        invoices = self.env['account.invoice'].browse(self._context.get('active_ids'))
        partners = invoices.mapped('partner_id')
        for partner in partners:
            self.partner_id = partner.id
            self.partner_id = False

    @api.model
    def _default_journal(self):
        if self._context.get('default_journal_id', False):
            return self.env['account.journal'].browse(self._context.get('default_journal_id'))
        inv_type = self._context.get('type', 'out_invoice')
        inv_types = inv_type if isinstance(inv_type, list) else [inv_type]
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        domain = [
            ('type', 'in', [TYPE2JOURNAL[ty] for ty in inv_types if ty in TYPE2JOURNAL]),
            ('company_id', '=', company_id),
        ]
        return self.env['account.journal'].search(domain, limit=1)

    interest = fields.Float(
        string='Interest',
        default=5,
        required=True)
    period = fields.Selection(
        selection=[(1, 'Daily'), (30, 'Monthly'), (360, 'Annual')],
        required=True,
        string='Period',
        default=30)
    date = fields.Date(string='Date', default=lambda s: fields.Date.context_today(s))
    partner_id = fields.Many2one('res.partner', string="Customer")
    invoice_ids = fields.Many2many('account.invoice', string="Invoices", required="True")
    # journal_id = fields.Many2one('account.journal', string="Journal", required="True")
    journal_id = fields.Many2one('account.journal', string='Journal',
        required=True,
        default=_default_journal,
        domain="[('type', 'in', ['sale'])]")
    multi = fields.Boolean()
    account_interest_calc_details_ids = fields.One2many('account.interest.calc.details.wizard', 'account_invoice_interest_calc_id', string="Invoice Lines")

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        # SE HIZO UN CAMBIO PARA TOMAR LOS INVOICES DESDE OTRO OBJETO
        # self.invoice_ids = False
        # self.invoice_ids = self.env['account.invoice'].search([('partner_id', '=', self.partner_id.id), ('type','=','out_invoice'), ('state','=','open'), ('date_due', '<', self.date)]
        # NUEVO OBJETO 27/01
        # self.account_interest_calc_details_ids = False
        # SI HAY CONTEXTO ES PORQUE LAS FACTURAS VIENEN DEL TREE
        invoices = self.env['account.invoice'].browse(self._context.get('active_ids'))
        if not invoices:
            self.account_interest_calc_details_ids = False
            invoices = self.env['account.invoice'].search([('account_due_calc', '=', True),('partner_id', '=', self.partner_id.id), ('type','=','out_invoice'), ('state','=','open')])
        new_lines = self.env['account.interest.calc.details.wizard']
        d = datetime.datetime.now().date()
        for invoice in invoices:
            # SE BUCAN LAS CUOTAS DE LAS FACTURAS
            invoice_dues = self.env['account.move.line'].search([('invoice_id', '=', invoice.id), ('amount_residual','!=',0), ('date_maturity','<', d)]) 
            # if invoice_dues:
            vals = {'invoice_ids': invoice.id,
                    'expired_date': d,
                    'invoice_dues': invoice_dues
            }
            
            new_line = new_lines.new(vals)
            new_lines += new_line
            # else:
            #     raise ValidationError(_('The %s invoice is not expired.')%str(invoice.display_name))
        self.account_interest_calc_details_ids += new_lines

    @api.onchange('date')
    def _onchange_date(self):
        self.invoice_ids = False

    @api.multi
    def calculate(self):
        # self.ensure_one()
        origin = ''
        total = 0.0
        form = (self.read())[0]
        model = self.env['account.invoice']

        if not self.account_interest_calc_details_ids: 
            raise ValidationError(_('Select one or more invoices to continue.'))

        if self.partner_id:
            if not self.partner_id.afip_responsability_type_id:
                raise ValidationError(_('You need define Afip responsability type for this partner.'))

        # SE HIZO UN CAMBIO PARA TOMAR LOS INVOICES DESDE OTRO OBJETO
        # if not self.invoice_ids:
        #     raise ValidationError(_('Select one or more invoices to continue.'))
        
        # CAMBIO 27/01
        # SE CAMBIO EL FLUJO PARA QUE RECORRA CADA UNA DE LAS CUOTAS SELECCIONADAS DE CADA UNA DE LAS FACTURAS
        for lines in self.account_interest_calc_details_ids:
            for invoice in lines.invoice_ids:
                origin += invoice.display_name+' '
                if invoice.state != 'open':
                    raise ValidationError(_('Only interest in open invoices can be calculated. At least one of the selected invoices is not in an open state. Change the selection of invoices and try again.'))
                else: 
                    for dues in lines.invoice_dues:
                        if (invoice == dues.invoice_id):
                            days = (datetime.datetime.strptime(self.date, '%Y-%m-%d').date() - datetime.datetime.strptime(dues.date_maturity, '%Y-%m-%d').date()).days
                            if days > 0:
                                if dues.amount_residual != 0:
                                    total += ((((self.interest/self.period) * days) / 100) * dues.debit)
                                    # total += (self.interest * (days)/self.period)
                            else:
                                raise ValidationError(_('The %s invoice is not expired.')%str(invoice.display_name))
        # for invoice in self.account_interest_calc_details_ids.invoice_ids:
        #     total = 0.0
        #     if invoice.state != 'open':
        #         raise ValidationError(_('Only interest in open invoices can be calculated. At least one of the selected invoices is not in an open state. Change the selection of invoices and try again.'))
        #     else: 
        #         for line in invoice.move_id.line_ids:
        #             days = (datetime.datetime.strptime(self.date, '%Y-%m-%d').date() - datetime.datetime.strptime(line.date_maturity, '%Y-%m-%d').date()).days
        #             d = datetime.datetime.now().date()
        #             if line.amount_residual != 0 and days > 0:
        #                 if d >= l.date_maturity:
        #                     total += (self.interest * (days)/self.period)

        product = self.env.ref("account_invoice_interest_calc.product_product_invoice_interest")
        docs = self.env['account.invoice']._get_available_journal_document_types(
                    self.journal_id, 'out_invoice', self.partner_id)
        available_journal_document_types = docs.get('available_journal_document_types')
        default_journal_document_type_id = False
        for doc_type in available_journal_document_types:
            if doc_type.document_type_id.internal_type == 'debit_note':
                default_journal_document_type_id = doc_type
                break
        view_id = self.env.ref('account.invoice_form').id
        invoice_line_tax_ids = [(4, product.taxes_id.id)] if len(product.taxes_id) == 1 else False
        return {
            'name': _('Debit Note'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice',
            'view_id': view_id,
            'target': 'current',
            'type': 'ir.actions.act_window',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_journal_id': self.journal_id.id,
                'default_origin': origin,
                'default_available_journal_document_types': available_journal_document_types.ids, 
                'default_journal_document_type_id': default_journal_document_type_id.id,
                'default_invoice_line_ids': [(0, 0,  {'product_id': product.id,
                                                    'name': product.name,
                                                    'account_id': product.property_account_income_id.id,
                                                    'invoice_line_tax_ids': invoice_line_tax_ids,
                                                    'quantity': 1,
                                                    'price_unit': total,
                                                    })]

            },
        }

    @api.multi
    def calculate_multi(self):
        # AGREGAR LAS INVOICES Y LAS CUOTAS A UNA LISTA PARA POSTERIORMENTE FILTRAR 
        invoices = []
        dues = []
        for lines in self.account_interest_calc_details_ids:
            for invoice in lines.invoice_ids:
                invoices.append(invoice.id)
            for due in lines.invoice_dues:
                dues.append(due.id)
        # invoices = self.env['account.invoice'].browse(self._context.get('active_ids'))
        invoices = self.env['account.invoice'].browse(invoices)
        if not invoices:
            raise ValidationError(_('Select one or more invoices to continue.'))
        dues = self.env['account.move.line'].browse(dues)
        product = self.env.ref("account_invoice_interest_calc.product_product_invoice_interest")
        partners = invoices.mapped('partner_id')
        interest_invoices = []
        for partner_id in partners:
            total = 0.0
            if not partner_id.afip_responsability_type_id:
                raise ValidationError(_('You need define Afip responsability type for this partner.'))
            partner_invoices = invoices.filtered(lambda r: r.partner_id == partner_id)
            origin = ''
            for invoice in partner_invoices:
                if invoice.state != 'open' or invoice.type != 'out_invoice':
                    raise ValidationError(_('Only interest in open invoices can be calculated. At least one of the selected invoices is not in an open state or supplier invoice. Change the selection of invoices and try again.'))
                elif invoice.account_due_calc != True:
                    raise ValidationError(_('The %s invoice is not expired.')%str(invoice.display_name))
                else:
                    dues_invoices = dues.filtered(lambda r: r.invoice_id == invoice)
                    for d_i in dues_invoices:
                        days = (datetime.datetime.strptime(self.date, '%Y-%m-%d').date() - datetime.datetime.strptime(d_i.date_maturity, '%Y-%m-%d').date()).days
                        d = datetime.datetime.strptime(self.date, '%Y-%m-%d').date()
                        if days > 0:
                            if d_i.amount_residual != 0:
                                # total += (self.interest * (days)/self.period)
                                total += ((((self.interest/self.period) * days) / 100) * d_i.debit)
                        else:
                            raise ValidationError(_('The %s invoice is not expired.')%str(invoice.display_name))
                origin += invoice.display_name+' '
            docs = self.env['account.invoice']._get_available_journal_document_types(
                        self.journal_id, 'out_invoice', partner_id)
            available_journal_document_types = docs.get('available_journal_document_types')
            default_journal_document_type_id = False
            for doc_type in available_journal_document_types:
                if doc_type.document_type_id.internal_type == 'debit_note':
                    default_journal_document_type_id = doc_type
                    break
            invoice_line_tax_ids = [(4, product.taxes_id.id)] if len(product.taxes_id) == 1 else False
            vals = {
                'partner_id': partner_id.id,
                'journal_id': self.journal_id.id,
                'type': 'out_invoice',
                'origin': origin,
                'available_journal_document_types': available_journal_document_types.ids, 
                'journal_document_type_id': default_journal_document_type_id.id,
                'invoice_line_ids': [(0, 0,  {'product_id': product.id,
                                                    'name': product.name,
                                                    'account_id': product.property_account_income_id.id,
                                                    'invoice_line_tax_ids': invoice_line_tax_ids,
                                                    'quantity': 1,
                                                    'price_unit': total,
                                                    })]

            }

            res_invoice = self.env['account.invoice'].create(vals)
            interest_invoices.append(res_invoice.id)
            view_form = self.env.ref('account.invoice_form').id
            view_tree = self.env.ref('account.invoice_tree').id

        return {
            'type': 'ir.actions.act_window',
            'name': 'Interest Invoices',
            'views': [[view_tree, 'tree'], [view_form, 'form']],
            'res_model': 'account.invoice',
            'domain': [('id','in',interest_invoices)],
            'target': 'current'
        }

class InvoiceInterestCalcWizardDetails(models.TransientModel):
    _name = "account.interest.calc.details.wizard"
    _description = "Account Invoice Calculator Lines Wizard"

    invoice_ids = fields.Many2one('account.invoice', string="Facturas", required="True")
    partner_id = fields.Many2one('res.partner', related="invoice_ids.partner_id", string="Cliente")
    date_invoice = fields.Date(string="Fecha Factura", related="invoice_ids.date_invoice")
    expired_date = fields.Date(string="Fecha de vencimiento", default=datetime.datetime.now().date())
    invoice_dues = fields.Many2many('account.move.line', string="Cuotas Vencidas", required="True")
    account_invoice_interest_calc_id = fields.Many2one('account.invoice.interest.calc.wizard', string="Account Interest")
    
    @api.onchange('invoice_ids')
    def _onchange_invoices(self):
        d = datetime.datetime.now().date()
        if self.invoice_ids:
            self.invoice_dues = self.env['account.move.line'].search([('invoice_id', '=', self.invoice_ids.id), ('amount_residual','!=',0), ('date_maturity','<', d)]) 