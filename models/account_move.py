# -*- coding: utf-8 -*-

import copy
from odoo import api, fields, models
from odoo.tools.misc import formatLang


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Por qué: Permite al usuario elegir imprimir en pesos aunque la factura sea en USD
    print_in_pesos = fields.Boolean(
        string='Imprimir en Pesos',
        default=False,
        help='Si está marcado y la factura es en moneda extranjera, '
             'el PDF mostrará los valores convertidos a pesos.',
    )

    # Por qué: Campos computados para mostrar valores en moneda de la compañía
    # Patrón: Computed fields con depends para recalcular cuando cambian los valores base
    amount_untaxed_pesos = fields.Monetary(
        string='Base Imponible (Pesos)',
        compute='_compute_amounts_pesos',
        currency_field='company_currency_id',
    )
    amount_tax_pesos = fields.Monetary(
        string='Impuestos (Pesos)',
        compute='_compute_amounts_pesos',
        currency_field='company_currency_id',
    )
    amount_total_pesos = fields.Monetary(
        string='Total (Pesos)',
        compute='_compute_amounts_pesos',
        currency_field='company_currency_id',
    )

    @api.depends('amount_untaxed', 'amount_tax', 'amount_total', 'currency_id', 'company_currency_id', 'date')
    def _compute_amounts_pesos(self):
        """Calcula los montos en la moneda de la compañía usando la tasa de la fecha de factura."""
        for move in self:
            if move.currency_id and move.company_currency_id and move.currency_id != move.company_currency_id:
                date = move.date or fields.Date.context_today(move)
                move.amount_untaxed_pesos = move.currency_id._convert(
                    move.amount_untaxed, move.company_currency_id, move.company_id, date)
                move.amount_tax_pesos = move.currency_id._convert(
                    move.amount_tax, move.company_currency_id, move.company_id, date)
                move.amount_total_pesos = move.currency_id._convert(
                    move.amount_total, move.company_currency_id, move.company_id, date)
            else:
                move.amount_untaxed_pesos = move.amount_untaxed
                move.amount_tax_pesos = move.amount_tax
                move.amount_total_pesos = move.amount_total

    def action_toggle_print_pesos(self):
        """Toggle para el smart button de impresión en pesos."""
        for move in self:
            move.print_in_pesos = not move.print_in_pesos

    def _is_foreign_currency(self):
        """Retorna True si la factura está en moneda extranjera."""
        self.ensure_one()
        return self.currency_id and self.company_currency_id and self.currency_id != self.company_currency_id

    # ── Override l10n_ar ──────────────────────────────────────────────────
    # Por qué: l10n_ar.report_invoice_document (primary=True) usa este método
    # para obtener el dict de totales del reporte. Si print_in_pesos está activo,
    # interceptamos y devolvemos la versión convertida a pesos.
    def _l10n_ar_get_invoice_totals_for_report(self):
        result = super()._l10n_ar_get_invoice_totals_for_report()
        if self.print_in_pesos and self._is_foreign_currency():
            return self._convert_tax_totals_to_pesos(result)
        return result

    # ── Conversión de totales ─────────────────────────────────────────────
    def _convert_tax_totals_to_pesos(self, tax_totals_dict):
        """Convierte cualquier dict de tax_totals a moneda de la compañía.

        Por qué: Método reutilizable que sirve tanto para el override de l10n_ar
        como para el wrapper _get_tax_totals_pesos().
        Patrón: Deep copy para no mutar el dict original.
        """
        self.ensure_one()
        tax_totals = copy.deepcopy(tax_totals_dict)
        if not tax_totals:
            return tax_totals

        currency = self.currency_id
        company_currency = self.company_currency_id
        company = self.company_id
        date = self.date or fields.Date.context_today(self)

        def convert(amount):
            return currency._convert(amount, company_currency, company, date)

        def fmt(amount):
            return formatLang(self.env, amount, currency_obj=company_currency)

        # Totales globales
        if 'amount_total' in tax_totals:
            tax_totals['amount_total'] = convert(tax_totals['amount_total'])
            tax_totals['formatted_amount_total'] = fmt(tax_totals['amount_total'])

        if 'amount_untaxed' in tax_totals:
            tax_totals['amount_untaxed'] = convert(tax_totals['amount_untaxed'])
            tax_totals['formatted_amount_untaxed'] = fmt(tax_totals['amount_untaxed'])

        # Subtotales (base imponible por grupo)
        for subtotal in tax_totals.get('subtotals', []):
            subtotal['amount'] = convert(subtotal['amount'])
            subtotal['formatted_amount'] = fmt(subtotal['amount'])
            subtotal.pop('amount_company_currency', None)

        # Grupos de impuestos
        for groups in tax_totals.get('groups_by_subtotal', {}).values():
            for group in groups:
                if 'tax_group_amount' in group:
                    group['tax_group_amount'] = convert(group['tax_group_amount'])
                    group['formatted_tax_group_amount'] = fmt(group['tax_group_amount'])
                if 'tax_group_base_amount' in group:
                    group['tax_group_base_amount'] = convert(group['tax_group_base_amount'])
                    group['formatted_tax_group_base_amount'] = fmt(group['tax_group_base_amount'])
                group.pop('tax_group_amount_company_currency', None)
                group.pop('tax_group_base_amount_company_currency', None)

        # Por qué: Detalle de impuestos argentinos (RG 5614/2024 - Transparencia Fiscal)
        for detail in tax_totals.get('detail_ar_tax', []):
            if 'amount_tax' in detail:
                detail['amount_tax'] = convert(detail['amount_tax'])
                detail['formatted_amount_tax'] = fmt(detail['amount_tax'])

        return tax_totals

    def _get_tax_totals_pesos(self):
        """Wrapper de compatibilidad: convierte tax_totals estándar a pesos."""
        self.ensure_one()
        return self._convert_tax_totals_to_pesos(self.tax_totals or {})
