from odoo import api, fields, models, _
from odoo.tools import date_utils
from odoo.exceptions import UserError, ValidationError
from datetime import date, timedelta, datetime
import base64, calendar


WITHHOLDING = '1'
PERCEPTION = '2'
STANDARD_CODE = '029'

class AccountExportArciba(models.Model):
    _name = 'account.export.arciba'
    _description = 'Export file for Arciba'

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
            ('perc/with', 'Withholding/Perception'),
            ('credit_note', 'Credit Note')
        ],
        string="Type of file",
        default="perc/with"
    )
    tag_tax = fields.Many2one(
        'account.account.tag',
        string='Jurisdiction',
        default=lambda self: self._get_default_tag_tax(),
    )
    export_arciba_data = fields.Text(
        'File content'
    )
    export_arciba_file = fields.Binary(
        'Download File',
        compute="_compute_files",
        readonly=True,
    )
    export_arciba_filename = fields.Char(
        'File arciba',
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

    def _get_default_tag_tax(self):
        jusdiriction = self.env.ref('l10n_ar_ux.tag_tax_jurisdiccion_901')
        if not jusdiriction:
            raise ValidationError(_('The jurisdiction for CABA has not been found'))
        return jusdiriction

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
        for rec in self:
            month = rec.month
            year = int(rec.year)
            first_day = datetime(year=year, month=month, day=1).date()
            last_day = datetime(year=year, month=month, day=calendar.monthrange(year, month)[1]).date()
            rec.date_from = first_day
            rec.date_to = last_day

    @api.depends('export_arciba_data')
    def _compute_files(self):
        for rec in self:
            # filename Arciba_['nc', 'retper']_month_year.TXT
            if not rec.env.company.vat:
                raise UserError(_('You have not configured the CUIT for this company'))

            company_name = rec.env.company.name
            if rec.date_from and rec.date_to:
                _date = '%s_%s' % (rec.date_from.month, rec.date_from.year)
            else:
                _date = '000000'
            doc = ''
            if rec.doc_type == 'credit_note':
                doc = 'nc'
            else:
                doc = 'retper'
            filename = 'Arciba_%s_%s-%s.txt' % (doc, company_name, _date)
            rec.export_arciba_filename = filename
            if rec.export_arciba_data:
                rec.export_arciba_file = base64.encodebytes(
                    rec.export_arciba_data.encode('UTF-8')
                )
            else:
                rec.export_arciba_file = False

    def get_withholding_payments(self, imp_ret):
        """
        Obtains the supplier payments that are withholdings and
        that are in the selected period
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
                        if imp_ret in tax_line.tag_ids.ids:
                            if not pay in ret:
                                ret += pay

        return ret

    def get_perception_invoices(self, imp_perc, type):
        """
        Gets the customer invoices that have perceptions
        and that are in the selected period.
        """
        invoice_obj = self.env['account.move'].sudo()
        invoices = invoice_obj.search([
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('move_type', '=', type),
            ('state', '=', 'posted'),
            ('company_id', '=', self.company_id.id)
        ])

        per = invoice_obj
        for inv in invoices:
            for line in inv.invoice_line_ids:
                for tax in line.tax_ids:
                    for tax_line in tax.invoice_repartition_line_ids:
                        if imp_perc in tax_line.tag_ids.ids:
                            if not inv in per:
                                per += inv
        return per

    def compute_arciba_data(self):
        for record in self:
            data = []
            if record.doc_type == 'perc/with':
                # Retenciones
                payments = self.get_withholding_payments(record.tag_tax.id)
                line = ''
                for payment in payments:
                    # 01 - Tipo de operacion len(1)
                    line += WITHHOLDING
                    # 02 - Codigo de norma len(3)
                    line += STANDARD_CODE
                    # 03 - Fecha de Retencion len(10)
                    _date = payment.payment_date.strftime('%d/%m/%Y')
                    line += str(_date)[:10]
                    # 04 - Tipo de comprobante Origen len(2)
                    voucher_type = {
                        'invoice': '01',
                        'debit_note': '02',
                        'supplier_payment': '03',
                        'customer_payment': '04',
                        'receipt_invoice': '07'
                    }.get(payment.document_type_id.internal_type, '09')
                    line += voucher_type
                    # 05 - Letra del comprobante len(1)
                    line += ' '
                    # 06 - Nro del comprobante len(16)
                    doc_number = '0'
                    doc_name = payment.document_number
                    if len(doc_name) > 0:
                        doc_number = doc_name.replace('-','')

                    line += str(doc_number)[:16].zfill(16)
                    # 07 - Fecha del comprobante len(10)
                    line += str(_date)[:10]
                    # 08 - Monto del comprobante len(16)(2decimales)
                    amount_ret = 0
                    amount_base_ret = 0
                    for pay_line in payment.payment_ids:
                        if pay_line.payment_method_id.code == 'withholding':
                            for tax_line in pay_line.tax_withholding_id.invoice_repartition_line_ids:
                                if self.tag_tax.id in tax_line.tag_ids.ids:
                                    amount_base_ret = pay_line.withholding_base_amount
                                    amount_ret = pay_line.computed_withholding_amount

                    amount_ret_str = '{:.2f}'.format(amount_ret).replace('.', ',')
                    line += amount_ret_str[:16].zfill(16)

                    # 09 - Numero de Certificado Propio len(16)
                    line += doc_number
                    # 10 - Tipo del documento len(1)
                    identification_type = {
                        'CUIT': '3',
                        'CUIL': '2',
                        'CDI': '1'
                    }.get(payment.partner_id.l10n_latam_identification_type_id.name, ' ')
                    line += identification_type
                    # 11 - Numero de documento len(11)
                    line += payment.partner_id.vat[:11].zfill(11)
                    # 12 - Situacion IB len(1)
                    income_type = {
                        'local': '1',
                        'multilateral': '2',
                        'exempt': '4'
                    }.get(payment.partner_id.l10n_ar_gross_income_type, '5')
                    line += income_type
                    # 13 - Nro Inscripcion IB len(11)
                    if income_type in ['local', 'multilateral'] and not payment.partner_id.l10n_ar_gross_income_number:
                        raise UserError(_('The partner {} does not have gross income configured in Contacts -> Fiscal data'.format(payment.partner_id.name)))
                    if income_type not in ['local', 'multilateral']:
                        income_type_number = ''.zfill(11)
                    else:
                        income_type_number = payment.partner_id.l10n_ar_gross_income_number[:11].zfill(11)
                    line += income_type_number
                    # 14 - Situacion Frente al IVA len(1)
                    responsibility_type = {
                        'IVA Responsable Inscripto': 1,
                        'IVA Sujeto Exento': 3,
                        'Responsable Monotributo': 4
                    }.get(payment.partner_id.l10n_ar_afip_responsibility_type_id.name, 0)
                    line += str(responsibility_type)
                    # 15 - Razon Social len(30)
                    partner_name = payment.partner_id.name[:30].ljust(30)
                    line += partner_name
                    # 16 - Importe otros conceptos len(16)(2decimales)
                    line += '0,00'.zfill(16)
                    # 17 - Importe IVA len(16)
                    line += '0,00'.zfill(16)
                    # 18 - Monto Sujeto a retencion len(16)(2decimales)
                    amount_base_ret_str = '{:.2f}'.format(amount_base_ret).replace('.', ',')
                    line += amount_base_ret_str[:16].zfill(16)
                    # 19 - Alicuota len(5)(2decimales)
                    alicuot = payment.partner_id.arba_alicuot_ids.filtered(lambda line: line.from_date == record.date_from and line.to_date == record.date_to)
                    alicuota_ret_str = '{:.2f}'.format(alicuot.alicuota_retencion) if alicuot else '0,00'
                    alicuota_ret_str = alicuota_ret_str.replace('.', ',')
                    line += alicuota_ret_str[:5].zfill(5) if alicuot else '00,00'
                    # 20 - Retencion practicada len(16)(2decimales)
                    line += alicuota_ret_str[:16].zfill(16)
                    # 21 - Monto Total recibido len(16)
                    line += alicuota_ret_str[:16].zfill(16)
                    # 22 - Aceptacion len(1)
                    line += ' '
                    # 23 - Fecha Aceptacion len(10)
                    line += ' '.ljust(10)
                    print(len(line))
                    data.append(line)
                #Percepciones
                line = ''
                invoices = self.get_perception_invoices(record.tag_tax.id, 'out_invoice')
                for invoice in invoices:
                    # 01 - Tipo de operacion len(1)
                    line += PERCEPTION
                    # 02 - Codigo de norma len(3)
                    line += STANDARD_CODE
                    # 03 - Fecha de Retencion len(10)
                    _date_invoice = invoice.invoice_date.strftime('%d/%m/%Y')
                    line += str(_date_invoice)[:10]
                    # 04 - Tipo de comprobante Origen len(2)
                    voucher_type = {
                        'invoice': '01',
                    }.get(invoice.l10n_latam_document_type_id.internal_type, '09')
                    if voucher_type == 'invoice':
                        if invoice.l10n_latam_document_type_id.doc_code_prefix == 'FCE-A':
                            voucher_type = '10'
                    line += voucher_type
                    # 05 - Letra del comprobante len(1)
                    line += ' '
                    # 06 - Nro del comprobante len(16)
                    doc_number = '0'
                    doc_name = invoice.name.split(' ')
                    if len(doc_name) > 0:
                        doc_number = doc_name[1].replace('-','')

                    line += str(doc_number)[:16].zfill(16)
                    # 07 - Fecha del comprobante len(10)
                    line += str(_date_invoice)[:10]
                    # 08 - Monto del comprobante len(16)(2decimales)
                    amount = invoice.amount_untaxed
                    amount_str = '{:.2f}'.format(amount)
                    amount_str = str(amount_str).replace('.', ',')
                    line += amount_str[:16].zfill(16)

                    # 09 - Numero de Certificado Propio len(16)
                    line += ''.ljust(16)
                    # 10 - Tipo del documento len(1)
                    identification_type = {
                        'CUIT': '3',
                        'CUIL': '2',
                        'CDI': '1'
                    }.get(invoice.partner_id.l10n_latam_identification_type_id.name, ' ')
                    line += identification_type
                    # 11 - Numero de documento len(11)
                    line += invoice.partner_id.vat[:11].zfill(11)
                    # 12 - Situacion IB len(1)
                    income_type = {
                        'local': '1',
                        'multilateral': '2',
                        'exempt': '4'
                    }.get(invoice.partner_id.l10n_ar_gross_income_type, '5')
                    line += income_type
                    # 13 - Nro Inscripcion IB len(11)
                    income_type_number = invoice.partner_id.l10n_ar_gross_income_number[:11].zfill(11)
                    if income_type == 'exempt':
                        income_type_number = '0'.zfill(11)
                    line += income_type_number
                    # 14 - Situacion Frente al IVA len(1)
                    responsibility_type = {
                        'IVA Responsable Inscripto': 1,
                        'IVA Sujeto Exento': 3,
                        'Responsable Monotributo': 4
                    }.get(invoice.partner_id.l10n_ar_afip_responsibility_type_id.name, 0)
                    line += str(responsibility_type)
                    # 15 - Razon Social len(30)
                    partner_name = invoice.partner_id.name[:30].ljust(30)
                    line += partner_name
                    # 16 - Importe otros conceptos len(16)(2decimales)
                    amount_perceptions = 0
                    amount_iva = 0
                    for lines in invoice.invoice_line_ids:
                        for tax in lines.tax_ids:
                            tag_tax = tax.description.split()
                            if tag_tax[0] == 'Perc':
                                for tax_line in tax.invoice_repartition_line_ids:
                                    if record.tag_tax.id not in tax_line.tag_ids.ids:
                                        amount_perceptions += record._get_tax_amount(tax, invoice.amount_untaxed)
                            elif tag_tax[0] == 'IVA':
                                amount_iva += record._get_tax_amount(tax, invoice.amount_untaxed)
                    amount_perceptions_str = '{:.2f}'.format(amount_perceptions)
                    amount_perceptions_str = str(amount_perceptions_str).replace('.', ',')

                    line += amount_perceptions_str[:16].zfill(16)
                    # 17 - Importe IVA len(16)
                    amount_iva_str = '{:.2f}'.format(amount_iva)
                    amount_iva_str = str(amount_iva_str).replace('.', ',')
                    line += amount_iva_str[:16].zfill(16)
                    # 18 - Monto Sujeto a retencion len(16)(2decimales)
                    amount_untaxed_str = '{:.2f}'.format(invoice.amount_untaxed).replace('.', ',')
                    line += amount_untaxed_str[:14].zfill(16)
                    # 19 - Alicuota len(5)(2decimales)
                    alicuot = invoice.partner_id.arba_alicuot_ids.filtered(lambda line: line.from_date == record.date_from and line.to_date == record.date_to)
                    alicuota_ret_str = '{:.2f}'.format(alicuot.alicuota_retencion) if alicuot else '0,00'
                    alicuota_ret_str = alicuota_ret_str.replace('.', ',')
                    line += alicuota_ret_str[:5].zfill(5) if alicuot else '00,00'
                    # 20 - Retencion practicada len(16)(2decimales)
                    line += alicuota_ret_str[:16].zfill(16)
                    # 21 - Monto Total recibido len(16)
                    line += alicuota_ret_str[:16].zfill(16)
                    # 22 - Aceptacion len(1)
                    line += ' '
                    # 23 - Fecha Aceptacion len(10)
                    line += ' '.ljust(10)
                    data.append(line)
            else:
                line = ''
                invoices = record.get_perception_invoices(record.tag_tax.id, 'out_refund')
                for invoice in invoices:
                        # 01 - Tipo de operacion len(1)
                        line += PERCEPTION
                        # 02 - Nro NotaCredito de norma len(12)
                        doc_number = '0'
                        doc_name = invoice.name.split(' ')
                        doc_name = doc_name[1].split('-')
                        if len(doc_name) > 0:
                            doc_number = doc_name[1]
                        line += str(doc_number)[:12].zfill(12)
                        # 03 - Fecha de Retencion len(10)
                        _date_invoice = invoice.invoice_date.strftime('%d/%m/%Y')
                        line += str(_date_invoice)[:10]
                        # 04 - Tipo de comprobante Origen len(2)
                        amount = invoice.amount_untaxed
                        amount_str = '{:.2f}'.format(amount)
                        amount_str = str(amount_str).replace('.', ',')
                        line += amount_str[:16].zfill(16)
                        #05 - Nro Certificado Propio len(16)
                        line += '0'[:16].zfill(16)
                        #06 - Tipo de comprobante len(2)
                        voucher_type = {
                        'invoice': '01',
                        }.get(invoice.l10n_latam_document_type_id.internal_type, '09')
                        if voucher_type == 'invoice':
                            if invoice.l10n_latam_document_type_id.doc_code_prefix == 'FCE-A':
                                voucher_type = '10'
                        line += voucher_type
                        #07 - Letra del comprobante len(1)
                        line += ' '
                        #08 -Nro de comprobante
                        doc_number_name = '0'
                        doc_name_number = invoice.name.split(' ')
                        if len(doc_name_number) > 0:
                            doc_number_name = doc_name_number[1].replace('-','')
                        line += str(doc_number_name)[:16].zfill(16)
                        #09 - Nro de documento len(11)
                        line += invoice.partner_id.vat[:11].zfill(11)
                        #10 - Codigo de Norma len(3)
                        line += STANDARD_CODE
                        #11 - Fecha de retencion len(10)
                        line += str(_date_invoice)[:10]
                        #12 - Retencion/Percepcion a deducir len(16)(2decimales)
                        amount_perceptions = 0
                        for lines in invoice.invoice_line_ids:
                            for tax in lines.tax_ids:
                                tag_tax = tax.description.split()
                                if tag_tax[0] == 'Perc' or tag_tax[0] == 'Ret':
                                    for tax_line in tax.invoice_repartition_line_ids:
                                        if record.tag_tax.id not in tax_line.tag_ids.ids:
                                            amount_perceptions += record._get_tax_amount(tax, invoice.amount_untaxed)
                        amount_perceptions_str = '{:.2f}'.format(amount_perceptions)
                        amount_perceptions_str = str(amount_perceptions_str).replace('.', ',')
                        line += amount_perceptions_str[:16].zfill(16)
                        #13 - Alicuota len(5)(2decimales)
                        alicuot = invoice.partner_id.arba_alicuot_ids.filtered(lambda line: line.from_date == record.date_from and line.to_date == record.date_to)
                        alicuota_ret_str = '{:.2f}'.format(alicuot.alicuota_retencion) if alicuot else '0,00'
                        alicuota_ret_str = alicuota_ret_str.replace('.', ',')
                        line += alicuota_ret_str[:5].zfill(5) if alicuot else '00,00'
                        data.append(line)
            if data:
                record.export_arciba_data = '\r\n'.join(data)

    def _get_tax_amount(self, tax, amount_untaxed):
        amount_tax = 0
        if tax.amount_type == 'percent':
            amount_tax = (amount_untaxed * tax.amount) / 100
        else:
            amount_tax = tax.amount
        return amount_tax
