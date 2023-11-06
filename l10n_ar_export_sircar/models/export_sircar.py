# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models, _
from odoo.tools import date_utils
from odoo.exceptions import UserError
from datetime import date, timedelta, datetime
import base64, calendar

WITHHOLDING = '1'
PERCEPTION = '2'
DOCUMENT_TYPES = {
    'FA':'001',
    'ND':'002',
    'RE':'003',
    'LI':'007',
    'TD':'020',
    'NC':'102',
    'TN':'120'
}

class AccountExportSircar(models.Model):
    _name = 'account.export.sircar'
    _description = _('Export file for SIRCAR')

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
    doc_type = fields.Selection(
        [
            (WITHHOLDING, 'Withholding'),
            (PERCEPTION, 'Perception')
        ],
        string="Type of file",
        default="1"
    )
    tag_tax = fields.Many2one(
        'account.account.tag', 
        string='Jurisdiction',
        domain=[("applicability", "=", "taxes"),('jurisdiction_code','!=','')]
    )
    export_sircar_data = fields.Text(
        'File content'
    )
    export_sircar_file = fields.Binary(
        'Download File',
        compute="_compute_files",
        readonly=True,
    )
    export_sircar_filename = fields.Char(
        'File SIRCAR',
        compute="_compute_files",
        readonly=True,
    )
    
    company_id = fields.Many2one('res.company')

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

    @api.onchange('year', 'month')
    def _compute_dates(self):
        """ 
        Given the month and the year calculate the first and last day of the period
        """
        for rec in self:
            month = rec.month
            year = int(rec.year)
            
            rec.date_from = datetime(year, month, 1)
            last_day = calendar.monthrange(year, month)[1]
            rec.date_to = datetime(year, month, last_day)

    @api.depends('export_sircar_data')
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
            
            filename = 'AR-%s-%s-%s.txt' % (cuit, _date, _type)
            rec.export_sircar_filename = filename
            if rec.export_sircar_data:
                rec.export_sircar_file = base64.encodebytes(
                    rec.export_sircar_data.encode('UTF-8')
                )
            else:
                rec.export_sircar_file = False

    def get_withholding_payments(self, retSIRCAR, jurSIRCAR):
        """ 
        Obtains the supplier payments that are withholdings and that are in the selected period
        """   
        payment_obj = self.env['account.payment.group'].sudo()
        payments = payment_obj.search([
            ('payment_date', '>=', self.date_from),
            ('payment_date', '<=', self.date_to),
            ('state', '=', 'posted'),
            ('company_id', '=', self.company_id.id)
        ])
        
        ret = payment_obj      
        for pay in payments:
            for line in pay.payment_ids:
                if line.payment_method_id.code == 'withholding':
                    for tax_line in line.tax_withholding_id.invoice_repartition_line_ids:
                        if retSIRCAR in tax_line.tag_ids.ids and jurSIRCAR in tax_line.tag_ids.ids:
                            if not pay in ret:
                                ret += pay
        
        return ret

    def get_perception_invoices(self, percSIRCAR, jurSIRCAR):
        """
        Gets the customer invoices that have perceptions and that are in the selected period.
        """
        invoice_obj = self.env['account.move'].sudo()
        invoices = invoice_obj.search([
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('type', 'in', ['out_invoice','out_refund']),
            ('state', '=', 'posted'),
            ('company_id', '=', self.company_id.id)
        ])
        
        per = invoice_obj      
        for inv in invoices:
            for line in inv.invoice_line_ids:
                for tax in line.tax_ids:
                    for tax_line in tax.invoice_repartition_line_ids:
                        if percSIRCAR in tax_line.tag_ids.ids and jurSIRCAR in tax_line.tag_ids.ids:
                            if not inv in per:
                                per += inv
                            
        return per
    
    def convert_currency(self, amount, rate, currency, round=True):
        to_amount = amount * rate
        return currency.round(to_amount) if round else to_amount
    
    def compute_sircar_data(self):
        line = ''
        account_tag_obj = self.env['account.account.tag']
        sircar_imp = self.env.ref("l10n_ar_ux.tag_ret_perc_iibb_aplicada")
        impSIRCAR = account_tag_obj.search([('id', '=', sircar_imp.id)]).id
        for rec in self:
            tag_tax = account_tag_obj.search([('id', '=', rec.tag_tax.id)])
            jurSIRCAR = tag_tax.id
            if rec.doc_type == WITHHOLDING:
                # Retenciones
                payments = self.get_withholding_payments(impSIRCAR, jurSIRCAR)
                data = []
                if tag_tax.jurisdiction_code != '904':
                    # Diseño N°1
                    nro_line = 1
                    for payment in payments:
                        # Campo 01 -- Número de renglón len 5
                        line = str(nro_line).zfill(5) + ","
                        
                        # Campo 02 -- Origen del comprobante len 1
                        line += '1' + ","
                        
                        # Campo 03 -- Tipo de comprobante len 1
                        line += '1' + ","
                        
                        # Campo 04 -- Numero del comprobante len 12  
                        doc_name = payment.display_name.split(' ')
                        if len(doc_name) > 0:
                            doc_number = doc_name[1].split('-')
                            code_issue = doc_number[1]
                        else:
                            code_issue = 0
                            
                        line += str(code_issue).zfill(12) + ","
                        
                        # Campo 05 -- Cuit contribuyente involucrado en la transacción comercial len 11
                        line += payment.partner_id.vat.zfill(11) + ","
                        
                        # Campo 06 -- Fecha de retencion len 10
                        _date = payment.payment_date.strftime('%d/%m/%Y') #fecha del pago
                        line += _date + ","
                        
                        # Campo 07 -- Monto sujeto a retencion len 12
                        amount = 0.00
                        for pay_line in payment.payment_ids:
                            if pay_line.payment_method_id.code == 'withholding':
                                amount = pay_line.withholding_base_amount
                        
                        amount_str = '{:.2f}'.format(amount)
                        #amount_str = amount_str.replace('.', ',')
                        line += amount_str.zfill(12) + ","
                        
                        # Campo 08 -- Alicuota len 6
                        amount_alicout = 0
                        for line_alicuot in payment.partner_id.arba_alicuot_ids:
                            if line_alicuot.tag_id.id == jurSIRCAR and rec.date_from >= line_alicuot.from_date and rec.date_to <= line_alicuot.to_date: 
                                amount_alicout = line_alicuot.alicuota_retencion
                        
                        amount_alicout_str = '{:.2f}'.format(amount_alicout)
                        #amount_alicout_str = amount_alicout_str.replace('.', ',')
                        line += amount_alicout_str.zfill(6) + ","
                        
                        # Campo 09 -- Monto Retenido len 12
                        currency = payment.company_id.currency_id
                        amount_total = (amount * amount_alicout) / 100
                        amount_total_round = currency.round(amount_total)
                        amount_total = '{:.2f}'.format(amount_total_round)
                        #amount_total = amount_total.replace('.', ',')
                        line += str(amount_total).zfill(12)  + ","
                        
                        # Campo 10 -- Tipo de régimen de retención len 3
                        type_reg_ret = '0'
                        for line_alicuot in payment.partner_id.arba_alicuot_ids:
                            if line_alicuot.tag_id.id == jurSIRCAR and rec.date_from >= line_alicuot.from_date and rec.date_to <= line_alicuot.to_date:
                                type_reg_ret = line_alicuot.regimen_retencion
                        
                        line += type_reg_ret.zfill(3) + ","
                        
                        # Campo 11 -- Jurisdicción len 3
                        line += tag_tax.jurisdiction_code

                        data.append(line)
                        nro_line += 1
                else:
                    # Diseño N°2
                    nro_line = 1
                    for payment in payments:
                        # Campo 01 -- Número de renglón len 5
                        line = str(nro_line).zfill(5) + ","
                        
                        # Campo 02 -- Origen del comprobante len 1
                        line += '1' + ","
                        
                        # Campo 03 -- Tipo de comprobante len 1
                        line += '1' + ","
                        
                        # Campo 04 -- Numero del comprobante len 12  
                        doc_name = payment.display_name.split(' ')
                        code_issue = 0
                        if len(doc_name) > 0:
                            doc_number = doc_name[1].split('-')
                            code_issue = doc_number[1]
                            
                        line += str(code_issue).zfill(12) + ","
                        
                        # Campo 05 -- Cuit contribuyente involucrado en la transacción comercial len 11
                        line += payment.partner_id.vat.zfill(11) + ","
                        
                        # Campo 06 -- Fecha de retencion len 10
                        _date = payment.payment_date.strftime('%d/%m/%Y') #fecha del pago
                        line += _date + ","
                        
                        # Campo 07 -- Monto sujeto a retencion len 12
                        amount = 0.00
                        for pay_line in payment.payment_ids:
                            if pay_line.payment_method_id.code == 'withholding':
                                amount = pay_line.withholding_base_amount
                        
                        amount_str = '{:.2f}'.format(amount)
                        #amount_str = amount_str.replace('.', ',')
                        line += amount_str.zfill(12) + ","
                        
                        # Campo 08 -- Alicuota len 6
                        amount_alicout = 0
                        for line_alicuot in payment.partner_id.arba_alicuot_ids:
                            if line_alicuot.tag_id.id == jurSIRCAR and rec.date_from >= line_alicuot.from_date and rec.date_to <= line_alicuot.to_date: 
                                amount_alicout = line_alicuot.alicuota_retencion
                        
                        amount_alicout_str = '{:.2f}'.format(amount_alicout)
                        #amount_alicout_str = amount_alicout_str.replace('.', ',')
                        line += amount_alicout_str.zfill(6) + ","
                        
                        # Campo 09 -- Monto Retenido len 12
                        currency = payment.company_id.currency_id
                        amount_total = (amount * amount_alicout) / 100
                        amount_total_round = currency.round(amount_total)
                        amount_total = '{:.2f}'.format(amount_total_round)
                        #amount_total = amount_total.replace('.', ',')
                        line += str(amount_total).zfill(12)  + ","
                        
                        # Campo 10 -- Tipo de régimen de retención len 3
                        type_reg_ret = '0'
                        for line_alicuot in payment.partner_id.arba_alicuot_ids:
                            if line_alicuot.tag_id.id == jurSIRCAR and rec.date_from >= line_alicuot.from_date and rec.date_to <= line_alicuot.to_date:
                                type_reg_ret = line_alicuot.regimen_retencion
                        
                        line += type_reg_ret.zfill(3) + ","
                        
                        # Campo 11 -- Jurisdicción len 3
                        line += tag_tax.jurisdiction_code + ","
                        
                        # Campo 12 -- Tipo de operacion len 1
                        line += '1' + ","
                        
                        # Campo 13 -- Fecha de emisión de constancia len 10
                        line += _date + ","
                        
                        # Campo 14 -- Número de constancia len 14
                        nro_const = '0'
                        for pay_line in payment.payment_ids:
                            if pay_line.payment_method_id.code == 'withholding':
                                nro_const = pay_line.withholding_number
                        
                        line += nro_const.zfill(14) + ","
                        
                        # Campo 15 -- Número de constancia original len 14
                        line += '0'.zfill(14)
                        
                        data.append(line)
                        nro_line += 1
                       
            elif tag_tax.jurisdiction_code == '906':
                # Percepciones Chaco
                invoices = self.get_perception_invoices(impSIRCAR, jurSIRCAR)
                data = []
                if tag_tax.jurisdiction_code != '904':
                    # Diseño N°1
                    nro_line = 1
                    for invoice in invoices:
                        
                        # Campo 01 -- Número de renglón len 5
                        cuit = self.env.company.vat.replace('-','')
                        line += str(cuit) 
                        
                        # Campo 02 -- Origen del comprobante len 1
                        line += invoice.name[3]

                        # Campo 03 -- comprobante
                        comprobante=invoice.name.replace('-', '')
                        line += str(comprobante) 
                        
                        # Campo 04 -- cuit del contribuyente
                        cuit_partner = invoice.partner_id.vat.zfill(11)
                        line += str(cuit_partner + ("     "))

                        # Campo 05 -- Nombre cliente
                        name_partner = invoice.partner_id.commercial_company_name
                        line += str(name_partner + ("     "))

                        # Campo 06 -- Fecha percepcion len 10
                        _date = invoice.invoice_date
                        day = str(_date.day) + ' ' if _date.day < 10 else str(_date.day)
                        month = str(_date.month) + ' ' if _date.month < 10 else str(_date.month)
                        year = str(_date.year)
                        formatted_date = f'{day}{month}{year}'
                        line += formatted_date



                       # Campo 07 -- Monto percibido len 12
                      amount_total = invoice.amount_by_group[1][1]
                      line += '{:011}'.format(int(amount_total * 100))
                        
                       
                        # Campo 8 -- Tipo de régimen de percepcion len 2
                        code_table = 0
                        for line_alicuot in invoice.partner_id.arba_alicuot_ids:
                            amount_alicout = line_alicuot.alicuota_percepcion
                            if amount_alicout == 3.5:
                                code_table = 1
                            elif amount_alicout == 2:
                                code_table = 2
                        
                        line += str(code_table)

                                              
                        # Campo 010 -- Monto sujeto a percepción len 9
                        if invoice.currency_id.id != invoice.company_id.currency_id.id:
                            amount = self.convert_currency(
                                invoice.amount_untaxed,
                                invoice.computed_currency_rate,
                                invoice.company_id.currency_id
                            )
                        else:
                            amount = invoice.amount_untaxed
                        amount_str = int(amount * 100)
                        line += f'{amount_str:09}'.replace('.','')
                        

                        #Campo 011 -- Alicuota len 4
                        amount_alicout = 0
                        for line_alicuot in invoice.partner_id.arba_alicuot_ids:
                            if line_alicuot.tag_id.id == jurSIRCAR and rec.date_from >= line_alicuot.from_date and rec.date_to <= line_alicuot.to_date: 
                                amount_alicout = line_alicuot.alicuota_percepcion
                                
                        amount_alicout_int = int(amount_alicout * 100)
                        amount_alicout_str = str(amount_alicout_int).zfill(4)
                        line += amount_alicout_str
                                                
                        data.append(line)
                        nro_line += 1
                else:
                    # Diseño N°2
                    nro_line = 1
                    for invoice in invoices:
                        # Campo 01 -- Número de renglón len 5
                        line = str(nro_line).zfill(5) + ","
                        
                        # Campo 02 -- Tipo de comprobante len 3
                        # Campo 03 -- Letra del comprobante len 1
                        # Campo 04 -- Numero del comprobante len 12  
                        code_prefix = '001'
                        code_letter = 'Z'
                        code_issue = '0'
                        doc_name = invoice.name.split(' ')
                        if len(doc_name) > 0:
                            doc_type = doc_name[0].split('-')
                            code_prefix = DOCUMENT_TYPES.get(doc_type[0],'001')
                            code_letter = doc_type[1]
                            code_issue = doc_name[1].replace('-','')[-12:]
                                                    
                        line += str(code_prefix) + ","
                        line += str(code_letter) + ","
                        line += str(code_issue).zfill(12) + ","
                        
                        # Campo 05 -- Cuit contribuyente involucrado en la transacción comercial len 11
                        line += invoice.partner_id.vat.zfill(11) + ","
                        
                        # Campo 06 -- Fecha percepcion len 10
                        _date = invoice.invoice_date.strftime('%d/%m/%Y')
                        line += _date + ","
                        
                        # Campo 07 -- Monto sujeto a percepción len 12
                        if invoice.currency_id.id != invoice.company_id.currency_id.id:
                            amount = self.convert_currency(
                                invoice.amount_untaxed,
                                invoice.computed_currency_rate,
                                invoice.company_id.currency_id
                            )
                        else:
                            amount = invoice.amount_untaxed
                        amount_str = '{:.2f}'.format(amount)
                        #amount_str = amount_str.replace('.', ',')
                        line += str(amount_str).zfill(12) + ","
                        
                        # Campo 08 -- Alicuota len 6
                        amount_alicout = 0
                        for line_alicuot in invoice.partner_id.arba_alicuot_ids:
                            if line_alicuot.tag_id.id == jurSIRCAR and rec.date_from >= line_alicuot.from_date and rec.date_to <= line_alicuot.to_date: 
                                amount_alicout = line_alicuot.alicuota_percepcion
                        
                        amount_alicout_str = '{:.2f}'.format(amount_alicout)
                        #amount_alicout_str = amount_alicout_str.replace('.', ',')
                        line += str(amount_alicout_str).zfill(6) + ","
                        
                        # Campo 09 -- Monto percibido len 12
                        currency = invoice.company_id.currency_id
                        amount_total = (amount * amount_alicout) / 100
                        amount_total_round = currency.round(amount_total)
                        amount_total = '{:.2f}'.format(amount_total_round)
                        #amount_total = amount_total.replace('.', ',')
                        line += str(amount_total).zfill(12) + ","

                        # Campo 10 -- Tipo de régimen de percepcion len 3
                        type_reg_perc = '0'
                        for line_alicuot in invoice.partner_id.arba_alicuot_ids:
                            if line_alicuot.tag_id.id == jurSIRCAR and rec.date_from >= line_alicuot.from_date and rec.date_to <= line_alicuot.to_date:
                                type_reg_perc = line_alicuot.regimen_percepcion
                        
                        line += type_reg_perc.zfill(3) + ","
                        
                        # Campo 11 -- Jurisdicción len 3
                        line += tag_tax.jurisdiction_code + ","
                        
                        # Campo 12 -- Tipo de operacion len 1
                        line += '1' + ","
                        
                        # Campo 13 -- Número de constancia original len 14
                        line += '0'.zfill(14)
                        
                        data.append(line)
                        nro_line += 1
            
                data.append('')
                rec.export_sircar_data = '\n'.join(data)
            
            else:
                # Percepciones Misiones
                invoices = self.get_perception_invoices(impSIRCAR, jurSIRCAR)
                data = []
                if tag_tax.jurisdiction_code != '904':
                    # Diseño N°1
                    nro_line = 1
                    for invoice in invoices:
                        # Campo 01 -- Fecha percepcion len 10
                        _date = invoice.invoice_date.strftime('%d-%m-%Y')
                        line += _date + ","

                        # Campo 02 -- Tipo de comprobante
                        voucher = {
                            '1' : 'FA_A',
                            '2' : 'FA_B',
                            '3' : 'RBO_A',
                            '4' : 'RBO_B',
                            '5' : 'NC_A',
                            '6' : 'NC_B',
                            '7' : 'ND_A',
                            '8' : 'ND_B'
                            }

                        if invoice.name[3] in voucher:
                            line += voucher[invoice.name[3]] + ","
 
                        # Campo 03 -- Numero de comprobante

                        number = invoice.name
                        line += number + ","

                        # Campo 04 -- Nombre o Razon Social

                        name_partner = invoice.partner_id.commercial_company_name
                        line += name_partner + ","

                        # Campo 05 -- cuit del contribuyente
                        cuit_partner = invoice.partner_id.vat.zfill(11)
                        formatted_cuit = f"{cuit_partner[:2]}-{cuit_partner[2:10]}-{cuit_partner[10]}"
                        line += formatted_cuit + ","

                        # Campo 06 -- Monto Total
                        amount_total = formatted_amount = "{:.2f}".format(invoice.amount_residual)
                        line += amount_total + ","

                        #Campo 07 -- Alicuota len 4
                        amount_alicout = 0
                        for line_alicuot in invoice.partner_id.arba_alicuot_ids:
                            if line_alicuot.tag_id.id == jurSIRCAR and rec.date_from >= line_alicuot.from_date and rec.date_to <= line_alicuot.to_date: 
                                amount_alicout = line_alicuot.alicuota_percepcion
                                
                        line += str(amount_alicout) + ",,,,"

                        data.append(line)
                        nro_line += 1
            
                data.append('')
                rec.export_sircar_data = '\n'.join(data)
