# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models, _
from odoo.tools import date_utils
from odoo.exceptions import UserError
from datetime import date, timedelta, datetime
import base64, calendar, logging

_logger = logging.getLogger(__name__)

# Diseno de registro de exportacion segun documento en la carpeta doc
WITHHOLDING = '6'
PERCEPTION = '7'

class AccountExportSicore(models.Model):
    _name = 'account.export.sicore'
    _description = 'Archivo de exportación para sicore'

    year = fields.Integer(
        default=lambda self: self._default_year(),
        help='año del periodo',
        string='Año'
    )
    month = fields.Integer(
        default=lambda self: self._default_month(),
        help='mes del periodo',
        string='Mes'
    )
    period = fields.Char(
        compute="_compute_period",
        string='Periodo'
    )
    quincena = fields.Selection(
        [('0', 'Mensual'),
         ('1', 'Primera'),
         ('2', 'Segunda')],
        default=0
    )
    doc_type = fields.Selection(
        [
            (WITHHOLDING, 'Retencion'),
            (PERCEPTION, 'Percepcion')
        ],
        string="Tipo de archivo",
        default="6"
    )
    date_from = fields.Date(
        'Desde',
        readonly=True,
        compute="_compute_dates"
    )
    date_to = fields.Date(
        'Hasta',
        readonly=True,
        compute="_compute_dates"
    )
    export_sicore_data = fields.Text(
        'Contenido archivo'
    )
    export_sicore_file = fields.Binary(
        'Descargar Archivo',
        compute="_compute_files",
        readonly=True,
    )
    export_sicore_filename = fields.Char(
        'Archivo sicore',
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

    @api.onchange('year', 'month', 'quincena', 'doc_type')
    def _compute_dates(self):
        """ Dado el mes y el año calcular el primero y el ultimo dia del
            periodo
        """
        for rec in self:
            # Las retenciones se hacen por mes
            if rec.doc_type == WITHHOLDING:
                rec.quincena = 0

            month = rec.month
            year = int(rec.year)

            _ds = fields.Date.to_date('%s-%.2d-01' % (year, month))
            _de = date_utils.end_of(_ds, 'month')

            if rec.quincena == '1':
                _ds = datetime(year, month, 1)
                _de = datetime(year, rec.month, 15)
            if rec.quincena == '2':
                _ds = datetime(year, month, 16)
                last_day = calendar.monthrange(year, rec.month)[1]
                _de = datetime(year, month, last_day)

            rec.date_from = _ds
            rec.date_to = _de

    @api.depends('export_sicore_data')
    def _compute_files(self):
        for rec in self:
            # segun vimos aca la afip espera "ISO-8859-1" en vez de utf-8
            # filename SICORE-30708346655-201901.TXT
            # Probamos con utf8 a ver que pasa.

            if not rec.env.company.vat:
                raise UserError(_('No tiene configurado el CUIT para esta compañia'))

            cuit = rec.env.company.vat
            if rec.date_from and rec.date_to:
                _date = '%s%s' % (rec.date_from.year, rec.date_from.month)
            else:
                _date = '000000'

            filename = 'SICORE-%s-%s.TXT' % (cuit, _date)
            rec.export_sicore_filename = filename
            if rec.export_sicore_data:
                rec.export_sicore_file = base64.encodebytes(
#                    rec.export_sicore_data.encode('ISO-8859-1'))
                    rec.export_sicore_data.encode('UTF-8'))
            else:
                rec.export_sicore_file = False

    def get_withholding_payments(self):
        """ Obtiene los pagos a proveedor que son retenciones y que
            estan en el periodo seleccionado
        """
        return self.env['account.payment'].search([
            ('payment_date', '>=', self.date_from),
            ('payment_date', '<=', self.date_to),
            ('state', '=', 'posted'),
            ('journal_id.inbound_payment_method_ids.code', '=', 'withholding')]
        )

    def get_perception_invoices(self):
        """ Obtiene las facturas de cliente que tienen percepciones y que
            estan en el periodo seleccionado.
        """

        # busco el id de la etiqueta que marca los impuestos de Ganancias
        name = 'Ret/Perc SICORE Aplicada'
        account_tag_obj = self.env['account.account.tag']
        percSICORE = account_tag_obj.search([('name', '=', name)]).id
        
        invoice_obj = self.env['account.move'].sudo()
        invoices = invoice_obj.search([
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('type', 'in', ['out_invoice','out_refund']),
            ('invoice_payment_state', '=', 'paid')
        ])
        
        ret = invoice_obj 
        
        for inv in invoices:
            for line in inv.invoice_line_ids:
                for tax in line.tax_ids:
                    for tax_line in tax.invoice_repartition_line_ids:
                        if percSICORE in tax_line.tag_ids.ids:
                            ret += inv
                            
        return ret

    def compute_sicore_data(self):
        line = ''
        for rec in self:
            if rec.doc_type == WITHHOLDING:
                # Retenciones
                payments = self.get_withholding_payments()
                data = []
                for payment in payments:

                    # Campo 01 -- Código de comprobante len 2
                    code = '1'
                    line = code.zfill(2)

                    # Campo 02 -- Fecha de emision del comprobante len 10
                    try:
                        payment_group = payment.payment_group_id
                        invoice = payment_group.matched_move_line_ids[0].move_id
                        _date = invoice.invoice_date.strftime('%d/%m/%Y')
                    except Exception as _ex:
                        raise UserError(
                            _('La linea %s del pago %s no tiene un comprobante '
                              'asociado. Posiblemente falte conciliar el comprobante '
                              'con este pago.') %
                              (payment.name, payment.payment_group_id.name)) from _ex
                    line += _date

                    # Campo 03 -- Numero comprobante len 16
                    _comprobante = invoice.l10n_latam_document_number.replace('-','')
                    line += _comprobante.rjust(16)

                    # Campo 04 -- Importe del comprobante len 16
                    amount = '{:.2f}'.format(invoice.amount_total)
                    amount = amount.replace('.', ',')
                    line += amount.zfill(16)

                    # Campo 05 Código de impuesto len 4
                    if not payment.tax_withholding_id:
                        raise UserError(
                            _('El elemento de pago %s que corresponde al grupo de '
                              'pagos %s no tiene retención asociada.\n'
                              'Sin embargo pertenece al diario %s el cual tiene tildada'
                              ' la opción retenciones.') %
                                (payment.name, payment.payment_group_id.name,
                                 payment.journal_id.name))
                    code = payment.tax_withholding_id.sicore_tax_code
                    if not code:
                        raise UserError(
                            _('El impuesto %s no tiene cargado el codigo de impuesto.') %
                                (payment.tax_withholding_id.name))
                    line += str(code).rjust(4) #TODO: ENTERO

                    # Campo 06 Código de régimen len 3
                    if not payment.payment_group_id.regimen_ganancias_id:
                        raise UserError(
                            _('El grupo de pago %s no tiene cargado el régimen de '
                              'ganancias.') % payment.payment_group_id.name)
                    code = payment.payment_group_id.regimen_ganancias_id.display_name
                    line += str(code).rjust(3) #TODO: ENTERO

                    # Campo 07 Código de operación len 1
                    code = '1' # 1 retencion 2 percepcion
                    line += code.zfill(1)

                    # Campo 08 Base de Cálculo len 14
                    amount = '{:.2f}'.format(invoice.amount_untaxed)
                    amount = amount.replace('.', ',')
                    line += amount.zfill(14)

                    # Campo 09 Fecha de emisión de la retención len 10
                    _date = payment.payment_date.strftime('%d/%m/%Y')
                    line += _date

                    # Campo 10 Código de condición len 2
                    code = '1'
                    line += code.zfill(2)

                    # Campo 11 Retención practicada a sujetos suspendidos según: len 1
                    line += ''.rjust(1)

                    # Campo 12 Importe de la retencion len 14
                    amount = '{:.2f}'.format(payment.amount)
                    amount = amount.replace('.', ',')
                    line += amount.zfill(14)

                    # Campo 13 Porcentaje de exclusión len 6
                    amount = '{:.2f}'.format(0)
                    amount = amount.replace('.', ',')
                    line += amount.zfill(6)

                    # Campo 14 Fecha publicación o de finalización de la vigencia len 10
                    _date = date.today().strftime('%d/%m/%Y')
                    line += _date

                    # Campo 15 Tipo de documento del retenido len 2
                    partner_id = payment.payment_group_id.partner_id
                    id_type = partner_id.l10n_latam_identification_type_id
                    code = id_type.l10n_ar_afip_code
                    line += str(code).zfill(2)

                    # Campo 16 Número de documento del retenido len 20
                    cuit = payment.payment_group_id.partner_id.vat
                    line += str(cuit).ljust(20)

                    # Campo 17 Número certificado original len 14
                    number = payment.withholding_number
                    line += number.zfill(14)
                    
                    # Campo 18 Denominación del ordenante len 30
                    line += "".rjust(30)
                    
                    # Campo 19 Acrecentamiento len 1
                    line += "0"
                    
                    # Campo 20 Cuit del país retenido len 11
                    line += "".zfill(11)
                    
                    # Campo 21 Cuit del ordenante len 11
                    line += "".zfill(11)
                    
                    data.append(line)
            else:
                #  Percepciones
                # traer todas las facturas con percepciones en el periodo
                invoices = self.get_perception_invoices()
                data = []
                for invoice in invoices:
                    # puede haber varios impuestos de percepcion en la factura
                    for line in invoice.invoice_line_ids:
                        for tax in line.tax_ids:
                            if tax.withholding_type == 'tabla_ganancias':
                                # Campo 01 -- Código de comprobante len 2
                                code = invoice.l10n_latam_document_type_id.code
                                line = code.zfill(2)
            
                                # Campo 02 -- Fecha de emision del comprobante len 10
                                _date = invoice.invoice_date.strftime('%d/%m/%Y')
                                line += _date
            
                                # Campo 03 -- Numero comprobante len 16
                                try:
                                    nro_comp = '0'
                                    data_name = invoice.name.split(' ')
                                    if len(data_name) > 1:
                                        nro_comp = data_name[1].replace('-','')
                                        line += nro_comp.rjust(16)
                                except Exception as _ex:
                                    raise UserError(_('El pago %s no tiene numero de '
                                                    'comprobante') % invoice.name) from _ex
            
                                # Campo 04 -- Importe del comprobante len 16
                                amount = '{:.2f}'.format(invoice.amount_total)
                                amount = amount.replace('.', ',')
                                line += amount.zfill(16)
            
                                # Campo 05 Código de impuesto len 4
                                code = str(tax.sicore_tax_code)
                                line += str(code).rjust(4)
            
                                # Campo 06 Código de régimen len 3
                                code = '94'
                                line += code.rjust(3)
            
                                # Campo 07 Código de operación len 1
                                code = '2'
                                line += code.zfill(1)
            
                                # Campo 08 Base de Cálculo len 14
                                amount = '{:.2f}'.format(invoice.amount_untaxed)
                                amount = amount.replace('.', ',')
                                line += amount.zfill(14)
            
                                # Campo 09 Fecha de emisión de la percepcion len 10
                                _date = date.today().strftime('%d/%m/%Y')
                                line += _date
            
                                # Campo 10 Código de condición len 2
                                code = invoice.partner_id.l10n_ar_afip_responsibility_type_id.code
                                line += code.zfill(2)
            
                                # Campo 11 Retención practicada a sujetos suspendidos según: len 1'
                                line += ''.zfill(1)
            
                                # Campo 12 Importe de la retencion len 14
                                amount = '{:.2f}'.format(tax.amount)
                                amount = amount.replace('.', ',')
                                line += amount.zfill(14)
            
                                # Campo 13 Porcentaje de exclusión len 6
                                amount = '{:.2f}'.format(0.0)
                                amount = amount.replace('.', ',')
                                line += amount.zfill(6)
            
                                # Campo 14 Fecha publicación o de finalización de la vigencia len 10
                                _date = '00/01/1900' #date.today().strftime('%d/%m/%Y')
                                line += _date
            
                                # Campo 15 Tipo de documento del retenido len 2
                                partner_id = invoice.partner_id
                                id_type = partner_id.l10n_latam_identification_type_id
                                code = id_type.l10n_ar_afip_code
                                line += str(code).zfill(2)
                                
                                # Campo 16 Número de documento del retenido len 20
                                cuit = invoice.partner_id.vat
                                line += str(cuit).ljust(20)
            
                                # Campo 17 Número certificado original len 14
                                number = '0'
                                line += number.zfill(14)
                                
                                # Campo 18 Denominación del ordenante len 30
                                line += "".rjust(30)
                                
                                # Campo 19 Acrecentamiento len 1
                                line += "0"
                                
                                # Campo 20 Cuit del país retenido len 11
                                line += "".zfill(11)
                                
                                # Campo 21 Cuit del ordenante len 11
                                line += "".zfill(11)
                                
                                data.append(line)
            
            rec.export_sicore_data = '\n'.join(data)

