# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Por qué: Permite al usuario elegir imprimir en pesos aunque el presupuesto sea en USD
    print_in_pesos = fields.Boolean(
        string='Imprimir en Pesos',
        default=False,
        help='Si está marcado y el presupuesto es en moneda extranjera, '
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

    # Por qué: Tipo de cambio para conversión a pesos
    # Se autocompleta con el TC de la fecha, pero el usuario puede modificarlo
    # tracking=True registra cambios en el chatter
    manual_currency_rate = fields.Float(
        string='Tipo de Cambio',
        digits=(12, 4),
        tracking=True,
        help='Tipo de cambio para convertir a pesos. '
             'Se autocompleta con el TC de la fecha, pero puede modificarse.',
    )

    @api.onchange('currency_id', 'company_id', 'date_order')
    def _onchange_currency_rate(self):
        """Actualiza el TC cuando cambia la moneda o la fecha."""
        for order in self:
            # Por qué: Solo actualizar si NO hay TC manual ya establecido
            # Esto permite que el usuario edite el TC sin que se sobrescriba al cambiar la fecha
            if not order.manual_currency_rate:
                if order.currency_id and order.company_id.currency_id and order.currency_id != order.company_id.currency_id:
                    # Por qué: Obtenemos el TC de la fecha actual
                    date = order.date_order or fields.Date.context_today(order)
                    # Convertimos 1 unidad de la moneda extranjera a pesos
                    order.manual_currency_rate = order.currency_id._convert(
                        1.0, order.company_id.currency_id, order.company_id, date)
                else:
                    order.manual_currency_rate = 0.0

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

    @api.depends('amount_untaxed', 'amount_tax', 'amount_total', 'currency_id', 'company_id.currency_id', 'date_order', 'manual_currency_rate')
    def _compute_amounts_pesos(self):
        """Calcula los montos en la moneda de la compañía usando la tasa manual o de la fecha del presupuesto."""
        for order in self:
            # Por qué: Comparamos con company_currency_id (pesos) para detectar presupuestos en USD
            if order.currency_id and order.company_id.currency_id and order.currency_id != order.company_id.currency_id:
                # Por qué: Si hay TC manual, lo usamos; sino usamos el automático de la fecha
                if order.manual_currency_rate:
                    # Conversión manual directa multiplicando por el TC
                    order.amount_untaxed_pesos = order.amount_untaxed * order.manual_currency_rate
                    order.amount_tax_pesos = order.amount_tax * order.manual_currency_rate
                    order.amount_total_pesos = order.amount_total * order.manual_currency_rate
                else:
                    # Conversión automática usando TC de la fecha
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
        """Retorna True si el presupuesto está en moneda extranjera."""
        self.ensure_one()
        return self.currency_id and self.company_id.currency_id and self.currency_id != self.company_id.currency_id

    def write(self, vals):
        """Override para registrar cambios de TC en el chatter inmediatamente."""
        # Por qué: Registrar el cambio de TC antes de guardar para comparar valores
        for order in self:
            if 'manual_currency_rate' in vals and order.manual_currency_rate != vals['manual_currency_rate']:
                old_rate = order.manual_currency_rate
                new_rate = vals['manual_currency_rate']
                # Ejecutar el write primero
                res = super(SaleOrder, order).write(vals)
                # Registrar en chatter después del cambio
                if old_rate and new_rate:
                    order.message_post(
                        body=f"Tipo de Cambio modificado: {old_rate:.4f} → {new_rate:.4f}",
                        subject="Cambio de Tipo de Cambio"
                    )
                elif new_rate:
                    order.message_post(
                        body=f"Tipo de Cambio establecido: {new_rate:.4f}",
                        subject="Tipo de Cambio"
                    )
                return res
        return super(SaleOrder, self).write(vals)

    def action_confirm(self):
        """Override para registrar TC en chatter al confirmar."""
        # Por qué: Ejecutar confirmación estándar primero
        result = super(SaleOrder, self).action_confirm()

        # Por qué: Registrar TC en chatter si es moneda extranjera
        for order in self:
            if order.manual_currency_rate and order._is_foreign_currency():
                total_pesos = order.amount_total * order.manual_currency_rate
                fecha = order.date_order.strftime('%d/%m/%Y') if order.date_order else 'N/A'

                # Por qué: Usar Markup para que el HTML se renderice correctamente
                from markupsafe import Markup

                html_body = Markup(f"""<div class="alert alert-success" style="margin-bottom: 0;">
    <h5>✓ <strong>Presupuesto Confirmado</strong></h5>
    <hr style="margin: 8px 0;"/>
    <table class="table table-sm table-borderless" style="margin-bottom: 0;">
        <tr>
            <td style="width: 40%;"><strong>Tipo de Cambio:</strong></td>
            <td><span class="badge badge-primary" style="font-size: 13px;">{order.manual_currency_rate:.4f}</span></td>
        </tr>
        <tr>
            <td><strong>Conversión:</strong></td>
            <td>{order.currency_id.name} → {order.company_currency_id.name}</td>
        </tr>
        <tr>
            <td><strong>Fecha:</strong></td>
            <td>{fecha}</td>
        </tr>
        <tr>
            <td><strong>Total Original:</strong></td>
            <td><strong>{order.currency_id.symbol} {order.amount_total:,.2f}</strong></td>
        </tr>
        <tr>
            <td><strong>Total en Pesos:</strong></td>
            <td><strong style="color: #28a745; font-size: 14px;">{order.company_currency_id.symbol} {total_pesos:,.2f}</strong></td>
        </tr>
    </table>
</div>""")

                order.message_post(
                    body=html_body,
                    subject="Confirmación con Tipo de Cambio"
                )

        return result

    def _prepare_invoice(self):
        """Override para copiar el TC del presupuesto a la factura."""
        # Por qué: Llamamos al método original para obtener los valores base
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        # Por qué: Copiamos el TC manual si existe
        if self.manual_currency_rate:
            invoice_vals['manual_currency_rate'] = self.manual_currency_rate
        return invoice_vals
