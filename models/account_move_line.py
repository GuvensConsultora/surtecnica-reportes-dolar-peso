# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

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

    @api.depends('price_unit', 'price_subtotal', 'currency_id', 'company_currency_id', 'move_id.date')
    def _compute_amounts_pesos(self):
        """Calcula precio unitario y subtotal en moneda de la compañía."""
        for line in self:
            if line.currency_id and line.company_currency_id and line.currency_id != line.company_currency_id:
                date = line.move_id.date or fields.Date.context_today(line)
                line.price_unit_pesos = line.currency_id._convert(
                    line.price_unit,
                    line.company_currency_id,
                    line.company_id,
                    date,
                )
                line.price_subtotal_pesos = line.currency_id._convert(
                    line.price_subtotal,
                    line.company_currency_id,
                    line.company_id,
                    date,
                )
            else:
                line.price_unit_pesos = line.price_unit
                line.price_subtotal_pesos = line.price_subtotal
