from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    company_country_id = fields.Char(
        string="Country_id",
        related="company_id.country_id.code",
        help="Technical field used to hide/show fields regarding the localization",
    )

    @api.constrains("name", "journal_id", "state")
    def _check_unique_sequence_number(self):
        """
        THIS CONSTRAINT IS OVERRIDEN from l10n_latam_invoice_document to avoid 'use_documents' validation on localizations
        other than AR and CL
        """
        if self.company_country_id not in ["AR", "CL"]:
            vendor = self.filtered(lambda x: x.is_purchase_document())
        else:
            vendor = self.filtered(
                lambda x: x.is_purchase_document() and x.l10n_latam_use_documents
            )
        return super(AccountMove, self - vendor)._check_unique_sequence_number()

    @api.constrains("name", "partner_id", "company_id")
    def _check_unique_vendor_number(self):
        """THIS CONSTRAINT IS OVERRIDEN from l10n_latam_invoice_document to avoid 'use_documents' validation on localizations
        other than AR and CL"""
        if self.env.company.country_id.code not in ["AR", "CL"]:
            filtered_bills = self.filtered(
                lambda x: x.is_purchase_document() and x.commercial_partner_id
            )
        else:
            filtered_bills = self.filtered(
                lambda x: x.is_purchase_document()
                and x.l10n_latam_use_documents
                and x.l10n_latam_document_number
                and x.commercial_partner_id
            )
        for rec in filtered_bills:
            domain = [
                ("type", "=", rec.type),
                # by validating name we validate l10n_latam_document_number and l10n_latam_document_type_id
                ("name", "=", rec.name),
                ("company_id", "=", rec.company_id.id),
                ("id", "!=", rec.id),
                ("commercial_partner_id", "=", rec.commercial_partner_id.id),
            ]
            if rec.search(domain):
                raise ValidationError(
                    _("Vendor bill number must be unique per vendor and company.")
                )
