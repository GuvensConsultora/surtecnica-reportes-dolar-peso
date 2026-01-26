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
                # Por qué: Usamos la fecha de la factura para obtener la tasa de conversión correcta
                # Tip: _convert() es el método estándar de Odoo para conversión de moneda
                date = move.date or fields.Date.context_today(move)
                move.amount_untaxed_pesos = move.currency_id._convert(
                    move.amount_untaxed,
                    move.company_currency_id,
                    move.company_id,
                    date,
                )
                move.amount_tax_pesos = move.currency_id._convert(
                    move.amount_tax,
                    move.company_currency_id,
                    move.company_id,
                    date,
                )
                move.amount_total_pesos = move.currency_id._convert(
                    move.amount_total,
                    move.company_currency_id,
                    move.company_id,
                    date,
                )
            else:
                # Por qué: Si ya está en moneda local, usamos los valores directamente
                move.amount_untaxed_pesos = move.amount_untaxed
                move.amount_tax_pesos = move.amount_tax
                move.amount_total_pesos = move.amount_total

    def action_toggle_print_pesos(self):
        """Toggle para el smart button de impresión en pesos."""
        # Por qué: El stat button necesita un método object para alternar el valor
        # Patrón: Toggle simple, sin lógica adicional
        for move in self:
            move.print_in_pesos = not move.print_in_pesos

    def _is_foreign_currency(self):
        """Retorna True si la factura está en moneda extranjera."""
        self.ensure_one()
        return self.currency_id and self.company_currency_id and self.currency_id != self.company_currency_id

    def _get_tax_totals_pesos(self):
        """Retorna el dict tax_totals con montos convertidos a moneda de la compañía.

        Por qué: En Odoo 17 los totales de factura se renderizan desde un dict JSON (tax_totals),
        no con t-field individuales. Para mostrar en pesos, convertimos todo el dict.
        Patrón: Deep copy + conversión in-place para no mutar el original.
        """
        self.ensure_one()
        tax_totals = copy.deepcopy(self.tax_totals or {})
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

        # Grupos de impuestos
        for groups in tax_totals.get('groups_by_subtotal', {}).values():
            for group in groups:
                if 'tax_group_amount' in group:
                    group['tax_group_amount'] = convert(group['tax_group_amount'])
                    group['formatted_tax_group_amount'] = fmt(group['tax_group_amount'])
                if 'tax_group_base_amount' in group:
                    group['tax_group_base_amount'] = convert(group['tax_group_base_amount'])
                    group['formatted_tax_group_base_amount'] = fmt(group['tax_group_base_amount'])
                # Por qué: Eliminamos claves de moneda de compañía para evitar
                # que el bloque "company currency" muestre valores redundantes
                group.pop('tax_group_amount_company_currency', None)
                group.pop('tax_group_base_amount_company_currency', None)

        # Por qué: Igual para subtotales, ya estamos mostrando en moneda de compañía
        for subtotal in tax_totals.get('subtotals', []):
            subtotal.pop('amount_company_currency', None)

        return tax_totals
