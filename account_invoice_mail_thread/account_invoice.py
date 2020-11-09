##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import api, fields, models, _

class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail(self, auto_commit=False):
        context = self._context
        if context.get('default_model') == 'account.invoice' and \
                context.get('default_res_id') and context.get('mark_invoice_as_sent'):
            invoice = self.env['account.invoice'].browse(context['default_res_id'])
            if not invoice.sent:
                invoice.sent = True
            self = self.with_context(mail_post_autofollow=True)
            msg=''
            for partner in self.partner_ids:
                if len(msg)>0:
                    msg+=','
                msg=msg+partner.name+'<'+partner.email+'>'
            invoice.message_post(body=msg)
        return super(MailComposeMessage, self).send_mail(auto_commit=auto_commit)