# Reportes Dólar/Peso - Surtecnica

**Módulo para Odoo 17.0**

## Resumen Ejecutivo

Este módulo permite a empresas argentinas que trabajan con moneda extranjera (principalmente USD) imprimir sus documentos comerciales mostrando valores convertidos a pesos argentinos (ARS), sin modificar los datos contables originales.

**Funcionalidades principales:**

1. **Análisis de Órdenes de Compra**: Vista lista y pivot de líneas de orden de compra con agrupaciones por categoría, proveedor, moneda, etc.
2. **Impresión de Facturas en Pesos**: Facturas en USD que se imprimen mostrando valores en ARS
3. **Impresión de Presupuestos de Venta en Pesos**: Presupuestos en USD que se imprimen en ARS
4. **Impresión de Presupuestos de Compra en Pesos**: Órdenes de compra en USD que se imprimen en ARS

---

## Tabla de Contenidos

- [Instalación](#instalación)
- [Parte 1: Análisis de Órdenes de Compra](#parte-1-análisis-de-órdenes-de-compra)
- [Parte 2: Impresión de Facturas en Pesos](#parte-2-impresión-de-facturas-en-pesos)
- [Parte 3: Impresión de Presupuestos en Pesos](#parte-3-impresión-de-presupuestos-en-pesos)
- [Arquitectura Técnica](#arquitectura-técnica)
- [Flujos de Uso](#flujos-de-uso)
- [Buenas Prácticas Aplicadas](#buenas-prácticas-aplicadas)

---

## Instalación

### Dependencias

```python
'depends': ['purchase', 'account', 'sale', 'l10n_ar']
```

- **purchase**: Órdenes de compra
- **account**: Facturas y contabilidad
- **sale**: Presupuestos de venta
- **l10n_ar**: Localización Argentina (crítico para facturas)

### Instalación

1. Copiar el módulo en la carpeta `addons/`
2. Actualizar lista de aplicaciones
3. Instalar "Reportes Dólar/Peso - Surtecnica"

---

## PARTE 1: Análisis de Órdenes de Compra

### Objetivo

Facilitar el análisis de compras mediante vistas personalizadas que muestren información agregada de las líneas de orden de compra.

### Modelo: `purchase.order.line`

**Archivo:** `models/purchase_order_line.py`

#### Campos Agregados

```python
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
```

**Por qué:**
- Son campos **relacionados** que traen información del producto
- `store=True` almacena en BD para consultas rápidas sin joins
- Permiten agrupaciones en reportes pivot
- `readonly=True` porque no se deben modificar directamente

### Vistas

**Archivo:** `views/purchase_order_line_views.xml`

#### 1. Vista Lista (Tree)

Muestra todas las líneas de compra en formato tabla con:
- Orden, fecha, proveedor
- Categoría y producto
- Cantidad, unidad de medida
- Precio unitario, subtotal
- Estado

**Características:**
- Suma automática de cantidad total y subtotal
- Ordenado por fecha descendente

#### 2. Vista Pivot

Análisis multidimensional tipo tabla dinámica:

**Agrupaciones disponibles:**
- Por fila: Moneda, Proveedor, Categoría, Producto, Unidad
- Por columna: Fecha planificada (por mes)
- Medidas: Cantidad, Subtotal

**Ejemplo de uso:**
Analizar cuánto se compró de cada categoría por proveedor en cada mes.

#### 3. Vista Search/Filtros

**Filtros predefinidos:**
- Borrador
- Confirmadas
- Realizadas

**Agrupaciones:**
- Por moneda
- Por proveedor
- Por categoría de producto
- Por producto
- Por unidad de medida
- Por estado
- Por fecha prevista

### Menú de Acceso

**Ubicación:** Compras → Informes → Líneas de Compra

**Configuración por defecto:**
- Muestra solo órdenes confirmadas
- Vista lista primero, pivot disponible

---

## PARTE 2: Impresión de Facturas en Pesos

### Objetivo

Permitir imprimir facturas que están en USD mostrando todos los valores convertidos a pesos argentinos en el PDF, respetando el tipo de cambio de la fecha de factura.

### Problema que Resuelve

**Escenario:**
- Empresa argentina compra/vende en USD
- Contabilidad se lleva en USD
- Clientes/proveedores necesitan ver valores en pesos
- No se pueden duplicar facturas (problema fiscal)

**Solución:**
Smart button que activa conversión visual en el PDF sin tocar los datos contables.

### Modelo: `account.move`

**Archivo:** `models/account_move.py`

#### Campo Principal: `print_in_pesos`

```python
print_in_pesos = fields.Boolean(
    string='Imprimir en Pesos',
    default=False,
    help='Si está marcado y la factura es en moneda extranjera, '
         'el PDF mostrará los valores convertidos a pesos.',
)
```

**Por qué:**
- Control manual del usuario
- Solo afecta al PDF, no a los datos
- Default False para mantener comportamiento estándar

#### Campos Computados

```python
amount_untaxed_pesos = fields.Monetary(
    string='Base Imponible (Pesos)',
    compute='_compute_amounts_pesos',
    currency_field='company_currency_id',  # Usa campo nativo de account.move
)
amount_tax_pesos = fields.Monetary(...)
amount_total_pesos = fields.Monetary(...)
```

**Nota:** `account.move` ya tiene el campo `company_currency_id` de forma nativa en Odoo 17.

**Método de cálculo:**

```python
@api.depends('amount_untaxed', 'amount_tax', 'amount_total',
             'currency_id', 'company_currency_id', 'invoice_date', 'date')
def _compute_amounts_pesos(self):
    for move in self:
        if move.currency_id != move.company_currency_id:
            date = move.invoice_date or move.date
            move.amount_untaxed_pesos = move.currency_id._convert(
                move.amount_untaxed,
                move.company_currency_id,
                move.company_id,
                date
            )
            # ... igual para tax y total
```

**Por qué invoice_date:**
Es la fecha oficial del comprobante fiscal, determina el tipo de cambio legal a aplicar.

**Patrón:** Computed fields con `@api.depends()` para recalcular automáticamente cuando cambian los valores base.

#### Método: `_convert_tax_totals_to_pesos()`

**Propósito:**
Convertir toda la estructura de impuestos (`tax_totals`) de USD a ARS.

**¿Qué contiene tax_totals?**
- Totales generales (base, impuestos, total)
- Subtotales por grupo
- Grupos de impuestos (IVA 21%, IVA 10.5%, etc.)
- Detalles fiscales argentinos (RG 5614/2024)

**Implementación:**

```python
def _convert_tax_totals_to_pesos(self, tax_totals_dict):
    self.ensure_one()
    tax_totals = copy.deepcopy(tax_totals_dict)  # No mutar original

    currency = self.currency_id
    company_currency = self.company_currency_id
    date = self.invoice_date or self.date

    def convert(amount):
        return currency._convert(amount, company_currency, self.company_id, date)

    def fmt(amount):
        return formatLang(self.env, amount, currency_obj=company_currency)

    # Convertir totales generales
    tax_totals['amount_total'] = convert(tax_totals['amount_total'])
    tax_totals['formatted_amount_total'] = fmt(tax_totals['amount_total'])

    # Convertir subtotales, grupos de impuestos, detalles AR...
    # (ver código completo en models/account_move.py)

    return tax_totals
```

**Patrón:** Deep copy para no mutar el diccionario original (inmutabilidad).

**Tip:** Método reutilizable que sirve para cualquier diccionario de tax_totals.

#### Override de Localización Argentina

```python
def _l10n_ar_get_invoice_totals_for_report(self):
    result = super()._l10n_ar_get_invoice_totals_for_report()
    if self.print_in_pesos and self._is_foreign_currency():
        return self._convert_tax_totals_to_pesos(result)
    return result
```

**Por qué este override es crítico:**
- `l10n_ar.report_invoice_document` tiene `primary=True`
- Es el template que realmente renderiza PDFs en Argentina
- Heredar de `account.report_invoice_document` NO funcionaría

**Patrón:** Override defensivo
1. Llama primero al método original (respeta otras customizaciones)
2. Solo modifica si es necesario (condicional)
3. Devuelve original si no aplica

### Modelo: `account.move.line`

**Archivo:** `models/account_move_line.py`

#### Campos por Línea

```python
price_unit_pesos = fields.Monetary(
    string='Precio Unit. (Pesos)',
    compute='_compute_amounts_pesos',
    currency_field='company_currency_id',
)
price_subtotal_pesos = fields.Monetary(...)
```

**Por qué a nivel de línea:**
Para mostrar cada producto con su precio en pesos en el PDF.

#### Override: `_l10n_ar_prices_and_taxes()`

```python
def _l10n_ar_prices_and_taxes(self):
    result = super()._l10n_ar_prices_and_taxes()
    move = self.move_id
    if move.print_in_pesos and move._is_foreign_currency():
        currency = move.currency_id
        company_currency = move.company_currency_id
        date = move.invoice_date or move.date

        for key in ('price_unit', 'price_subtotal', 'price_total', 'vat_amount'):
            if key in result:
                result[key] = currency._convert(
                    result[key], company_currency, move.company_id, date)
    return result
```

**Por qué es crítico:**
- `l10n_ar` usa este método para obtener precios ajustados según reglas fiscales AR
- El template usa estos valores para mostrar precios Y calcular subtotales acumulados
- Si no se convierte aquí, los totales no cuadran

### Vista: Smart Button

**Archivo:** `views/account_move_views.xml`

```xml
<button name="action_toggle_print_pesos" type="object"
        class="oe_stat_button"
        icon="fa-print"
        invisible="currency_id == company_currency_id">
    <div class="o_stat_info">
        <span class="o_stat_value" invisible="not print_in_pesos">$ Pesos</span>
        <span class="o_stat_value text-muted" invisible="print_in_pesos">$ USD</span>
        <span class="o_stat_text">Impresión</span>
    </div>
</button>
```

**Características:**
- Solo visible en facturas con moneda extranjera
- Muestra estado actual: "$ Pesos" (activo) o "$ USD" (inactivo)
- Ejecuta `action_toggle_print_pesos()` que invierte el valor

**Patrón:** `oe_stat_button` es el estándar de Odoo para botones de acción en formularios.

### Reporte: PDF Personalizado

**Archivo:** `report/account_move_report.xml`

**Template heredado:** `l10n_ar.report_invoice_document`

#### Modificaciones Aplicadas

**1. Estilos CSS**

```xml
<style>
    .page { font-size: 13px; }
    table.o_report_block_table tbody td { font-size: 13px; }
    div#total table.table span { font-size: 14px !important; }
</style>
```

**Por qué:** El PDF de Odoo por defecto tiene letra muy pequeña, difícil de leer en papel.

**2. Nota Informativa**

```xml
<div t-if="o.print_in_pesos and o._is_foreign_currency()">
    <strong>Moneda Original:</strong> USD |
    <strong>Impreso en:</strong> ARS
</div>
```

**3. Precios de Líneas**

```xml
<xpath expr='//span[contains(@t-out, "price_unit")]' position="attributes">
    <attribute name="t-options">{
        "display_currency": o.company_currency_id if o.print_in_pesos else o.currency_id
    }</attribute>
</xpath>
```

**Por qué solo cambiar display_currency:**
Los valores ya están en pesos gracias al override de `_l10n_ar_prices_and_taxes()`.
Solo falta mostrar el símbolo $ correcto.

**4. Tax Totals: NO necesita modificación**

El template llama a `_l10n_ar_get_invoice_totals_for_report()`, ya sobrescrito en Python.
Los valores vienen convertidos con formato correcto.

**Ventaja:** Código más limpio, lógica en Python, no en XML.

**5. Pagos Asociados**

```xml
<attribute name="t-out">
    o.currency_id._convert(payment_vals['amount'], o.company_currency_id, ...)
    if o.print_in_pesos else payment_vals['amount']
</attribute>
```

**6. Monto Residual**

Oculta el original y muestra una versión convertida cuando `print_in_pesos` está activo.

**7. Nota al Pie**

```xml
<div t-if="o.print_in_pesos">
    Valores expresados en ARS — Moneda original: USD —
    T.C. al 15/01/2026: 1150.00
</div>
```

---

## PARTE 3: Impresión de Presupuestos en Pesos

### Objetivo

Extender la funcionalidad de impresión en pesos a presupuestos de venta y órdenes de compra.

### A. Presupuestos de Venta (sale.order)

**Archivos:**
- `models/sale_order.py`
- `models/sale_order_line.py`
- `views/sale_order_views.xml`
- `report/sale_order_report.xml`

#### Modelo: `sale.order`

**Campos agregados:**

```python
print_in_pesos = fields.Boolean(
    string='Imprimir en Pesos',
    default=False,
)

# Por qué: Campo relacionado necesario para los campos Monetary que usan currency_field
# Patrón: Campo related para acceder a company_id.currency_id de forma directa
company_currency_id = fields.Many2one(
    'res.currency',
    string='Moneda de la Compañía',
    related='company_id.currency_id',
    readonly=True,
)

amount_untaxed_pesos = fields.Monetary(
    string='Subtotal (Pesos)',
    compute='_compute_amounts_pesos',
    currency_field='company_currency_id',
)
amount_tax_pesos = fields.Monetary(...)
amount_total_pesos = fields.Monetary(...)
```

**Por qué company_currency_id:**
- Los campos Monetary requieren especificar un `currency_field`
- Este campo debe existir en el modelo (Many2one a res.currency)
- Se define como `related` para acceder a la moneda de la compañía

**Método de cálculo:**

```python
@api.depends('amount_untaxed', 'amount_tax', 'amount_total',
             'currency_id', 'pricelist_id.currency_id', 'date_order')
def _compute_amounts_pesos(self):
    for order in self:
        # Compara con pricelist_id.currency_id
        if order.currency_id != order.pricelist_id.currency_id:
            date = order.date_order
            # Conversión usando date_order
```

**Diferencia con facturas:**
- Usa `pricelist_id.currency_id` como moneda base
- Usa `date_order` en lugar de `invoice_date`

#### Modelo: `sale.order.line`

Similar a `account.move.line`:

```python
price_unit_pesos = fields.Monetary(...)
price_subtotal_pesos = fields.Monetary(...)

@api.depends('price_unit', 'price_subtotal', 'currency_id', 'order_id.date_order')
def _compute_amounts_pesos(self):
    # Conversión por línea
```

#### Vista: Smart Button

```xml
<button name="action_toggle_print_pesos"
        icon="fa-print"
        invisible="currency_id == pricelist_id.currency_id">
    <!-- Estado visual -->
</button>
```

**Diferencia:** Invisibilidad basada en comparación con `pricelist_id.currency_id`.

#### Reporte: PDF

**Template heredado:** `sale.report_saleorder_document`

**Modificaciones:**
1. Estilos CSS (igual que facturas)
2. Nota informativa con moneda original
3. Precios de líneas con `display_currency` condicional
4. Totales usando campos computados `*_pesos`
5. Nota al pie con tipo de cambio

**Diferencia con facturas:**
No hay override de métodos especiales (no existe `_get_sale_totals_for_report()`).
Usa campos computados directamente en el template.

### B. Órdenes de Compra (purchase.order)

**Archivos:**
- `models/purchase_order.py`
- `models/purchase_order_line.py` (modificado)
- `views/purchase_order_views.xml`
- `report/purchase_order_report.xml`

#### Modelo: `purchase.order`

**Campos agregados:**

```python
print_in_pesos = fields.Boolean(
    string='Imprimir en Pesos',
    default=False,
)

# Por qué: Campo relacionado necesario para los campos Monetary que usan currency_field
# Patrón: Campo related para acceder a company_id.currency_id de forma directa
company_currency_id = fields.Many2one(
    'res.currency',
    string='Moneda de la Compañía',
    related='company_id.currency_id',
    readonly=True,
)

amount_untaxed_pesos = fields.Monetary(
    string='Subtotal (Pesos)',
    compute='_compute_amounts_pesos',
    currency_field='company_currency_id',
)
amount_tax_pesos = fields.Monetary(...)
amount_total_pesos = fields.Monetary(...)

@api.depends('amount_untaxed', 'amount_tax', 'amount_total',
             'currency_id', 'company_id.currency_id', 'date_order')
def _compute_amounts_pesos(self):
    # Usa company_id.currency_id como base
    # Usa date_order para conversión
```

**Diferencia con ventas:**
- Compara con `company_id.currency_id` (no con pricelist)
- Purchase no usa pricelist, usa moneda de la compañía directamente

#### Modelo: `purchase.order.line`

**MODIFICACIÓN del archivo existente:**

El archivo ya existe con campos `product_categ_id` y `product_uom_id`.
Se agregan:

```python
price_unit_pesos = fields.Monetary(...)
price_subtotal_pesos = fields.Monetary(...)

@api.depends(...)
def _compute_amounts_pesos(self):
    # Conversión por línea
```

#### Vista: Smart Button

```xml
<button name="action_toggle_print_pesos"
        icon="fa-print"
        invisible="currency_id == company_id.currency_id">
    <!-- Estado visual -->
</button>
```

#### Reporte: PDF

**Template heredado:** `purchase.report_purchaseorder_document`

**Modificaciones idénticas a sale.order:**
- Estilos CSS
- Nota informativa
- Precios con display_currency condicional
- Totales en pesos
- Nota al pie con TC

---

## Arquitectura Técnica

### Patrón de Herencia de Odoo

```python
class AccountMove(models.Model):
    _inherit = 'account.move'
```

**Tipo:** Herencia por extensión

**Ventajas:**
- No crea tablas nuevas
- Agrega campos y métodos a modelos existentes
- Permite sobrescribir métodos (override)
- Respeta otras customizaciones

### Campos Computados con Dependencias

```python
@api.depends('amount_untaxed', 'currency_id', 'invoice_date')
def _compute_amounts_pesos(self):
    ...
```

**¿Cómo funciona?**
- `@api.depends()` declara qué campos disparan el recálculo
- Cuando cambia `invoice_date`, Odoo recalcula automáticamente
- Usa el tipo de cambio del nuevo día
- No se almacena en BD (computed on-the-fly)

**Patrón:** Observer pattern (reactividad)

### Conversión de Moneda Estándar de Odoo

```python
currency_id._convert(
    amount,              # Monto a convertir
    target_currency,     # Moneda destino
    company,            # Compañía (para tasas específicas)
    date                # Fecha para buscar el TC
)
```

**Por qué usar el método estándar:**
- Busca en `res.currency.rate` automáticamente
- Respeta configuración multicompañía
- Maneja redondeos correctamente
- Compatible con otras customizaciones

### Deep Copy para Inmutabilidad

```python
tax_totals = copy.deepcopy(tax_totals_dict)
```

**Por qué:**
- No modifica el diccionario original
- Previene efectos secundarios
- Otro módulo puede usar ese diccionario después

**Patrón:** Inmutabilidad (functional programming)

### Override Defensivo

```python
def _l10n_ar_get_invoice_totals_for_report(self):
    result = super()._l10n_ar_get_invoice_totals_for_report()
    if self.print_in_pesos and self._is_foreign_currency():
        return self._convert_tax_totals_to_pesos(result)
    return result
```

**Patrón:** Template Method Pattern

**Ventajas:**
1. Respeta el comportamiento original (super())
2. Solo modifica cuando aplica (if condicional)
3. Fácil de debuggear
4. Compatible con otros módulos

### Separación de Responsabilidades

**Modelo (Python):**
- Lógica de negocio
- Cálculos y conversiones
- Validaciones

**Vista (XML):**
- Interfaz de usuario
- Smart buttons
- Campos visibles

**Reporte (XML):**
- Presentación
- Formato de impresión
- Estilos CSS

**Ventaja:** Cada componente tiene una responsabilidad clara.

---

## Flujos de Uso

### Caso 1: Factura de Proveedor USD $1,000

**Contexto:**
- Proveedor: Empresa de USA
- Factura: USD $1,000 + IVA 21% = $1,210
- Tipo de cambio: 1150 ARS/USD
- Fecha: 15/01/2026

**Flujo:**

1. **Usuario crea factura de proveedor**
   - Menú: Contabilidad → Proveedores → Facturas
   - Proveedor: USA Corp
   - Moneda: USD
   - Producto: Servicio técnico - $1,000
   - IVA: 21%

2. **Smart button aparece automáticamente**
   - Muestra: "$ USD | Impresión" (gris)
   - Solo visible porque currency_id != company_currency_id

3. **Usuario activa impresión en pesos**
   - Clic en smart button
   - Cambia a: "$ Pesos | Impresión" (negro)
   - `print_in_pesos = True`

4. **Usuario imprime PDF**

   **Header:**
   ```
   Moneda Original: USD | Impreso en: ARS
   ```

   **Líneas:**
   ```
   Descripción              Cant.    P.Unit.         Subtotal
   Servicio técnico         1.00     $ 1,150,000.00  $ 1,150,000.00
   ```

   **Totales:**
   ```
   Base Imponible:          $ 1,150,000.00
   IVA 21%:                 $   241,500.00
   ────────────────────────────────────────
   Total:                   $ 1,391,500.00
   ```

   **Pie:**
   ```
   Valores expresados en ARS — Moneda original: USD —
   T.C. al 15/01/2026: 1150.00
   ```

5. **Si desactiva el botón**
   - Vuelve a imprimir en USD normalmente
   - Sin conversión

### Caso 2: Presupuesto de Venta USD $500

**Contexto:**
- Cliente: Empresa local que pide presupuesto
- Precio: USD $500 (sin IVA para simplificar)
- Tipo de cambio: 1180 ARS/USD
- Fecha: 04/02/2026

**Flujo:**

1. **Usuario crea presupuesto**
   - Menú: Ventas → Presupuestos
   - Cliente: Cliente Local SA
   - Tarifa: USD Pricelist
   - Producto: Consultoría - $500

2. **Smart button disponible**
   - Muestra: "$ USD | Impresión"

3. **Usuario activa print_in_pesos**
   - Clic en botón
   - Cambia a: "$ Pesos | Impresión"

4. **Usuario envía PDF al cliente**

   **Header:**
   ```
   Moneda Original: USD | Impreso en: ARS
   ```

   **Líneas:**
   ```
   Producto              Cant.    P.Unit.       Subtotal
   Consultoría           1.00     $ 590,000.00  $ 590,000.00
   ```

   **Totales:**
   ```
   Total: $ 590,000.00
   ```

   **Pie:**
   ```
   Valores expresados en ARS — Moneda original: USD —
   T.C. al 04/02/2026: 1180.00
   ```

5. **Cliente aprueba y se confirma**
   - Al confirmar, contabilidad sigue en USD
   - Solo el PDF mostró valores en ARS

### Caso 3: Orden de Compra Multimoneda

**Contexto:**
- Proveedor con productos en USD y ARS
- Orden: Repuestos en USD
- Necesita PDF en pesos para aprobación interna

**Flujo:**

1. **Crear orden de compra**
   - Moneda: USD
   - Producto A: USD $100 x 10 = $1,000
   - Producto B: USD $50 x 5 = $250
   - Total: USD $1,250

2. **Activar print_in_pesos**

3. **Imprimir para aprobación gerencia**
   - Gerencia ve: $ 1,437,500.00 (TC: 1150)
   - Aprueba basándose en monto en pesos
   - Orden sigue en USD en el sistema

4. **Confirmar orden**
   - Factura llegará en USD
   - Se podrá imprimir en pesos también

---

## Buenas Prácticas Aplicadas

### 1. Uso de Métodos Estándar de Odoo

```python
# ✅ BIEN: Usar método estándar
currency_id._convert(amount, target, company, date)

# ❌ MAL: Calcular manualmente
amount * exchange_rate
```

**Por qué:**
- Respeta configuración de redondeo
- Maneja multicompañía
- Compatible con otros módulos

### 2. Store=True en Campos Relacionados

```python
product_categ_id = fields.Many2one(
    related='product_id.categ_id',
    store=True,  # ✅ Mejora performance
)
```

**Ventaja:**
- Consultas SQL más rápidas
- Permite agrupaciones sin joins
- Índices en BD

### 3. Campos Computados Sin Store

```python
amount_total_pesos = fields.Monetary(
    compute='_compute_amounts_pesos',
    # store=False (por defecto)
)
```

**Por qué NO store:**
- Se recalcula con TC actualizado
- No ocupa espacio en BD
- Siempre refleja valores actuales

### 4. Validaciones Defensivas

```python
def _compute_amounts_pesos(self):
    for move in self:  # ✅ Itera por registro
        if move.currency_id != move.company_currency_id:  # ✅ Valida
            # conversión
        else:
            # sin conversión
```

**Patrón:**
- Siempre iterar con `for`
- Validar condiciones antes de operar
- Manejar caso contrario (else)

### 5. Override con super()

```python
def _l10n_ar_get_invoice_totals_for_report(self):
    result = super()._l10n_ar_get_invoice_totals_for_report()  # ✅ Llama original
    # Modifica result
    return result
```

**Ventaja:**
- Respeta otras customizaciones
- Compatible con módulos de terceros
- Fácil de debuggear

### 6. Deep Copy en Diccionarios

```python
tax_totals = copy.deepcopy(tax_totals_dict)  # ✅ Copia profunda
```

**Evita:**
```python
tax_totals = tax_totals_dict  # ❌ Referencia, mutará el original
```

### 7. Comentarios Didácticos

```python
# Por qué: invoice_date es la fecha del comprobante (la que importa para el TC)
date = move.invoice_date or move.date

# Patrón: Deep copy para no mutar el dict original
tax_totals = copy.deepcopy(tax_totals_dict)

# Tip: formatLang respeta el idioma del usuario
formatted = formatLang(self.env, amount, currency_obj=currency)
```

**Estructura:**
- **Por qué:** Explica la razón de la decisión
- **Patrón:** Nombra el patrón de diseño usado
- **Tip:** Consejo para aprender

### 8. Invisible en Vistas

```xml
<!-- ✅ BIEN: Campo en vista para usar en attrs -->
<field name="print_in_pesos" invisible="1"/>

<button invisible="currency_id == company_currency_id">
```

**Por qué:**
- Odoo 17 exige que campos usados en attrs estén en la vista
- `invisible="1"` oculta pero carga el valor

### 9. Herencia de Templates

```xml
<!-- ✅ BIEN: Heredar del template correcto -->
<template id="report_invoice_document_pesos"
          inherit_id="l10n_ar.report_invoice_document">

<!-- ❌ MAL: Heredar del genérico no funciona en AR -->
<template inherit_id="account.report_invoice_document">
```

**Por qué:**
- `l10n_ar.report_invoice_document` tiene `primary=True`
- Es el que realmente se usa en Argentina

### 10. XPath Específicos

```xml
<!-- ✅ BIEN: XPath específico -->
<xpath expr='//span[contains(@t-out, "price_unit")]' position="attributes">

<!-- ❌ MAL: XPath genérico que puede romper -->
<xpath expr='//span' position="attributes">
```

**Ventaja:**
- Solo modifica el elemento deseado
- No afecta otros spans
- Más robusto ante cambios

---

## Comparación de Implementaciones

### Facturas vs Presupuestos

| Aspecto | Facturas (account.move) | Presupuestos Venta | Órdenes Compra |
|---------|------------------------|-------------------|----------------|
| **Moneda base** | `company_currency_id` | `pricelist_id.currency_id` | `company_id.currency_id` |
| **Fecha conversión** | `invoice_date` | `date_order` | `date_order` |
| **Template** | `l10n_ar.report_invoice_document` | `sale.report_saleorder_document` | `purchase.report_purchaseorder_document` |
| **Override totales** | `_l10n_ar_get_invoice_totals_for_report()` | No existe | No existe |
| **Override líneas** | `_l10n_ar_prices_and_taxes()` | No existe | No existe |
| **Complejidad fiscal** | Alta (tax_totals, l10n_ar) | Media (totales simples) | Media (totales simples) |
| **Depende de l10n_ar** | ✅ Sí (crítico) | ❌ No | ❌ No |

---

## Dependencias Críticas

### l10n_ar (Localización Argentina)

**¿Por qué es crítica para facturas?**

1. Define `l10n_ar.report_invoice_document` con `primary=True`
2. Ese template es el que se usa en Argentina (no el estándar)
3. Heredar de `account.report_invoice_document` NO afecta al PDF argentino

**Métodos específicos de l10n_ar:**
- `_l10n_ar_get_invoice_totals_for_report()`: Totales del reporte
- `_l10n_ar_prices_and_taxes()`: Precios ajustados según reglas AR
- Manejo de RG 5614/2024 (Transparencia Fiscal)

**Para presupuestos:**
No es crítica, solo se usa el módulo estándar de Odoo.

---

## Estructura del Módulo

```
surtecnica-reportes-dolar-peso/
├── __init__.py
├── __manifest__.py
├── README.md
│
├── models/
│   ├── __init__.py
│   ├── account_move.py              # Facturas
│   ├── account_move_line.py         # Líneas de factura
│   ├── purchase_order.py            # Órdenes de compra
│   ├── purchase_order_line.py       # Líneas de orden (análisis + pesos)
│   ├── sale_order.py                # Presupuestos de venta
│   └── sale_order_line.py           # Líneas de presupuesto
│
├── views/
│   ├── account_move_views.xml       # Smart button facturas
│   ├── purchase_order_line_views.xml # Vistas análisis + smart button
│   ├── purchase_order_views.xml     # Smart button órdenes
│   └── sale_order_views.xml         # Smart button presupuestos
│
└── report/
    ├── account_move_report.xml      # PDF facturas en pesos
    ├── purchase_order_report.xml    # PDF órdenes en pesos
    └── sale_order_report.xml        # PDF presupuestos en pesos
```

---

## Troubleshooting

### Problema: Smart button no aparece

**Causas posibles:**
1. Factura/presupuesto está en la misma moneda que la compañía
2. Vista XML no heredó correctamente
3. Campo `print_in_pesos` no está en la vista (Odoo 17 lo exige)

**Solución:**
```xml
<!-- Agregar campo invisible -->
<field name="print_in_pesos" invisible="1"/>
```

### Problema: PDF sigue mostrando USD

**Causas posibles:**
1. `print_in_pesos` no está marcado
2. Template heredó del incorrecto (usar `l10n_ar.report_invoice_document` para facturas)
3. Override de Python no se ejecuta

**Debug:**
```python
# Agregar en _compute_amounts_pesos
_logger.info(f"Convirtiendo {self.amount_total} a pesos")
```

### Problema: Totales no cuadran

**Causa:**
No se sobrescribió `_l10n_ar_prices_and_taxes()` en líneas de factura.

**Solución:**
El override DEBE convertir todos los valores: `price_unit`, `price_subtotal`, `price_total`, `vat_amount`.

### Problema: Tipo de cambio incorrecto

**Causas posibles:**
1. No hay tasa configurada para esa fecha
2. Se usa fecha incorrecta (debe ser `invoice_date` o `date_order`)

**Solución:**
Verificar en: Contabilidad → Configuración → Monedas → Tasas

---

## Extensiones Futuras

### 1. Selección de Moneda de Impresión

Permitir elegir entre múltiples monedas (EUR, BRL, etc.).

```python
print_currency_id = fields.Many2one('res.currency', string='Imprimir en')
```

### 2. Histórico de Tipos de Cambio

Mostrar tabla con TCs históricos en el formulario.

### 3. Alertas de Variación de TC

Notificar cuando el TC varíe más de X% desde la última cotización.

### 4. Análisis de Compras con Conversión Automática

Vista pivot que convierta TODO a pesos automáticamente.

### 5. Exportación a Excel

Botón para exportar presupuesto/factura en Excel con ambas monedas.

---

## Licencia

LGPL-3

---

## Soporte

**Autor:** Surtecnica
**Versión:** 17.0.1.0.0
**Categoría:** Accounting
