# pylint: disable=protected-access
import logging
from datetime import datetime

from odoo import http, models, fields, SUPERUSER_ID, _
from odoo.http import request

_logger = logging.getLogger(__name__)


def get_invoice_values(data: dict) -> dict:
    """Prepares the values for the invoice creation.

    * Company: Mandatory (vat, name or id). [company]

    * Partner: Mandatory (vat, name or id). [partner]

    * Invoice Date: Optional (dd-mm-yyyy). Default is current date. [date]

    * Reference: Optional. Default is empty string. [ref]

    * Type: Optional. Default is 'out_invoice'. TODO: implement other types.

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
        "type": "out_invoice",
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


def add_lines_to_invoice(
    invoice: models.Model, lines: list, company: int
) -> dict or bool:
    """Adds the lines to the invoice.

    * Product: Mandatory (name or id). [product]

    * Quantity: Mandatory. [quantity]

    * Taxes: Optional (name or id). Default is product's taxes. If not taxes are found,
    and the product does not have a default tax, this will return an error.
    If more than one Argentinian IVA Tax Type is added, will return an error. [taxes[list]]

    * Price Unit: Optional. Default is product's list price. [price_unit]

    Args:
        invoice (models.Model): account.move record.
        lines (list): List of dicts with the lines to add.

    Returns:
        dict or bool: error message or success.
    """
    #FIXME: document_type is overwriten when adding lines
    l10n_latam_document_type_id = invoice.l10n_latam_document_type_id.id
    for line in lines:
        product = line.get("product")
        if not product:
            return {"error": "An Invoice Line is missing the product"}
        product = (
            request.env["product.template"]
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

        invoice.invoice_line_ids = [(0, 0, line_values)]
    invoice.update({"l10n_latam_document_type_id":l10n_latam_document_type_id})
    return {"success": True}


def create_payment_group(invoice: models.Model, context: dict) -> models.Model:
    """Creates the Payment Group for the given invoice.

    Args:
        invoice (models.Model): account.move record.
        context (dict): Context needed to create the Payment Group.

    Returns:
        models.Model: account.payment.group record.
    """
    _logger.info("Creating payment group for invoice %s", invoice.name)
    acc_pay_group = request.env["account.payment.group"].with_user(SUPERUSER_ID)
    vals = {
        "partner_id": context["default_partner_id"],
        "to_pay_move_line_ids": context["to_pay_move_line_ids"],
        "company_id": context["default_company_id"],
        "state": "draft",
        "partner_type": "customer",
    }
    pay_group = acc_pay_group.with_context(
        active_ids=invoice.id, active_model="account.move"
    ).create(vals)
    return pay_group


def create_payments(
    payments: list, payment_group: models.Model, invoice: models.Model, context: dict
) -> models.Model:
    """Creates the Payments for the given Payment Group.

    Args:
        payments (list): list of dictionaries with the payments data.
        payment_group (models.Model): account.payment.group record.
        invoice (models.Model): account.move record.
        context (dict): Context needed to create the Payments.

    Returns:
        models.Model: account.payment record.
    """
    _logger.info(
        "Creating payments for payment group of invoice %s",
        invoice.name,
    )
    acc_payment = request.env["account.payment"].with_user(SUPERUSER_ID)
    payment_context = {
        "active_ids": invoice.ids,
        "active_model": "account.move",
        "to_pay_move_line_ids": context.get("to_pay_move_line_ids"),
    }
    payment_context.update(context)
    for payment in payments:
        payment_vals = {
            # inmutable fields
            "company_id": invoice.company_id,
            "partner_id": invoice.partner_id.id,
            "payment_type": "inbound",
            "partner_type": "customer",
            "payment_group_id": payment_group.id,
            # payment specific fields
            "journal_id": payment.get("journal"),
            "amount": payment.get("amount"),
            "currency_id": payment.get("currency"),
            "payment_date": payment.get("date"),
            "communication": payment.get("communication"),
            "payment_method_id": payment.get("payment_method_id"),
        }
        acc_payment = acc_payment.with_context(**payment_context).create(payment_vals)
    return acc_payment


def create_and_post_payments(payments: list, invoice: models.Model) -> models.Model:
    """Creates and post the Payment Group for the given invoice.

    * Journal: Mandatory (code, name or id). [journal]

    * Currency: Optional (name). Default is invoice's currency. [currency]

    * Amount: Optional. Default is invoice's total. [amount]

    * Date: Optional. Default is current date. [date]

    * Communication: Optional. Default is empty string. [communication]

    Args:
        payments (list): list of dictionaries with the payments data.
        invoice (models.Model): account.move record.

    Returns:
        models.Model: account.payment.group record.
    """
    payments_data = []
    for payment in payments:
        payment_journal = payment.get("journal")
        if not payment_journal:
            return {"error": "Missing payment journal"}
        payment_journal = (
            request.env["account.journal"]
            .with_user(SUPERUSER_ID)
            .search([("company_id", "=", invoice.company_id.id)])
            .filtered(
                lambda j, payment_journal=payment_journal: j.code
                == str(payment_journal)
                or j.name.lower() == str(payment_journal).lower()
                or j.id == payment_journal
            )
        )
        currency = payment.get("currency")
        if not currency:
            currency = invoice.currency_id
        else:
            currency = (
                request.env["res.currency"]
                .with_user(SUPERUSER_ID)
                .search([("name", "=", currency)])
            )
        payments_data.append(
            {
                "journal": payment_journal.id,
                "amount": payment.get("amount") or invoice.amount_total,
                "currency": currency.id,
                "date": payment.get("date") or fields.Date.today(),
                "communication": payment.get("communication"),
                "payment_method_id": request.env.ref(
                    "account.account_payment_method_manual_in"
                ).id,
            }
        )

    payment_context = invoice.with_context(
        active_ids=invoice,
        active_model="account.move",
    ).action_account_invoice_payment_group()["context"]

    payment_group = create_payment_group(invoice, payment_context)
    payments = create_payments(payments_data, payment_group, invoice, payment_context)

    # Compute Methods and Post Payments
    ## Payment Group compute methods
    payment_group._compute_payments_amount()
    payment_group._compute_matched_amounts()
    payment_group._compute_document_number()
    payment_group._compute_matched_amount_untaxed()
    payment_group._compute_move_lines()
    ## Individual Payments compute methods
    for payment in payment_group.payment_ids:
        payment._onchange_partner_id()
        payment._compute_reconciled_invoice_ids()
        payment.post()
    payment_group.post()

    return payment_group


def post_invoices(invoices: models.Model) -> models.Model:
    """In case special invoice posting is required or multiple invoices created

    Args:
        invoices (models.Model): account.move

    Returns:
        models.Model: account.move
    """
    invoices.action_post()


class ApiInvoicePaymentsControllers(http.Controller):
    @http.route(
        "/account/create/invoice",
        type="json",
        auth="jwt_cx_api_invoice_payments",
        methods=["POST"],
        website=True,
    )
    def create_invoice(self, **kwargs):
        """
        Create an invoice from a request.
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

        posted_invoices = post_invoices(invoice)

        res = {
            "result": "Invoice created",
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

        # Create payments if any
        payments = kwargs.get("payments")
        if payments:
            payment_group = create_and_post_payments(payments, invoice)
            if isinstance(payment_group, dict) and payment_group.get("error"):
                return payment_group
            res["result"] = "Invoice created and payments posted"
            res["payment_group_id"] = payment_group.id
            res["payment_group_number"] = payment_group.display_name
            res["payment_group_amount"] = payment_group.payments_amount
            res["payment_group_state"] = payment_group.state

        return res
