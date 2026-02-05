# -*- coding: utf-8 -*-

from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # ── Campos para análisis de reportes ──────────────────────────────────
    product_categ_id = fields.Many2one(
        'product.category',
        string='Categoría de Producto',
        related='product_id.categ_id',
        store=True,
        readonly=True,
    )

    product_uom_id = fields.Many2one(
        'uom.uom',
        string='UdM del Producto',
        related='product_id.uom_id',
        store=True,
        readonly=True,
    )

    # ── Campos para impresión en pesos ────────────────────────────────────
    # Por qué: Campo relacionado necesario para los campos Monetary que usan currency_field
    company_currency_id = fields.Many2one(
        'res.currency',
        string='Moneda de la Compañía',
        related='order_id.company_id.currency_id',
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

    @api.depends('price_unit', 'price_subtotal', 'currency_id', 'company_id.currency_id', 'order_id.date_order')
    def _compute_amounts_pesos(self):
        """Calcula precio unitario y subtotal en moneda de la compañía."""
        for line in self:
            if line.currency_id and line.company_id.currency_id and line.currency_id != line.company_id.currency_id:
                date = line.order_id.date_order or fields.Date.context_today(line)
                line.price_unit_pesos = line.currency_id._convert(
                    line.price_unit, line.company_id.currency_id, line.company_id, date)
                line.price_subtotal_pesos = line.currency_id._convert(
                    line.price_subtotal, line.company_id.currency_id, line.company_id, date)
            else:
                line.price_unit_pesos = line.price_unit
                line.price_subtotal_pesos = line.price_subtotal
