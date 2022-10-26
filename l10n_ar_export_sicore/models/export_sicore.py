# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models, _
from odoo.tools import date_utils
from odoo.exceptions import UserError
from datetime import date, timedelta, datetime
import base64, calendar

WITHHOLDING = '6'
PERCEPTION = '7'

class AccountExportSicore(models.Model):
    _name = 'account.export.sicore'
    _description = 'Export file for Sicore'

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
    export_sicore_data = fields.Text(
        'File content'
    )
    export_sicore_file = fields.Binary(
        'Download File',
        compute="_compute_files",
        readonly=True,
    )
    export_sicore_filename = fields.Char(
        'File sicore',
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
        Given the month and the year calculate the first 
        and last day of the period
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

    @api.depends('export_sicore_data')
    def _compute_files(self):
        for rec in self:
            # filename SICORE-30708346655-201901.TXT
            if not rec.env.company.vat:
                raise UserError(_('You have not configured the CUIT for this company'))

            cuit = rec.env.company.vat.replace('-','')
            if rec.date_from and rec.date_to:
                _date = '%s%s' % (rec.date_from.year, rec.date_from.month)
            else:
                _date = '000000'

            filename = 'SICORE-%s-%s.txt' % (cuit, _date)
            rec.export_sicore_filename = filename
            if rec.export_sicore_data:
                rec.export_sicore_file = base64.encodebytes(
                    rec.export_sicore_data.encode('UTF-8')
                )
            else:
                rec.export_sicore_file = False

    def get_withholding_payments(self, imp_ret):
        """ 
        Obtains the supplier payments that are withholdings and 
        that are in the selected period
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
                        if imp_ret in tax_line.tag_ids.ids:
                            ret += pay
        
        return ret

    def get_perception_invoices(self, imp_perc):
        """ 
        Gets the customer invoices that have perceptions 
        and that are in the selected period.
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
                        if imp_perc in tax_line.tag_ids.ids:
                            per += inv
                            
        return per

    def compute_sicore_data(self):
        line = ''
        account_tag_obj = self.env['account.account.tag']
        sicore_imp = self.env.ref("l10n_ar_ux.tag_ret_perc_sicore_aplicada")
        impSicore = account_tag_obj.search([('id', '=', sicore_imp.id)]).id
        for rec in self:
            if rec.doc_type == WITHHOLDING:
                # Retenciones
                payments = self.get_withholding_payments(impSicore)
                data = []
                for payment in payments:
                    # Campo 01 -- Código de comprobante len 2
                    # Campo 02 -- Fecha de emision del comprobante len 10
                    # Campo 03 -- Numero del comprobante len 16
                    code_prefix = '05'
                    doc_number = ''
                    doc_name = payment.display_name.split(' ')
                    if len(doc_name) > 0:
                        doc_type = doc_name[0].split('-')
                        if doc_type[0] == 'OP':
                            code_prefix = '06'
                        doc_number = doc_name[1].replace('-','')
                    _date = payment.payment_date.strftime('%d/%m/%Y')
                    
                    line = code_prefix[:2]
                    line += str(_date)[:10]
                    line += str(doc_number)[:16].zfill(16)

                    # Campo 04 -- Importe del comprobante len 16
                    amount = payment.payments_amount
                    amount_str = '{:.2f}'.format(amount)
                    amount_str = str(amount_str).replace('.', ',')
                    line += amount_str[:16].zfill(16)
                    
                    # Campo 05 -- Código de impuesto len 4
                    code_tax = 0
                    amount_ret = 0.00
                    amount_base_ret = 0.00
                    for pay_line in payment.payment_ids:
                        if pay_line.payment_method_id.code == 'withholding':
                            amount_base_ret = pay_line.withholding_base_amount
                            amount_ret = pay_line.computed_withholding_amount
                            code_tax = pay_line.tax_withholding_id.sicore_tax_code
                    
                    line += str(code_tax)[:4].zfill(4)
                    
                    # Campo 06 -- Código de régimen len 3
                    if not payment.regimen_ganancias_id:
                        code_reg = '094'
                    else:
                        code_reg = payment.regimen_ganancias_id.display_name
                    line += str(code_reg)[:3].zfill(3)

                    # Campo 07 -- Código de operación len 1
                    line += '1'.zfill(1)

                    # Campo 08 -- Base de Cálculo len 14
                    amount_base_ret_str = '{:.2f}'.format(amount_base_ret)
                    amount_base_ret_str = str(amount_base_ret_str).replace('.', ',')
                    line += amount_base_ret_str[:14].zfill(14)

                    # Campo 09 -- Fecha de emisión de la retención len 10
                    line += str(_date)[:10]

                    # Campo 10 -- Código de condición len 2
                    line += '1'.zfill(2)

                    # Campo 11 -- Retención practicada a sujetos suspendidos según: len 1
                    line += '0'.zfill(1)

                    # Campo 12 -- Importe de la retencion len 14
                    amount_ret_str = '{:.2f}'.format(amount_ret)
                    amount_ret_str = str(amount_ret_str).replace('.', ',')
                    line += amount_ret_str[:14].zfill(14)

                    # Campo 13 -- Porcentaje de exclusión len 6
                    amount_excl = '{:.2f}'.format(0)
                    amount_excl = str(amount_excl).replace('.', ',')
                    line += amount_excl[:6].zfill(6)

                    # Campo 14 -- Fecha publicación o de finalización de la vigencia len 10
                    _date_pub = date.today().strftime('%d/%m/%Y')
                    #line += _date_pub
                    line += "00/00/0000".zfill(10)

                    # Campo 15 -- Tipo de documento del retenido len 2
                    type_doc = payment.partner_id.l10n_latam_identification_type_id.l10n_ar_afip_code
                    line += str(type_doc)[:2]

                    # Campo 16 -- Número de documento del retenido len 20
                    line += str(payment.partner_id.vat)[:20].zfill(20)

                    # Campo 17 -- Número certificado original len 14
                    line += '0'.zfill(14)
                    
                    # Campo 18 -- Denominación del ordenante len 30
                    line += "0".zfill(30)
                    
                    # Campo 19 -- Acrecentamiento len 1
                    line += "0"
                    
                    # Campo 20 -- Cuit del país retenido len 11
                    line += "0".zfill(11)
                    
                    # Campo 21 -- Cuit del ordenante len 11
                    line += str(payment.company_id.vat).replace('-','')[:11].zfill(11)
                    
                    data.append(line)
            else:
                # Percepciones
                invoices = self.get_perception_invoices(impSicore)
                data = []
                for invoice in invoices:
                    # Campo 01 -- Código de comprobante len 2
                    code = invoice.l10n_latam_document_type_id.code
                    line = str(code)[:2].zfill(2)

                    # Campo 02 -- Fecha de emision del comprobante len 10
                    _date = invoice.invoice_date.strftime('%d/%m/%Y')
                    line += str(_date)[:10]

                    # Campo 03 -- Numero comprobante len 16
                    doc_number = '0'
                    doc_name = invoice.name.split(' ')
                    if len(doc_name) > 0:
                        doc_number = doc_name[1].replace('-','')
                    
                    line += str(doc_number)[:16].zfill(16)

                    # Campo 04 -- Importe del comprobante len 16
                    amount = invoice.amount_untaxed
                    amount_str = '{:.2f}'.format(amount)
                    amount_str = str(amount_str).replace('.', ',')
                    line += amount_str[:16].zfill(16)

                    # Campo 05 -- Código de impuesto len 4
                    code_tax = 0
                    for line_invoice in invoice.invoice_line_ids:
                        for tax in line_invoice.tax_ids:
                            for tax_line in tax.invoice_repartition_line_ids:
                                if impSicore in tax_line.tag_ids.ids:
                                    code_tax = tax.sicore_tax_code
                    
                    line += str(code_tax)[:4].zfill(4)

                    # Campo 06 -- Código de régimen len 3
                    line += '94'.zfill(3)

                    # Campo 07 -- Código de operación len 1
                    line += '2'.zfill(1)

                    # Campo 08 -- Base de Cálculo len 14
                    line += amount_str[:14].zfill(14)

                    # Campo 09 -- Fecha de emisión de la percepcion len 10
                    line += str(_date)[:10]

                    # Campo 10 -- Código de condición len 2
                    code_afip = invoice.partner_id.l10n_ar_afip_responsibility_type_id.code
                    line += str(code_afip)[:2].zfill(2)

                    # Campo 11 -- Retención practicada a sujetos suspendidos según: len 1'
                    line += '0'.zfill(1)

                    # Campo 12 -- Importe de la retencion len 14
                    line += amount_str[:14].zfill(14)

                    # Campo 13 -- Porcentaje de exclusión len 6
                    amount_excl = '{:.2f}'.format(0)
                    amount_excl = str(amount_excl).replace('.', ',')
                    line += amount_excl[:6].zfill(6)

                    # Campo 14 -- Fecha publicación o de finalización de la vigencia len 10
                    _date_pub = date.today().strftime('%d/%m/%Y')
                    #line += str(_date_pub)[:10]
                    line += "00/00/0000".zfill(10)

                    # Campo 15 -- Tipo de documento del retenido len 2
                    type_doc = invoice.partner_id.l10n_latam_identification_type_id.l10n_ar_afip_code
                    line += str(type_doc)[:2]
                    
                    # Campo 16 -- Número de documento del retenido len 20
                    cuit = invoice.partner_id.vat
                    line += str(cuit)[:20].zfill(20)

                    # Campo 17 -- Número certificado original len 14
                    line += '0'.zfill(14)
                    
                    # Campo 18 -- Denominación del ordenante len 30
                    line += "0".zfill(30)
                    
                    # Campo 19 -- Acrecentamiento len 1
                    line += "0"
                    
                    # Campo 20 -- Cuit del país retenido len 11
                    line += "0".zfill(11)
                    
                    # Campo 21 -- Cuit del ordenante len 11
                    line += str(invoice.company_id.vat).replace('-','')[:11].zfill(11)
                    
                    data.append(line)
            
            rec.export_sicore_data = '\r\n'.join(data)

