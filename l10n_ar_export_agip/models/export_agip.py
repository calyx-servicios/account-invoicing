# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models, _
from odoo.tools import date_utils
from odoo.exceptions import UserError
from datetime import date, timedelta, datetime
import base64, calendar

WITHHOLDINGPERCEPTION = '6'
CREDITNOTE = '7'
DOCUMENT_TYPES = {
    'FA':'01',
    'ND':'02',
    'OP':'03',
    'RE':'07'
}
IDENTIFICATION_TYPES = {
    '80':'3',
    '86':'2'
}
IB_SITUATIONS = {
    'multilateral':'2',
    'local':'1',
    'exempt':'4'
}
IVA_SITUATIONS = {
    '1':'1',
    '4':'3',
    '6':'4'
}

class AccountExportAgip(models.Model):
    _name = 'account.export.agip'
    _description = 'Export file for AGIP'

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
            (WITHHOLDINGPERCEPTION, 'Withholding and Perception'),
            (CREDITNOTE, 'Credit notes')
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
    export_agip_data = fields.Text(
        'File content'
    )
    export_agip_file = fields.Binary(
        'Download File',
        compute="_compute_files",
        readonly=True,
    )
    export_agip_filename = fields.Char(
        'File AGIP',
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
            if rec.doc_type == WITHHOLDINGPERCEPTION:
                rec.fortnight = 0

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

    @api.depends('export_agip_data')
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
            if rec.doc_type == WITHHOLDINGPERCEPTION:
                _type = 'WITHHOLDING-PERCEPTION'
            else:
                _type = 'CREDIT-NOTE'
            
            filename = 'AR-%s-%s-%s.txt' % (cuit, _date, _type)
            rec.export_agip_filename = filename
            if rec.export_agip_data:
                rec.export_agip_file = base64.encodebytes(
                    rec.export_agip_data.encode('UTF-8')
                )
            else:
                rec.export_agip_file = False

    def get_withholding_payments(self):
        """ 
        Obtains the supplier payments that are withholdings and that are in the selected period
        """
        agip_imp = 'Ret/Perc IIBB Aplicada'
        jur_imp = 'Jur: 901 - Capital Federal'
        account_tag_obj = self.env['account.account.tag']
        retAGIP = account_tag_obj.search([('name', '=', agip_imp)]).id
        jurAGIP = account_tag_obj.search([('name', '=', jur_imp)]).id
        
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
                        if retAGIP in tax_line.tag_ids.ids and jurAGIP in tax_line.tag_ids.ids:
                            ret += pay
        
        return ret

    def get_perception_invoices(self):
        """
        Gets the customer invoices that have perceptions and that are in the selected period.
        """
        agip_imp = 'Ret/Perc IIBB Aplicada'
        jur_imp = 'Jur: 901 - Capital Federal'
        account_tag_obj = self.env['account.account.tag']
        percAGIP = account_tag_obj.search([('name', '=', agip_imp)]).id
        jurAGIP = account_tag_obj.search([('name', '=', jur_imp)]).id
        
        invoice_obj = self.env['account.move'].sudo()
        invoices = invoice_obj.search([
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('type', '=', 'out_invoice'),
            ('invoice_payment_state', '=', 'paid')
        ])
        
        per = invoice_obj      
        for inv in invoices:
            for line in inv.invoice_line_ids:
                for tax in line.tax_ids:
                    for tax_line in tax.invoice_repartition_line_ids:
                        if percAGIP in tax_line.tag_ids.ids and jurAGIP in tax_line.tag_ids.ids:
                            per += inv
                            
        return per
    
    def get_perception_credit_notes(self):
        """
        Gets the customer credit notes that have perceptions and that are in the selected period.
        """
        agip_imp = 'Ret/Perc IIBB Aplicada'
        jur_imp = 'Jur: 901 - Capital Federal'
        account_tag_obj = self.env['account.account.tag']
        percAGIP = account_tag_obj.search([('name', '=', agip_imp)]).id
        jurAGIP = account_tag_obj.search([('name', '=', jur_imp)]).id
        
        invoice_obj = self.env['account.move'].sudo()
        invoices = invoice_obj.search([
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('type', '=', 'out_refund'),
            ('invoice_payment_state', '=', 'paid')
        ])
        
        per = invoice_obj      
        for inv in invoices:
            for line in inv.invoice_line_ids:
                for tax in line.tax_ids:
                    for tax_line in tax.invoice_repartition_line_ids:
                        if percAGIP in tax_line.tag_ids.ids and jurAGIP in tax_line.tag_ids.ids:
                            per += inv
                            
        return per

    def compute_agip_data(self):
        line = ''
        for rec in self:
            if rec.doc_type == WITHHOLDINGPERCEPTION:
                # Retenciones
                payments = self.get_withholding_payments()
                data = []
                for payment in payments:
                    # Campo 01 -- Tipo de operacion len 1
                    line = '1'
                    
                    # Campo 02 -- Código de norma len 3
                    line += '029'
                    
                    # Campo 03 -- Fecha retencion len 10
                    _date = payment.payment_date.strftime('%d/%m/%Y') #fecha del pago
                    line += _date
                    
                    # Campo 04 -- Tipo de comprobante len 2
                    # Campo 05 -- Letra del comprobante len 1
                    # Campo 06 -- Numero del comprobante len 16  
                    doc_name = payment.display_name.split(' ')
                    if len(doc_name) > 0:
                        doc_type = doc_name[0].split('-')
                        code_prefix = DOCUMENT_TYPES.get(doc_type[0],'09')
                        code_letter = ' '
                        doc_number = doc_name[1].split('-')
                        code_issue = doc_number[1]
                    else:
                        code_prefix = ' '
                        code_letter = ' '
                        code_issue = 0
                        
                    line += str(code_prefix)
                    line += str(code_letter)
                    line += str(code_issue).zfill(16)
                    
                    # Campo 07 -- Fecha del comprobante len 10
                    _date_pay = payment.payment_date.strftime('%d/%m/%Y')
                    line += _date_pay  
                    
                    # Campo 08 -- Monto del comprobante len 16
                    amount = 0.00
                    for pay_line in payment.payment_ids:
                        if pay_line.payment_method_id.code == 'withholding':
                            amount = pay_line.withholding_base_amount
                    
                    amount_str = '{:.2f}'.format(amount)
                    amount_str = amount_str.replace('.', ',')
                    line += amount_str.zfill(16)
                    
                    # Campo 09 -- Nro certificado propio len 16
                    number = payment.withholding_number
                    line += number.rjust(16)
                    
                    # Campo 10 -- Tipo de documento del retenido len 1
                    type_doc = payment.partner_id.l10n_latam_identification_type_id.l10n_ar_afip_code
                    code_type_doc = IDENTIFICATION_TYPES.get(type_doc, '3')
                    line += code_type_doc
                    
                    # Campo 11 -- Nro de documento del retenido len 11
                    line += payment.partner_id.vat.zfill(11)
                    
                    # Campo 12 -- Situacion IB del retenido len 1
                    situation_ib = payment.partner_id.l10n_ar_gross_income_type
                    code_situation_ib = IB_SITUATIONS.get(situation_ib, '1')
                    line += code_situation_ib
                    
                    # Campo 13 -- Nro inscripcion IB del retenido len 11
                    nro_ib = payment.partner_id.l10n_ar_gross_income_number
                    line += nro_ib.zfill(11)
                    
                    # Campo 14 -- Situacion frente IVA del retenido len 1
                    type_afip = payment.partner_id.l10_ar_afip_responsibility_type_id
                    code_afip = IVA_SITUATIONS.get(type_afip, '1')
                    line += code_afip
                    
                    # Campo 15 -- Razon social del retenido len 30
                    line += payment.partner_id.name.rjust(30)
                    
                    # Campo 16 -- Importe otros conceptos len 16
                    other_amount = 0.00
                    line += str(other_amount).zfill(16)
                    
                    # Campo 17 -- Importe IVA len 16
                    iva_amount = 0.00
                    line += str(iva_amount).zfill(16)
                    
                    # Campo 18 -- Monto sujeto a retencion len 16
                    ret_amount = amount - iva_amount - other_amount
                    line += str(ret_amount).zfill(16)
                    
                    agip_imp = 'Ret/Perc IIBB Aplicada'
                    jur_imp = 'Jur: 901 - Capital Federal'
                    account_tag_obj = self.env['account.account.tag']
                    percAGIP = account_tag_obj.search([('name', '=', agip_imp)]).id
                    jurAGIP = account_tag_obj.search([('name', '=', jur_imp)]).id
                    amount_alicout = 0
                    for line_alicuot in invoice.partner_id.arba_alicuot_ids:
                        if line_alicuot.tag_id == jurAGIP and rec.date_from >= line_alicuot.from_date and rec.date_to <= line_alicuot.to_date: 
                            amount_alicout = line_alicuot.alicuota_retencion
                    
                    # Campo 19 -- Alicuota len 5 
                    amount_alicout_str = '{:.2f}'.format(amount_alicout)
                    amount_alicout_str = amount_alicout_str.replace('.', ',')
                    line += amount_alicout_str.zfill(5)
                    
                    # Campo 20 -- Retencion practicada len 16
                    amount_total = (ret_amount * amount_alicout) / 100
                    line += str(amount_total).zfill(16)       
                    
                    # Campo 21 -- Monto total retenido len 16
                    line += str(amount_total).zfill(16)
                    
                    data.append(line)
                    
                # Percepciones
                invoices = self.get_perception_invoices()
                data = []
                for invoice in invoices:
                    # Campo 01 -- Tipo de operacion len 1
                    line = '2'
                    
                    # Campo 02 -- Código de norma len 3
                    line += '029'
                    
                    # Campo 03 -- Fecha percepcion len 10
                    _date = invoice.invoice_date.strftime('%d/%m/%Y')
                    line += _date
                    
                    # Campo 04 -- Tipo de comprobante len 2
                    # Campo 05 -- Letra del comprobante len 1
                    # Campo 06 -- Numero del comprobante len 16  
                    doc_name = payment.display_name.split(' ')
                    if len(doc_name) > 0:
                        doc_type = doc_name[0].split('-')
                        code_prefix = DOCUMENT_TYPES.get(doc_type[0],'09')
                        code_letter = doc_type[1]
                        doc_number = doc_name[1].split('-')
                        code_issue = doc_number[1]
                    else:
                        code_prefix = ' '
                        code_letter = ' '
                        code_issue = 0
                        
                    line += str(code_prefix)
                    line += str(code_letter)
                    line += str(code_issue).zfill(16)
                    
                    # Campo 07 -- Fecha del comprobante len 10
                    _date_inv = invoice.invoice_date.strftime('%d/%m/%Y')
                    line += _date_inv
                    
                    # Campo 08 -- Monto del comprobante len 16
                    amount = invoice.amount_untaxed
                    amount_str = '{:.2f}'.format(amount)
                    amount_str = amount_str.replace('.', ',')
                    line += amount_str.zfill(16)
                    
                    # Campo 09 -- Nro certificado propio len 16
                    line += ''.rjust(16)
                    
                    # Campo 10 -- Tipo de documento del percibido len 1
                    type_doc = invoice.partner_id.l10n_latam_identification_type_id.l10n_ar_afip_code
                    code_type_doc = IDENTIFICATION_TYPES.get(type_doc, '3')
                    line += code_type_doc
                    
                    # Campo 11 -- Nro de documento del percibido len 11
                    line += invoice.partner_id.vat.zfill(11)
                    
                    # Campo 12 -- Situacion IB del percibido len 1
                    situation_ib = invoice.partner_id.l10n_ar_gross_income_type
                    code_situation_ib = IB_SITUATIONS.get(situation_ib, '1')
                    line += code_situation_ib
                    
                    # Campo 13 -- Nro inscripcion IB del percibido len 11
                    nro_ib = invoice.partner_id.l10n_ar_gross_income_number
                    line += nro_ib.zfill(11)
                    
                    # Campo 14 -- Situacion frente IVA del percibido len 1
                    type_afip = invoice.partner_id.l10_ar_afip_responsibility_type_id
                    code_afip = IVA_SITUATIONS.get(type_afip, '1')
                    line += code_afip
                    
                    # Campo 15 -- Razon social del percibido len 30
                    line += invoice.partner_id.name.rjust(30)
                    
                    # Campo 16 -- Importe otros conceptos len 16
                    other_amount = 0.00
                    line += str(other_amount).zfill(16)
                    
                    # Campo 17 -- Importe IVA len 16
                    iva_amount = 0.00
                    line += str(iva_amount).zfill(16)
                    
                    # Campo 18 -- Monto sujeto a percepcion len 16
                    ret_amount = amount - iva_amount - other_amount
                    line += str(ret_amount).zfill(16)
                    
                    agip_imp = 'Ret/Perc IIBB Aplicada'
                    jur_imp = 'Jur: 901 - Capital Federal'
                    account_tag_obj = self.env['account.account.tag']
                    percAGIP = account_tag_obj.search([('name', '=', agip_imp)]).id
                    jurAGIP = account_tag_obj.search([('name', '=', jur_imp)]).id
                    amount_alicout = 0
                    for line_alicuot in invoice.partner_id.arba_alicuot_ids:
                        if line_alicuot.tag_id == jurAGIP and rec.date_from >= line_alicuot.from_date and rec.date_to <= line_alicuot.to_date: 
                            amount_alicout = line_alicuot.alicuota_percepcion
                    
                    # Campo 19 -- Alicuota len 5 
                    amount_alicout_str = '{:.2f}'.format(amount_alicout)
                    amount_alicout_str = amount_alicout_str.replace('.', ',')
                    line += amount_alicout_str.zfill(5)
                    
                    # Campo 20 -- Percepcion practicada len 16
                    amount_total = (ret_amount * amount_alicout) / 100
                    line += str(amount_total).zfill(16)       
                    
                    # Campo 21 -- Monto total percibido len 16
                    line += str(amount_total).zfill(16)
                    
                    data.append(line)
            else:
                # Percepciones
                invoices = self.get_perception_credit_notes()
                data = []
                for invoice in invoices:
                    # Campo 01 -- Tipo de operacion len 1
                    line = '2' #1=withholding 2=perception
                    
                    # Campo 02 -- Nro. Nota de Crédito len 12
                    doc_name = invoice.name.split(' ')
                    if len(doc_name) > 0:
                        doc_number = doc_name[1].split('-')
                        code_issue = doc_number[1]
                    else:
                        code_issue = 0
                    line += str(code_issue).zfill(12)
                    
                    # Campo 03 -- Fecha nota de credito len 10
                    _date = invoice.invoice_date.strftime('%d/%m/%Y')
                    line += _date
                    
                    # Campo 04 -- Monto nota de credito len 16
                    amount = invoice.amount_untaxed
                    amount_str = '{:.2f}'.format(amount)
                    amount_str = amount_str.replace('.', ',')
                    line += amount_str.zfill(16)
                    
                    # Campo 05 -- Nro certificado propio len 16
                    line += "".rjust(16)
                    
                    # Campo 06 -- Tipo de comprobante origen de la retencion len 2
                    line += '01' #01=Factura 02=Otro comprobante
                    
                    # Campo 07 -- Letra del comprobante len 1
                    # Campo 08 -- Nro de comprobante len 16
                    doc_name = invoice.reversed_entry_id.name.split(' ')
                    if len(doc_name) > 0:
                        doc_type = doc_name[0].split('-')
                        code_letter = doc_type[1]
                        doc_number = doc_name[1].split('-')
                        code_issue = doc_number[1]
                    else:
                        code_letter = ' '
                        code_issue = 0
                    
                    line += str(code_letter)
                    line += str(code_issue).zfill(16)
                    
                    # Campo 09 -- Nro de documento del retenido len 11
                    line += str(invoice.partner_id.vat).zfill(11)
                    
                    # Campo 10 -- Código norma len 3
                    line += '029'
                    
                    # Campo 11 -- Fecha de retención/percepción len 10
                    _date_per = invoice.invoice_date.strftime('%d/%m/%Y')
                    line += _date_per
                    
                    agip_imp = 'Ret/Perc IIBB Aplicada'
                    jur_imp = 'Jur: 901 - Capital Federal'
                    account_tag_obj = self.env['account.account.tag']
                    percAGIP = account_tag_obj.search([('name', '=', agip_imp)]).id
                    jurAGIP = account_tag_obj.search([('name', '=', jur_imp)]).id
                    amount_alicout = 0
                    for line_alicuot in invoice.partner_id.arba_alicuot_ids:
                        if line_alicuot.tag_id == jurAGIP and rec.date_from >= line_alicuot.from_date and rec.date_to <= line_alicuot.to_date: 
                            amount_alicout = line_alicuot.alicuota_percepcion
                    
                    # Campo 12 -- Ret/Percep a deducir len 16
                    # Campo 13 -- Alicuota len 5
                    amount_total = (amount * amount_alicout) / 100 
                    amount_alicout_str = '{:.2f}'.format(amount_alicout)
                    amount_alicout_str = amount_alicout_str.replace('.', ',')
                    line += str(amount_total).zfill(16)          
                    line += amount_alicout_str.zfill(5)

                    data.append(line)
            
            rec.export_agip_data = '\n'.join(data)

