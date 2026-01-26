# -*- coding: utf-8 -*-

from odoo import fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

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
