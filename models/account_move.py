# -*- coding: utf-8 -*-

from odoo import api, fields, models


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

    def _is_foreign_currency(self):
        """Retorna True si la factura está en moneda extranjera."""
        self.ensure_one()
        return self.currency_id and self.company_currency_id and self.currency_id != self.company_currency_id
