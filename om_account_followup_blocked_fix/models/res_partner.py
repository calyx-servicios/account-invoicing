# -*- coding: utf-8 -*-

from functools import reduce
from lxml import etree

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.misc import formatLang


class ResPartner(models.Model):
    _inherit = "res.partner"

    def get_followup_table_html(self):
        """ Build the html tables to be included in emails send to partners,
            when reminding them their overdue invoices.
            :param ids: [id] of the partner for whom we are building the tables
            :rtype: string
        """
        self.ensure_one()
        partner = self.commercial_partner_id
        # copy the context to not change global context.
        # Overwrite it because _() looks for the
        # lang in local variable 'context'.
        # Set the language to use = the partner language
        followup_table = ''
        if partner.unreconciled_aml_ids:
            company = self.env.user.company_id
            current_date = fields.Date.today()
            report = self.env['report.om_account_followup.report_followup']
            final_res = report._lines_get_with_partner(partner, company.id)

            for currency_dict in final_res:
                currency = currency_dict.get('line', [
                    {'currency_id': company.currency_id}])[0]['currency_id']
                followup_table += '''
                <table border="2" width=100%%>
                <tr>
                    <td>''' + _("Invoice Date") + '''</td>
                    <td>''' + _("Description") + '''</td>
                    <td>''' + _("Reference") + '''</td>
                    <td>''' + _("Due Date") + '''</td>
                    <td>''' + _("Amount") + " (%s)" % (
                    currency.symbol) + '''</td> 
                </tr>'''

                total = 0
                lines_to_send = []
                for aml in currency_dict['line']:
                    if aml['blocked']:
                        #Si se indica en litigio el documento no se agrega al reporte/mail
                        continue
                    lines_to_send.append(aml)
                    block = aml['blocked'] and 'X' or ' '
                    total += aml['balance']
                    strbegin = "<TD>"
                    strend = "</TD>"
                    date = aml['date_maturity'] or aml['date']
                    if date <= current_date and aml['balance'] > 0:
                        strbegin = "<TD><B>"
                        strend = "</B></TD>"
                    followup_table += "<TR>" + strbegin + str(aml['date']) + \
                                      strend + strbegin + aml['name'] + \
                                      strend + strbegin + \
                                      (aml['ref'] or '') + strend + \
                                      strbegin + str(date) + strend + \
                                      strbegin + str(aml['balance']) + \
                                      strend + "</TR>"


                total = reduce(lambda x, y: x + y['balance'],lines_to_send, 0.00)
                total = formatLang(self.env, total, currency_obj=currency)
                followup_table += '''<tr> </tr>
                                </table>
                                <center>''' + _(
                    "Amount due") + ''' : %s </center>''' % (total)
        return followup_table
