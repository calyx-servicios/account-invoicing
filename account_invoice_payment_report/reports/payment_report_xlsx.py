# coding: utf-8
from datetime import datetime
from odoo import models, _


class PayrollReport(models.AbstractModel):
    _name = "report.account_invoice_payment_report.payment_report_xlsx"
    _inherit = "report.report_xlsx.abstract"

    def generate_xlsx_report(self, workbook, data, objs):

        #
        # Helper Method
        #
        def _format_date(date_utc_format):
            """Change the UTC format used by Odoo for dd-mm-yyyy

            Arguments:
                date_utc_format {str} -- Date UTC format yyyy-mm-dd

            Returns:
                str -- Date in dd-mm-yyyy format.
            """
            date_d_m_y_format = datetime.strptime(date_utc_format, '%Y-%m-%d').strftime('%d-%m-%Y')
            return date_d_m_y_format

        #
        # Formatting
        #
        heading_format = workbook.add_format({
            "align": "center",
            "valign": "vcenter",
            "bold": True,
            "size": 14,
            "bg_color": "#C8E6C9"
        })

        sub_heading_format = workbook.add_format({
            "align": "center",
            "valign": "vcenter",
            "bold": True,
            "size": 12,
            "bg_color": "#FFF9C4"
        })

        sub_heading_taxes_format = workbook.add_format({
            "align": "center",
            "valign": "vcenter",
            "bold": True,
            "size": 12,
            "bg_color": "#FFAB91"
        })

        center_format = workbook.add_format({
            "align": "center",
            "valign": "vcenter",
        })

        monetary_format = workbook.add_format({
            "num_format": "AR$ #,##0.00",
            "align": "center",
            "valign": "vcenter",
        })

        date_range_format = workbook.add_format({
            "align": "left",
            "bold": True,
            "size": 12,
            "bg_color": "#FFCCBC"
        })

        #
        # Adding Sheet
        #
        column = 0
        row = 0
        worksheet = workbook.add_worksheet(_("Payments"))

        #
        # Merging Columns and Rows
        #
        worksheet.merge_range("A1:C2", _("Invoice Payments Report"), heading_format)

        #
        # Dates Selected
        #
        trans_date_from = _("Date From")
        worksheet.write(row, column + 5, trans_date_from, date_range_format)
        worksheet.write(row, column + 6, _format_date(objs.date_from) or "")

        row += 1
        trans_date_to = _("Date To")
        worksheet.write(row, column + 5, trans_date_to, date_range_format)
        worksheet.write(row, column + 6, _format_date(objs.date_to) or "")

        #
        # Invoice query
        #
        invoice_objs = self.env['account.invoice'].search([
            ('date_invoice', '>=', objs.date_from),
            ('date_invoice', '<=', objs.date_to),
            ('state', '=', 'paid'),
            ('type', 'in', ['in_invoice', 'in_refund'])
        ])

        #
        # Column Titles
        #
        row += 2
        worksheet.write(row, column, "Fecha", sub_heading_format)
        column += 1
        worksheet.write(row, column, "Razón Social", sub_heading_format)
        column += 1
        worksheet.write(row, column, "Categoría AFIP", sub_heading_format)
        column += 1
        worksheet.write(row, column, "CUIT", sub_heading_format)
        column += 1
        worksheet.write(row, column, "Tipo Comprobante", sub_heading_format)
        column += 1
        worksheet.write(row, column, "N°", sub_heading_format)
        column += 1
        worksheet.write(row, column, "Importe No Gravado", sub_heading_format)
        column += 1
        worksheet.write(row, column, "Importe Neto Gravado 21%", sub_heading_format)
        column += 1
        worksheet.write(row, column, "Importe Neto Gravado 27%", sub_heading_format)
        column += 1
        worksheet.write(row, column, "Importe Neto Gravado 10.5%", sub_heading_format)

        # Taxes Columns
        taxes_columns = {}
        curr_column = column

        for invoice in invoice_objs:
            for taxe in invoice.tax_line_ids:
                if taxe.amount != 0.0:
                    if taxe.name not in taxes_columns:
                        curr_column += 1
                        taxes_columns.update({
                            taxe.name: curr_column
                        })

        for taxe in taxes_columns:
            column += 1
            worksheet.write(row, column, taxe, sub_heading_taxes_format)

        columns_added = len(taxes_columns)

        column += 1
        worksheet.write(row, column, "Total Comprobante", sub_heading_format)
        column += 1
        worksheet.write(row, column, "Fecha del Pago", sub_heading_format)
        column += 1
        worksheet.write(row, column, "Orden de Pago", sub_heading_format)
        column += 1
        worksheet.write(row, column, "Importe de Pago", sub_heading_format)
        column += 1
        worksheet.write(row, column, "Descrip. Prod.", sub_heading_format)
        column += 1
        worksheet.write(row, column, "Cuenta Analítica", sub_heading_format)
        column += 1
        worksheet.write(row, column, "Descrip. Cuenta", sub_heading_format)
        column += 1
        worksheet.write(row, column, "Servicio desde", sub_heading_format)
        column += 1
        worksheet.write(row, column, "Servicio hasta", sub_heading_format)
        column += 1

        #
        # Width of the Columns
        #
        for column in range(column):
            worksheet.set_column(row, column, 30)

        #
        # Invoices Manipulation
        #
        for invoice in invoice_objs:

            tax_0 = 0
            tax_21 = 0
            tax_27 = 0
            tax_10_5 = 0

            line_id_first = invoice.invoice_line_ids[0]

            for line in invoice.invoice_line_ids:
                for tax_line in line.invoice_line_tax_ids:
                    if tax_line.amount == 0.0:
                        tax_0 += line.price_subtotal
                    elif tax_line.amount == 21.0:
                        tax_21 += line.price_subtotal
                    elif tax_line.amount == 27.0:
                        tax_27 += line.price_subtotal
                    elif tax_line.amount == 10.5:
                        tax_10_5 += line.price_subtotal

            if invoice.currency_id.display_name != 'ARS':
                tax_21 *= invoice.currency_rate
                tax_27 *= invoice.currency_rate
                tax_10_5 *= invoice.currency_rate
                invoice_total = (invoice.amount_total * invoice.currency_rate)
            else:
                invoice_total = invoice.amount_total

            for payment in invoice.payment_group_ids:
                #
                # Writing row of invoice information for each payment group.
                #
                column = 0
                row += 1
                worksheet.write(row, column, _format_date(invoice.date_invoice), center_format)
                column += 1
                worksheet.write(row, column, invoice.partner_id.name, center_format)
                column += 1
                worksheet.write(row, column, invoice.partner_id.afip_responsability_type_id.name, center_format)
                column += 1
                worksheet.write(row, column, invoice.partner_id.formated_cuit, center_format)
                column += 1
                worksheet.write(row, column, invoice.document_type_id.doc_code_prefix, center_format)
                column += 1
                worksheet.write(row, column, invoice.document_number, center_format)
                column += 1
                if tax_0 != 0:
                    worksheet.write(row, column, tax_0, monetary_format)
                column += 1
                if tax_21 != 0:
                    worksheet.write(row, column, tax_21, monetary_format)
                column += 1
                if tax_27 != 0:
                    worksheet.write(row, column, tax_27, monetary_format)
                column += 1
                if tax_10_5 != 0:
                    worksheet.write(row, column, tax_10_5, monetary_format)

                for taxe in invoice.tax_line_ids:
                    for header, column_header in taxes_columns.items():
                        if taxe.name == header:
                            if taxe.amount == 0:
                                continue
                            if invoice.currency_id.display_name != 'ARS':
                                taxe_ars = taxe.amount * invoice.currency_rate
                                worksheet.write(row, column_header, taxe_ars, monetary_format)
                            else:
                                worksheet.write(row, column_header, taxe.amount, monetary_format)

                column += (columns_added + 1)
                worksheet.write(row, column, invoice_total, monetary_format)

                column += 1
                worksheet.write(row, column, _format_date(payment.payment_date), center_format)
                column += 1
                worksheet.write(row, column, payment.display_name, center_format)
                column += 1
                worksheet.write(row, column, payment.payments_amount, monetary_format)

                column += 1
                worksheet.write(row, column, line_id_first.name, center_format)
                column += 1
                worksheet.write(row, column, line_id_first.account_analytic_id.name, center_format)
                column += 1
                worksheet.write(row, column, line_id_first.account_id.display_name, center_format)

                if invoice.force_afip_concept in ["2", "3"]:
                    column += 1
                    worksheet.write(row, column, _format_date(invoice.afip_service_start), center_format)
                    column += 1
                    worksheet.write(row, column, _format_date(invoice.afip_service_end), center_format)
