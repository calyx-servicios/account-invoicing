# pylint: disable=protected-access
import logging
from datetime import datetime

from odoo import http, SUPERUSER_ID, _
from odoo.http import request

_logger = logging.getLogger(__name__)


def get_invoice_values(data: dict) -> dict:
    """Prepares the values for the invoice creation.

    * Company: Mandatory (vat, name or id). [company]

    * Partner: Mandatory (vat, name or id). [partner]

    * Invoice Date: Optional (dd-mm-yyyy). Default is current date. [date]

    * Reference: Optional. Default is empty string. [ref]

    * Journal: Optional (code, name or id). Default is partner's default journal. [journal]

    * Document Type: Mandatory depending on the journal (code, name or id). [document_type]

    Args:
        data (dict): Data received from the external service.

    Returns:
        dict: Values for the invoice creation.
    """
    company = data.get("company")
    if not company:
        return {"error": "Company not found"}
    company = (
        request.env["res.company"]
        .with_user(SUPERUSER_ID)
        .search([])
        .filtered(
            lambda c: c.vat == str(company)
            or c.name.lower() == str(company).lower()
            or c.id == company
        )
    )
    if not company:
        return {"error": f"Company '{data.get('company')}' not found"}

    partner = data.get("partner")
    if not partner:
        return {"error": "Missing partner"}
    partner = (
        request.env["res.partner"]
        .with_user(SUPERUSER_ID)
        .search([])
        .filtered(
            lambda p: p.vat == str(partner)
            or p.name.lower() == str(partner).lower()
            or p.id == partner
        )
    )
    if not partner:
        return {"error": f"Partner '{data.get('partner')}' not found"}

    date = data.get("date")
    if date:
        date = datetime.strptime(date, "%d-%m-%Y").strftime("%Y-%m-%d")

    values = {
        "partner_id": partner.id,
        "ref": data.get("ref"),
        "move_type": "out_invoice",
        "company_id": company.id,
        "invoice_date": date,
    }

    journal = data.get("journal")
    if journal:
        journal = (
            request.env["account.journal"]
            .with_user(SUPERUSER_ID)
            .search([("type", "=", "sale"), ("company_id", "=", company.id)])
            .filtered(
                lambda j: j.code == str(journal)
                or j.name.lower() == str(journal).lower()
                or j.id == journal
            )
        )
        if not journal:
            return {"error": "Journal not found"}

        values["journal_id"] = journal.id
        if journal.l10n_latam_use_documents:
            document_type = data.get("document_type")
            if not document_type:
                return {"error": "Missing document type"}
            document_type = (
                request.env["l10n_latam.document.type"]
                .with_user(SUPERUSER_ID)
                .search([])
                .filtered(
                    lambda j: j.code == str(document_type)
                    or j.name.lower() == str(document_type).lower()
                    or j.id == document_type
                )
            )
            values["l10n_latam_document_type_id"] = document_type.id

    return values


def add_lines_to_invoice(invoice, lines: list, company: int) -> dict:
    """Adds the lines to the invoice.

    * Product: Mandatory (name or id). [product]

    * Quantity: Mandatory. [quantity]

    * Taxes: Optional (name or id). Default is product's taxes. If not taxes are found,
    and the product does not have a default tax, this will return an error.
    If more than one Argentinian IVA Tax Type is added, will return an error. [taxes[list]]

    * Price Unit: Optional. Default is product's list price. [price_unit]

    Args:
        invoice: account.move record.
        lines (list): List of dicts with the lines to add.
        company (int): Company ID.

    Returns:
        dict: error message or success.
    """
    l10n_latam_document_type_id = invoice.l10n_latam_document_type_id.id
    invoice = invoice.with_context(check_move_validity=False)
    for line in lines:
        product = line.get("product")
        if not product:
            return {"error": "An Invoice Line is missing the product"}
        product = (
            request.env["product.product"]
            .with_user(SUPERUSER_ID)
            .search([("company_id", "in", [company, False])])
            .filtered(
                lambda p, product=product: p.name.lower() == str(product).lower()
                or p.id == product
            )
        )
        if not product:
            return {"error": f"Product '{line.get('product')}' not found"}

        quantity = line.get("quantity")
        if not quantity:
            return {"error": "Missing quantity"}

        taxes = line.get("taxes")
        if not taxes and not product.taxes_id:
            return {"error": "Missing taxes"}

        tax_ids = []
        if taxes:
            for tax in taxes:
                tax_id = (
                    request.env["account.tax"]
                    .with_user(SUPERUSER_ID)
                    .search(
                        [
                            ("company_id", "=", invoice.company_id.id),
                            ("type_tax_use", "=", "sale"),
                        ]
                    )
                    .filtered(
                        lambda t, tax=tax: t.name.lower() == str(tax).lower()
                        or t.id == tax
                    )
                )
                if not tax_id:
                    return {"error": f"{tax} Not Found"}
                tax_ids.append(tax_id.id)

        tax_ids.extend(product.taxes_id.ids)
        tax_ids = list(set(tax_ids))

        vat_taxes = (
            request.env["account.tax"]
            .sudo()
            .browse(tax_ids)
            .filtered(lambda x: x.tax_group_id.l10n_ar_vat_afip_code)
        )
        if len(vat_taxes) > 1:
            return {
                "error": _(
                    "There must be one and only one VAT tax per line. "
                    'Check line with product "%s"'
                )
                % product.name
            }

        line_values = {
            "product_id": product.id,
            "quantity": quantity,
            "price_unit": line.get("price_unit") or product.lst_price,
            "tax_ids": [(6, 0, tax_ids)],
        }

        invoice.write({"invoice_line_ids": [(0, 0, line_values)]})
    invoice.write({"l10n_latam_document_type_id": l10n_latam_document_type_id})
    return {"success": True}


class ApiInvoiceControllers(http.Controller):
    @http.route(
        "/account/create/invoice",
        type="json",
        auth="jwt_cx_api_invoice_payments",
        methods=["POST"],
    )
    def create_invoice(self, **kwargs):
        """
        Create a draft invoice from a request.
        """
        values = get_invoice_values(kwargs)
        if values.get("error"):
            return values

        invoice = request.env["account.move"].with_user(SUPERUSER_ID).create(values)
        if not invoice:
            return {"error": "Invoice not created"}

        lines = kwargs.get("lines")
        if lines:
            res = add_lines_to_invoice(invoice, lines, values.get("company_id"))
            if res.get("error"):
                return res
        else:
            return {"error": "Missing invoice lines"}

        return {
            "result": "Invoice created in draft",
            "invoice_id": invoice.id,
            "invoice_number": invoice.display_name,
            "invoice_date": invoice.invoice_date,
            "invoice_amount": invoice.amount_total,
            "invoice_currency": invoice.currency_id.name,
            "invoice_state": invoice.state,
            "invoice_journal": invoice.journal_id.name,
            "invoice_partner": invoice.partner_id.name,
            "invoice_partner_vat": invoice.partner_id.vat,
        }
