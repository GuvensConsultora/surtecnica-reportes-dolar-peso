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

    @api.onchange('currency_id', 'company_id', 'invoice_date', 'date')
    def _onchange_currency_rate(self):
        """Actualiza el TC cuando cambia la moneda o la fecha."""
        for move in self:
            # Por qué: Solo actualizar si NO hay TC manual ya establecido (ej: viene del presupuesto)
            if not move.manual_currency_rate:
                if move.currency_id and move.company_currency_id and move.currency_id != move.company_currency_id:
                    # Por qué: Obtenemos el TC de la fecha actual
                    date = move.invoice_date or move.date or fields.Date.context_today(move)
                    # Convertimos 1 unidad de la moneda extranjera a pesos
                    move.manual_currency_rate = move.currency_id._convert(
                        1.0, move.company_currency_id, move.company_id, date)
                else:
                    move.manual_currency_rate = 0.0

    @api.depends('amount_untaxed', 'amount_tax', 'amount_total', 'currency_id', 'company_currency_id', 'invoice_date', 'date', 'manual_currency_rate')
    def _compute_amounts_pesos(self):
        """Calcula los montos en la moneda de la compañía usando la tasa manual o de la fecha de factura."""
        for move in self:
            if move.currency_id and move.company_currency_id and move.currency_id != move.company_currency_id:
                # Por qué: Si hay TC manual, lo usamos; sino usamos el automático de la fecha
                if move.manual_currency_rate:
                    # Conversión manual directa multiplicando por el TC
                    move.amount_untaxed_pesos = move.amount_untaxed * move.manual_currency_rate
                    move.amount_tax_pesos = move.amount_tax * move.manual_currency_rate
                    move.amount_total_pesos = move.amount_total * move.manual_currency_rate
                else:
                    # Conversión automática usando TC de la fecha
                    date = move.invoice_date or move.date or fields.Date.context_today(move)
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

    def action_post(self):
        """Override para registrar TC en chatter al validar factura."""
        # Por qué: Ejecutar validación estándar primero
        result = super(AccountMove, self).action_post()

        # Por qué: Registrar TC en chatter si es moneda extranjera
        for move in self:
            if move.manual_currency_rate and move._is_foreign_currency():
                # Por qué: Diferentes estilos para facturas de cliente vs proveedor
                if move.move_type in ('out_invoice', 'out_refund'):
                    alert_class = 'alert-warning'
                    icon = '📄'
                    doc_type = 'Factura de Cliente'
                else:
                    alert_class = 'alert-info'
                    icon = '📋'
                    doc_type = 'Factura de Proveedor'

                total_pesos = move.amount_total * move.manual_currency_rate
                fecha = move.invoice_date.strftime('%d/%m/%Y') if move.invoice_date else (move.date.strftime('%d/%m/%Y') if move.date else 'N/A')

                # Por qué: Usar Markup para que el HTML se renderice correctamente
                from markupsafe import Markup

                html_body = Markup(f"""<div class="alert {alert_class}" style="margin-bottom: 0;">
    <h5>{icon} <strong>{doc_type} Validada</strong></h5>
    <hr style="margin: 8px 0;"/>
    <table class="table table-sm table-borderless" style="margin-bottom: 0;">
        <tr>
            <td style="width: 40%;"><strong>Tipo de Cambio:</strong></td>
            <td><span class="badge badge-primary" style="font-size: 13px;">{move.manual_currency_rate:.4f}</span></td>
        </tr>
        <tr>
            <td><strong>Conversión:</strong></td>
            <td>{move.currency_id.name} → {move.company_currency_id.name}</td>
        </tr>
        <tr>
            <td><strong>Fecha:</strong></td>
            <td>{fecha}</td>
        </tr>
        <tr>
            <td><strong>Total Original:</strong></td>
            <td><strong>{move.currency_id.symbol} {move.amount_total:,.2f}</strong></td>
        </tr>
        <tr>
            <td><strong>Total en Pesos:</strong></td>
            <td><strong style="color: #28a745; font-size: 14px;">{move.company_currency_id.symbol} {total_pesos:,.2f}</strong></td>
        </tr>
    </table>
</div>""")

                move.message_post(
                    body=html_body,
                    subject="Validación con Tipo de Cambio"
                )

        return result

    # ── Override create/write para aplicar TC manual ──────────────────────
    # Por qué: Recalcular líneas contables cuando se crea/modifica con TC manual
    @api.model_create_multi
    def create(self, vals_list):
        """Override para aplicar TC manual después de crear la factura."""
        # Por qué: Primero crear la factura normalmente
        moves = super().create(vals_list)

        # Por qué: Luego recalcular líneas que tienen TC manual
        for move in moves:
            if move.manual_currency_rate and move._is_foreign_currency():
                move._apply_manual_currency_rate()

        return moves

    def write(self, vals):
        """Override para aplicar TC manual cuando se modifica."""
        result = super().write(vals)

        # Por qué: Si se modificó el TC manual, recalcular las líneas
        if 'manual_currency_rate' in vals:
            for move in self:
                if move.manual_currency_rate and move._is_foreign_currency():
                    move._apply_manual_currency_rate()

        return result

    def _apply_manual_currency_rate(self):
        """Aplica el TC manual a todas las líneas contables del move."""
        self.ensure_one()
        # Por qué: Recalcular balance de las líneas con amount_currency
        # Patrón: Usar with_context para evitar recursiones y write para triggear recálculos
        for line in self.line_ids.filtered(lambda l: l.amount_currency and l.currency_id == self.currency_id):
            # Por qué: Convertir amount_currency a moneda de compañía con TC manual
            balance = line.amount_currency * self.manual_currency_rate
            # Tip: Escribir solo balance, debit/credit se recalculan automáticamente
            line.with_context(check_move_validity=False).write({
                'balance': balance,
            })

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
        # Por qué: Usamos invoice_date (fecha del comprobante) para tomar el TC del día de emisión
        date = self.invoice_date or self.date or fields.Date.context_today(self)

        def convert(amount):
            # Por qué: Si hay TC manual, lo usamos para la conversión; sino usamos el TC nativo de Odoo
            if self.manual_currency_rate:
                return amount * self.manual_currency_rate
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

    # ── Override para registración contable con TC manual ─────────────────
    # Por qué: Recalcular debit/credit de las líneas usando TC manual antes de validar
    # Patrón: _recompute_dynamic_lines se llama antes de post para recalcular todo
    def _recompute_dynamic_lines(self, recompute_all_taxes=False, recompute_tax_base_amount=False):
        """Override para aplicar TC manual a las líneas contables."""
        # Por qué: Primero ejecutar el comportamiento estándar de Odoo
        result = super()._recompute_dynamic_lines(recompute_all_taxes, recompute_tax_base_amount)

        # Por qué: Si hay TC manual, recalcular debit/credit de las líneas en moneda extranjera
        for move in self:
            if move.manual_currency_rate and move._is_foreign_currency():
                # Por qué: Recalcular solo las líneas con amount_currency (en USD)
                for line in move.line_ids.filtered(lambda l: l.amount_currency and l.currency_id == move.currency_id):
                    # Por qué: Convertir amount_currency a moneda de compañía con TC manual
                    amount_company_currency = line.amount_currency * move.manual_currency_rate
                    # Tip: Asignación directa evita recursión, debit/credit según el signo
                    if amount_company_currency > 0:
                        line.debit = amount_company_currency
                        line.credit = 0.0
                    else:
                        line.debit = 0.0
                        line.credit = -amount_company_currency
                    # Por qué: balance es debit - credit
                    line.balance = line.debit - line.credit

        return result
