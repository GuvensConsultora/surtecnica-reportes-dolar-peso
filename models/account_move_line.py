# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # Por qué: Campo relacionado necesario para los campos Monetary que usan currency_field
    company_currency_id = fields.Many2one(
        'res.currency',
        string='Moneda de la Compañía',
        related='move_id.company_currency_id',
        readonly=True,
    )

    # Por qué: Campos para mostrar precio unitario y subtotal en pesos en el PDF
    price_unit_pesos = fields.Monetary(
        string='Precio Unit. (Pesos)',
        compute='_compute_amounts_pesos',
        currency_field='company_currency_id',
    )
    price_subtotal_pesos = fields.Monetary(
        string='Subtotal (Pesos)',
        compute='_compute_amounts_pesos',
        currency_field='company_currency_id',
    )

    @api.depends('price_unit', 'price_subtotal', 'currency_id', 'company_currency_id', 'move_id.invoice_date', 'move_id.date', 'move_id.manual_currency_rate')
    def _compute_amounts_pesos(self):
        """Calcula precio unitario y subtotal en moneda de la compañía."""
        for line in self:
            if line.currency_id and line.company_currency_id and line.currency_id != line.company_currency_id:
                # Por qué: Si hay TC manual, lo usamos; sino usamos el TC automático de la fecha
                if line.move_id.manual_currency_rate:
                    line.price_unit_pesos = line.price_unit * line.move_id.manual_currency_rate
                    line.price_subtotal_pesos = line.price_subtotal * line.move_id.manual_currency_rate
                else:
                    date = line.move_id.invoice_date or line.move_id.date or fields.Date.context_today(line)
                    line.price_unit_pesos = line.currency_id._convert(
                        line.price_unit, line.company_currency_id, line.company_id, date)
                    line.price_subtotal_pesos = line.currency_id._convert(
                        line.price_subtotal, line.company_currency_id, line.company_id, date)
            else:
                line.price_unit_pesos = line.price_unit
                line.price_subtotal_pesos = line.price_subtotal

    # ── Override l10n_ar ──────────────────────────────────────────────────
    # Por qué: l10n_ar reemplaza los spans de precio/subtotal con valores de
    # _l10n_ar_prices_and_taxes() (incluye/excluye IVA según reglas AR).
    # El template usa estos valores para display Y para current_subtotal.
    # Al convertir aquí, todo queda consistente (precios + subtotales acumulados).
    def _l10n_ar_prices_and_taxes(self):
        result = super()._l10n_ar_prices_and_taxes()
        move = self.move_id
        if move.print_in_pesos and move._is_foreign_currency():
            # Por qué: Si hay TC manual, lo usamos; sino usamos el TC automático de la fecha
            if move.manual_currency_rate:
                # Tip: Convertimos todas las claves monetarias del dict usando TC manual
                for key in ('price_unit', 'price_subtotal', 'price_total', 'vat_amount'):
                    if key in result:
                        result[key] = result[key] * move.manual_currency_rate
            else:
                currency = move.currency_id
                company_currency = move.company_currency_id
                company = move.company_id
                date = move.invoice_date or move.date or fields.Date.context_today(self)
                # Tip: Convertimos todas las claves monetarias del dict usando TC automático
                for key in ('price_unit', 'price_subtotal', 'price_total', 'vat_amount'):
                    if key in result:
                        result[key] = currency._convert(
                            result[key], company_currency, company, date)
        return result
