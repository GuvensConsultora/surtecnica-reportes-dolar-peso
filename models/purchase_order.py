# -*- coding: utf-8 -*-

from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # Por qué: Permite al usuario elegir imprimir en pesos aunque la orden sea en USD
    print_in_pesos = fields.Boolean(
        string='Imprimir en Pesos',
        default=False,
        help='Si está marcado y la orden es en moneda extranjera, '
             'el PDF mostrará los valores convertidos a pesos.',
    )

    # Por qué: Campo relacionado necesario para los campos Monetary que usan currency_field
    # Patrón: Campo related para acceder a company_id.currency_id de forma directa
    company_currency_id = fields.Many2one(
        'res.currency',
        string='Moneda de la Compañía',
        related='company_id.currency_id',
        readonly=True,
    )

    # Por qué: Campos computados para mostrar valores en moneda de la compañía
    # Patrón: Computed fields con depends para recalcular cuando cambian los valores base
    amount_untaxed_pesos = fields.Monetary(
        string='Subtotal (Pesos)',
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

    @api.depends('amount_untaxed', 'amount_tax', 'amount_total', 'currency_id', 'company_id.currency_id', 'date_order')
    def _compute_amounts_pesos(self):
        """Calcula los montos en la moneda de la compañía usando la tasa de la fecha de la orden."""
        for order in self:
            # Por qué: Comparamos con company_currency_id (pesos) para detectar órdenes en USD
            if order.currency_id and order.company_id.currency_id and order.currency_id != order.company_id.currency_id:
                # Por qué: date_order es la fecha de la orden (la que importa para el TC)
                date = order.date_order or fields.Date.context_today(order)
                order.amount_untaxed_pesos = order.currency_id._convert(
                    order.amount_untaxed, order.company_id.currency_id, order.company_id, date)
                order.amount_tax_pesos = order.currency_id._convert(
                    order.amount_tax, order.company_id.currency_id, order.company_id, date)
                order.amount_total_pesos = order.currency_id._convert(
                    order.amount_total, order.company_id.currency_id, order.company_id, date)
            else:
                order.amount_untaxed_pesos = order.amount_untaxed
                order.amount_tax_pesos = order.amount_tax
                order.amount_total_pesos = order.amount_total

    def action_toggle_print_pesos(self):
        """Toggle para el smart button de impresión en pesos."""
        for order in self:
            order.print_in_pesos = not order.print_in_pesos

    def _is_foreign_currency(self):
        """Retorna True si la orden está en moneda extranjera."""
        self.ensure_one()
        return self.currency_id and self.company_id.currency_id and self.currency_id != self.company_id.currency_id
