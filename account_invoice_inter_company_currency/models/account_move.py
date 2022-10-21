from odoo import models, _
from odoo.tools import float_compare
from odoo.exceptions import UserError
from odoo.tests.common import Form

class AccountMove(models.Model):
    _inherit = "account.move"
    
    def _inter_company_create_invoice(self, dest_company):
        """ create an invoice for the given company : it will copy
                the invoice lines in the new invoice.
            :param dest_company : the company of the created invoice
            :rtype dest_company : res.company record
        """
        self.ensure_one()
        self = self.with_context(check_move_validity=False)
        # check intercompany product
        self._check_intercompany_product(dest_company)
        # if an invoice has already been generated
        # delete it and force the same number
        inter_invoice = self.search(
            [("auto_invoice_id", "=", self.id), ("company_id", "=", dest_company.id)]
        )
        force_number = False
        if inter_invoice and inter_invoice.state in ["draft", "cancel"]:
            force_number = inter_invoice.name
            inter_invoice.with_context(force_delete=True).unlink()
        # create invoice
        dest_invoice_data = self._prepare_invoice_data(dest_company)
        if force_number:
            dest_invoice_data["name"] = force_number
        dest_invoice = self.create(dest_invoice_data)
        
        #The intercompany module was not prepared to work with 
        #the account_ux module that returns the currency readonly.
        #For that reason this action is added.
        dest_invoice.currency_id = self.currency_id.id
        dest_invoice._onchange_currency()
        
        # create invoice lines
        dest_move_line_data = []
        for src_line in self.invoice_line_ids.filtered(lambda x: not x.display_type):
            if not src_line.product_id:
                raise UserError(
                    _(
                        "The invoice line '%s' doesn't have a product. "
                        "All invoice lines should have a product for "
                        "inter-company invoices."
                    )
                    % src_line.name
                )
            dest_move_line_data.append(
                src_line._prepare_account_move_line(dest_invoice, dest_company)
            )
        self.env["account.move.line"].create(dest_move_line_data)
        dest_invoice._move_autocomplete_invoice_lines_values()
        # Validation of account invoice
        precision = self.env["decimal.precision"].precision_get("Account")
        if dest_company.invoice_auto_validation and not float_compare(
            self.amount_total, dest_invoice.amount_total, precision_digits=precision
        ):
            dest_invoice.action_post()
        else:
            # Add warning in chatter if the total amounts are different
            if float_compare(
                self.amount_total, dest_invoice.amount_total, precision_digits=precision
            ):
                body = _(
                    "WARNING!!!!! Failure in the inter-company invoice "
                    "creation process: the total amount of this invoice "
                    "is %s but the total amount of the invoice %s "
                    "in the company %s is %s"
                ) % (
                    dest_invoice.amount_total,
                    self.name,
                    self.company_id.name,
                    self.amount_total,
                )
                dest_invoice.message_post(body=body)
        return {"dest_invoice": dest_invoice}

    def _prepare_invoice_data(self, dest_company):
        """ Generate invoice values
            :param dest_company : the company of the created invoice
            :rtype dest_company : res.company record
        """
        self.ensure_one()
        dest_inv_type = self._get_destination_invoice_type()
        dest_journal_type = self._get_destination_journal_type()
        # find the correct journal
        dest_journal = self.env["account.journal"].search(
            [("type", "=", dest_journal_type), ("company_id", "=", dest_company.id)],
            limit=1,
        )
        if not dest_journal:
            raise UserError(
                _('Please define %s journal for this company: "%s" (id:%d).')
                % (dest_journal_type, dest_company.name, dest_company.id)
            )
        # Use test.Form() class to trigger propper onchanges on the invoice
        dest_invoice_data = Form(
            self.env["account.move"].with_context(
                default_type=dest_inv_type, force_company=dest_company.id
            )
        )
        dest_invoice_data.journal_id = dest_journal
        dest_invoice_data.partner_id = self.company_id.partner_id
        dest_invoice_data.ref = self.name
        dest_invoice_data.invoice_date = self.invoice_date
        dest_invoice_data.narration = self.narration
        
        #The intercompany module was not prepared to work with 
        #the account_ux module that returns the currency readonly.
        #For this reason, this action must be changed.
        #dest_invoice_data.currency_id = self.currency_id
        
        vals = dest_invoice_data._values_to_save(all_fields=True)
        vals.update(
            {
                "invoice_origin": _("%s - Invoice: %s")
                % (self.company_id.name, self.name),
                "auto_invoice_id": self.id,
                "auto_generated": True,
            }
        )
        return vals

