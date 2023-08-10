from odoo import models,fields, api, _
from ast import literal_eval
from odoo.exceptions import UserError, ValidationError


class AccountTax(models.Model):
    _inherit = "account.tax"

    _CUSTOM_IDENTIFIER_SELECTION = [
        ('income_tax', _('Income Tax Withholding')),
        ('vat_withholding', _('VAT Withholding')),
    ]

    custom_identifier = fields.Selection(selection=_CUSTOM_IDENTIFIER_SELECTION, string='Custom Identifier')

    @api.constrains('custom_identifier', 'company_id')
    def _check_unique_custom_identifier(self):
        for record in self:
            if record.custom_identifier and record.company_id:
                existing_records = self.env['account.tax'].search([
                    ('custom_identifier', '=', record.custom_identifier),
                    ('company_id', '=', record.company_id.id),
                    ('id', '!=', record.id)
                ])

                if existing_records:
                    raise ValidationError(_('There can be only one record with the custom identifier {} for the same company.'.format(record.custom_identifier)))

    def create_payment_withholdings(self, payment_group):
        payments = False
        moves_m = payment_group.to_pay_move_line_ids.filtered(
            lambda x: x.move_id.l10n_latam_document_type_id.doc_code_prefix in [
                'FA-M',
                'ND-M',
                'NC-M',
            ]
        )
        if moves_m:
            payments = self.create_withholding_type_m(payment_group)

        if payments:
            return payments
        else:
            return super(AccountTax, self).create_payment_withholdings(payment_group)

    def create_withholding_type_m(self, payment_group):
        # Get custom_taxes
        income_taxes, vat_taxes = self._get_taxes_for_payment_group(payment_group.company_id)

        withholding_totals = {}

        for move in payment_group.to_pay_move_line_ids:
            if move.move_id.l10n_latam_document_type_id.doc_code_prefix in [
                'FA-M',
                'ND-M',
                'NC-M',
            ]:
                for tax in income_taxes:
                    withholding_amount = (
                        move.move_id.amount_untaxed
                        * 0.06
                    )

                    if withholding_amount:
                        if tax.id in withholding_totals:
                            withholding_totals[tax.id] += withholding_amount
                        else:
                            withholding_totals[tax.id] = withholding_amount

                for tax in vat_taxes:
                    withholding_amount = (
                        move.move_id.amount_tax
                        * 1.0
                    )

                    if withholding_amount:
                        if tax.id in withholding_totals:
                            withholding_totals[tax.id] += withholding_amount
                        else:
                            withholding_totals[tax.id] = withholding_amount

        for tax_id, amount in withholding_totals.items():
            payment_withholding = self.env['account.payment'].search([
                ('payment_group_id', '=', payment_group.id),
                ('tax_withholding_id', '=', tax_id),
                ('automatic', '=', True),
            ], limit=1)

            if payment_withholding:
                payment_withholding.write({'amount': amount})
            else:
                move = payment_group.to_pay_move_line_ids[0].move_id
                journal = self.env['account.journal'].search([
                    ('company_id', '=', move.company_id.id),
                    ('outbound_payment_method_line_ids.payment_method_id.code', '=', 'withholding'),
                    ('type', 'in', ['cash', 'bank']),
                ], limit=1)

                if not journal:
                    raise UserError(
                        _('No journal for withholdings found on company %s')
                        % move.company_id.name
                    )

                payment_method_line_id = journal.outbound_payment_method_line_ids.filtered(
                    lambda x: x.code == 'withholding'
                ).mapped('id')[0]

                vals = {
                    'payment_group_id': payment_group.id,
                    'tax_withholding_id': tax_id,
                    'automatic': True,
                    'amount': amount,
                    'journal_id': journal.id,
                    'payment_method_line_id': payment_method_line_id,
                    'payment_type': 'outbound',
                    'partner_type': payment_group.partner_type,
                    'partner_id': payment_group.partner_id.id,
                }
                self.env['account.payment'].create(vals)

        return True

    def _get_taxes_for_payment_group(self, company_id):
        income_taxes = self.search([
            ('custom_identifier', '=', 'income_tax'),
            ('company_id', '=', company_id.id)
        ])

        vat_taxes = self.search([
            ('custom_identifier', '=', 'vat_withholding'),
            ('company_id', '=', company_id.id)
        ])

        if not income_taxes or not vat_taxes:
            raise UserError(_('Income Tax or VAT Withholding not found for the company. Please make sure you have set up the appropriate taxes.'))

        return income_taxes, vat_taxes
