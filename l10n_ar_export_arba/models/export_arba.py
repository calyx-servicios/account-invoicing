# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models, _
from odoo.tools import date_utils
from odoo.exceptions import UserError
from datetime import date, timedelta, datetime
import base64, calendar

WITHHOLDING = '6'
PERCEPTION = '7'
DOCUMENT_TYPES = {
    'FA':'F',
    'RE':'R',
    'NC':'C',
    'ND':'D',
    'FCE':'E',
    'NCE':'H',
    'NDE':'I',
}

class AccountExportArba(models.Model):
    _name = 'account.export.arba'
    _description = 'Export file for ARBA'

    year = fields.Integer(
        default=lambda self: self._default_year(),
        help='Year of the period',
        string='Year'
    )
    month = fields.Integer(
        default=lambda self: self._default_month(),
        help='Month of the period',
        string='Month'
    )
    period = fields.Char(
        compute="_compute_period",
        string='Period'
    )
    fortnight = fields.Selection(
        [('0', 'Monthly'),
         ('1', 'First'),
         ('2', 'Second')],
        default=0
    )
    doc_type = fields.Selection(
        [
            (WITHHOLDING, 'Withholding'),
            (PERCEPTION, 'Perception')
        ],
        string="Type of file",
        default="6"
    )
    date_from = fields.Date(
        'From',
        readonly=True,
        compute="_compute_dates"
    )
    date_to = fields.Date(
        'To',
        readonly=True,
        compute="_compute_dates"
    )
    export_arba_data = fields.Text(
        'File content'
    )
    export_arba_file = fields.Binary(
        'Download File',
        compute="_compute_files",
        readonly=True,
    )
    export_arba_filename = fields.Char(
        'File ARBA',
        compute="_compute_files",
        readonly=True,
    )

    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, '%s%.2d' % (rec.year, rec.month)))
        return res

    @staticmethod
    def _last_month():
        today = date.today()
        first = today.replace(day=1)
        return first - timedelta(days=1)

    def _default_year(self):
        return self._last_month().year

    def _default_month(self):
        return self._last_month().month

    @api.onchange('year', 'month')
    def _compute_period(self):
        for reg in self:
            reg.period = '%s/%s' % (reg.year, reg.month)

    @api.onchange('year', 'month', 'fortnight', 'doc_type')
    def _compute_dates(self):
        """ 
        Given the month and the year calculate the first and last day of the period
        """
        for rec in self:
            if rec.doc_type == WITHHOLDING:
                rec.fortnight = '0'

            month = rec.month
            year = int(rec.year)

            _ds = fields.Date.to_date('%s-%.2d-01' % (year, month))
            _de = date_utils.end_of(_ds, 'month')

            if rec.fortnight == '1':
                _ds = datetime(year, month, 1)
                _de = datetime(year, rec.month, 15)
            if rec.fortnight == '2':
                _ds = datetime(year, month, 16)
                last_day = calendar.monthrange(year, rec.month)[1]
                _de = datetime(year, month, last_day)

            rec.date_from = _ds
            rec.date_to = _de

    @api.depends('export_arba_data')
    def _compute_files(self):
        for rec in self:
            # filename AR-CUIT-PERIODO-TIPO.TXT
            if not rec.env.company.vat:
                raise UserError(_('You have not configured the CUIT for this company'))

            cuit = rec.env.company.vat.replace('-','')
            if rec.date_from and rec.date_to:
                _date = '%s%s' % (rec.date_from.year, rec.date_from.month)
            else:
                _date = '000000'
                
            _type = ''
            if rec.doc_type == WITHHOLDING:
                _type = 'WITHHOLDING'
            else:
                _type = 'PERCEPTION'
            
            filename = 'AR-%s-%s%s-%s.txt' % (cuit, _date, rec.fortnight, _type)
            rec.export_arba_filename = filename
            if rec.export_arba_data:
                rec.export_arba_file = base64.encodebytes(
                    rec.export_arba_data.encode('UTF-8')
                )
            else:
                rec.export_arba_file = False

    def get_withholding_payments(self, retARBA, jurARBA):
        """ 
        Obtains the supplier payments that are withholdings and that are in the selected period
        """
        payment_obj = self.env['account.payment.group'].sudo()
        payments = payment_obj.search([
            ('payment_date', '>=', self.date_from),
            ('payment_date', '<=', self.date_to),
            ('state', '=', 'posted')
        ])
        
        ret = payment_obj      
        for pay in payments:
            for line in pay.payment_ids:
                if line.payment_method_id.code == 'withholding':
                    for tax_line in line.tax_withholding_id.invoice_repartition_line_ids:
                        if retARBA in tax_line.tag_ids.ids and jurARBA in tax_line.tag_ids.ids:
                            ret += pay
        
        return ret

    def get_perception_invoices(self, percARBA, jurARBA):
        """
        Gets the customer invoices that have perceptions and that are in the selected period.
        """
        invoice_obj = self.env['account.move'].sudo()
        invoices = invoice_obj.search([
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('type', 'in', ['out_invoice','out_refund']),
            ('state', '=', 'posted')
        ])
        
        per = invoice_obj      
        for inv in invoices:
            for line in inv.invoice_line_ids:
                for tax in line.tax_ids:
                    for tax_line in tax.invoice_repartition_line_ids:
                        if percARBA in tax_line.tag_ids.ids and jurARBA in tax_line.tag_ids.ids:
                            per += inv
                            
        return per

    def compute_arba_data(self):
        line = ''
        account_tag_obj = self.env['account.account.tag']
        arba_imp = self.env.ref("l10n_ar_ux.tag_ret_perc_iibb_aplicada")
        arba_jur = self.env.ref("l10n_ar_ux.tag_tax_jurisdiccion_902")
        impARBA = account_tag_obj.search([('id', '=', arba_imp.id)]).id
        jurARBA = account_tag_obj.search([('id', '=', arba_jur.id)]).id
        for rec in self:
            if rec.doc_type == WITHHOLDING:
                # Retenciones
                payments = self.get_withholding_payments(impARBA, jurARBA)
                data = []
                for payment in payments:       
                    # Campo 01 -- Cuit contribuyente retenido len 13
                    try:
                        cuit = payment.partner_id.vat[:2] + "-" + payment.partner_id.vat[2:-1] + "-" + payment.partner_id.vat[-1:]
                    except Exception:
                        raise UserError(_('Partner does not have a loaded cuit.'))
                    line = cuit.zfill(13)

                    # Campo 02 -- Fecha de retención len 10
                    _date = payment.payment_date.strftime('%d/%m/%Y')
                    line += _date

                    # Campo 03 -- Número de sucursal len 4
                    # Campo 04 -- Número de emisión len 8
                    name_pay = payment.display_name.split(' ')
                    if len(name_pay) > 0:
                        code_office = name_pay[1][:4]
                        code_issue = name_pay[1][5:]
                    else:
                        code_office = 0
                        code_issue = 0
                    line += str(code_office).zfill(4)
                    line += str(code_issue).zfill(8)
                    
                    # Campo 5 Importe de la retencion len 11
                    for pay_line in payment.payment_ids:
                        if pay_line.payment_method_id.code == 'withholding':
                            amount_ret = '{:.2f}'.format(pay_line.amount)
                            amount_ret = amount_ret.replace('.', ',')
                            line += str(amount_ret).zfill(11)

                    # Campo 6 Tipo Operación len 1
                    line += 'A'
                    
                    data.append(line)
            else:
                # Percepciones
                invoices = self.get_perception_invoices(impARBA, jurARBA)
                data = []
                for invoice in invoices:
                    # Campo 01 -- Cuit contribuyente percibido len 13
                    try:
                        cuit = invoice.partner_id.vat[:2] + "-" + invoice.partner_id.vat[2:-1] + "-" + invoice.partner_id.vat[-1:]
                    except Exception:
                        raise UserError(_('Partner does not have a loaded cuit.'))
                    line = cuit.zfill(13)
                    
                    # Campo 02 -- Fecha de percepción len 10
                    _date = invoice.invoice_date.strftime('%d/%m/%Y')
                    line += _date
                    
                    # Campo 03 -- Tipo de comprobante len 1
                    # Campo 04 -- Letra de comprobante len 1
                    # Campo 05 -- Número sucursal len 4
                    # Campo 06 -- Número emisión len 8
                    code_prefix = ' '
                    code_letter = ' '
                    code_office = 0
                    code_issue = 0
                    doc_name = invoice.name.split(' ')
                    if len(doc_name) > 0:
                        doc_type = doc_name[0].split('-')
                        code_prefix = DOCUMENT_TYPES.get(doc_type[0],'F')
                        code_letter = doc_type[1]
                        doc_number = doc_name[1].split('-')
                        code_office = doc_number[0][-4:]
                        code_issue = doc_number[1]
                        
                    line += str(code_prefix)
                    line += str(code_letter)
                    line += str(code_office)
                    line += str(code_issue)
                    
                    amount = 0
                    for inv_line in invoice.line_ids:
                        if impARBA in inv_line.tag_ids.ids and jurARBA in inv_line.tag_ids.ids:
                            if code_prefix == 'C' or code_prefix == 'H':
                                amount = inv_line.debit
                            else:
                                amount = inv_line.credit
                    
                    # Campo 07 -- Monto imponible len 12
                    # Campo 08 -- Importe de Percepción len 11
                    amount_untaxed = '{:.2f}'.format(invoice.amount_untaxed)
                    amount_untaxed = amount_untaxed.replace('.', ',')
                    amount_tax = '{:.2f}'.format(amount)
                    amount_tax = amount_tax.replace('.', ',')
                    if code_prefix == 'C' or code_prefix == 'H':
                        sign = '-'
                        line += sign + str(amount_untaxed).zfill(11)
                        line += sign + str(amount_tax).zfill(10)
                    else:
                        line += str(amount_untaxed).zfill(12)
                        line += str(amount_tax).zfill(11)
                    
                    # Campo 09 -- Tipo Operación len 1
                    line += 'A'
                    
                    data.append(line)
            
            rec.export_arba_data = '\n'.join(data)

