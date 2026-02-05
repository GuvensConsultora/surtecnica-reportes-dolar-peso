# Módulo: Reportes Dólar/Peso con Tipo de Cambio Manual

**Versión:** 17.0.1.0.0
**Autor:** Surtecnica
**Categoría:** Accounting / Reporting
**Licencia:** LGPL-3

---

## Tabla de Contenidos

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Problema de Negocio](#problema-de-negocio)
3. [Solución Propuesta](#solución-propuesta)
4. [Funcionalidad Principal](#funcionalidad-principal)
5. [Arquitectura Técnica](#arquitectura-técnica)
6. [Flujos de Uso](#flujos-de-uso)
7. [Instalación y Configuración](#instalación-y-configuración)
8. [Troubleshooting](#troubleshooting)
9. [Buenas Prácticas Implementadas](#buenas-prácticas-implementadas)

---

## Resumen Ejecutivo

Este módulo resuelve el problema de empresas argentinas que operan en moneda extranjera (USD) pero necesitan presentar documentación comercial y contable en pesos argentinos (ARS), permitiendo:

**Características principales:**

1. **Tipo de Cambio Manual Editable**: Define y controla el TC usado para conversiones
2. **Impresión Dual**: Documentos en USD que se imprimen en ARS sin alterar datos originales
3. **Registración Contable Personalizada**: Asientos contables usando TC manual, no el TC nativo de Odoo
4. **Trazabilidad Completa**: Tracking de cambios de TC en el chatter
5. **Transferencia de TC**: El TC se copia automáticamente desde presupuestos/órdenes a facturas
6. **Análisis de Compras**: Vistas pivot y reportes para análisis multidimensional

**Alcance:**
- Presupuestos de Venta (sale.order)
- Órdenes de Compra (purchase.order)
- Facturas de Cliente/Proveedor (account.move)

---

## Problema de Negocio

### Contexto

Las empresas argentinas que operan en mercados internacionales enfrentan desafíos únicos:

**Situación típica:**
- Negociación comercial en USD (moneda estable, aceptada internacionalmente)
- Necesidad de documentación en ARS (requerimientos locales, proveedores/clientes locales)
- Volatilidad del peso argentino (tipo de cambio cambia diariamente)
- Regulaciones contables argentinas (AFIP, registración en pesos)

**Problemas específicos:**

1. **Discrepancia entre TC Oficial y TC Operativo**
   - Odoo usa TC de `res.currency.rate` (actualización manual o automática)
   - El TC real de operación puede diferir (TC bancario, TC del día de facturación, TC acordado)
   - Necesidad de registrar contablemente con el TC real, no el oficial

2. **Documentación Dual**
   - Presupuestos negociados en USD
   - Cliente local necesita ver valores en ARS para aprobación
   - No se pueden duplicar documentos (problema fiscal)

3. **Trazabilidad del TC**
   - El TC del presupuesto debe mantenerse en la factura
   - Cambios de TC deben quedar registrados (auditoría)
   - Necesidad de justificar TC usado ante controles fiscales

4. **Registración Contable Precisa**
   - Los asientos contables (debit/credit) deben reflejar el TC real
   - El balance debe mostrar valores según TC operativo
   - Conciliaciones bancarias requieren TC exacto

---

## Solución Propuesta

### Enfoque de Diseño

El módulo implementa una solución **no invasiva** que:

1. **Respeta la funcionalidad estándar de Odoo**: No modifica comportamiento por defecto
2. **Agrega capacidades opcionales**: El usuario decide cuándo aplicar conversiones
3. **Mantiene trazabilidad**: Todos los cambios quedan registrados
4. **Garantiza consistencia**: TC se mantiene desde presupuesto hasta factura y contabilidad

### Componentes de la Solución

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRESUPUESTO / ORDEN DE COMPRA                │
│  USD $1,000                                                     │
│  ┌──────────────────────────────────────────┐                  │
│  │ Tipo de Cambio Manual: 1,250.00          │ (editable)       │
│  │ • Auto-completado con TC de la fecha     │                  │
│  │ • Usuario puede modificar                │                  │
│  │ • Cambios registrados en chatter         │                  │
│  └──────────────────────────────────────────┘                  │
│                                                                 │
│  Smart Button: [$ Pesos | Impresión] ←─────── Toggle           │
│                                                                 │
│  → PDF muestra: $ 1,250,000.00 (si activado)                   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ Crear Factura
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                           FACTURA                               │
│  USD $1,000                                                     │
│  ┌──────────────────────────────────────────┐                  │
│  │ Tipo de Cambio Manual: 1,250.00          │ (copiado)        │
│  │ • Viene del presupuesto/orden            │                  │
│  └──────────────────────────────────────────┘                  │
│                                                                 │
│  Smart Button: [$ Pesos | Impresión]                           │
│                                                                 │
│  → PDF muestra: $ 1,250,000.00                                 │
│  → Asientos contables:                                         │
│     • Debit:  $ 1,250,000.00 (con TC manual)                   │
│     • Credit: $ 1,250,000.00 (con TC manual)                   │
│                                                                 │
│  Nota: Si TC nativo de Odoo es 1,180.00, los asientos IGUAL    │
│        usan 1,250.00 (TC manual definido por el usuario)       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Funcionalidad Principal

### 1. Tipo de Cambio Manual

**Campo:** `manual_currency_rate`

**Ubicación:**
- Presupuestos de Venta
- Órdenes de Compra
- Facturas (Cliente/Proveedor)

**Comportamiento:**

```python
# Por qué: Auto-completa con TC de la fecha, pero permite edición manual
@api.onchange('currency_id', 'company_id', 'date_order')
def _onchange_currency_rate(self):
    """Actualiza el TC cuando cambia la moneda o la fecha."""
    for order in self:
        if order.currency_id != order.company_id.currency_id:
            date = order.date_order or fields.Date.context_today(order)
            order.manual_currency_rate = order.currency_id._convert(
                1.0, order.company_id.currency_id, order.company_id, date)
```

**Características:**

1. **Auto-completado Inteligente**
   - Al crear un documento en USD, el campo se completa automáticamente
   - Usa el TC de la fecha del documento
   - Se actualiza si cambia la fecha

2. **Edición Manual**
   - El usuario puede modificar el valor en cualquier momento
   - Útil cuando el TC real difiere del TC oficial
   - Ejemplo: TC acordado con el cliente, TC bancario del día

3. **Tracking en Chatter**
   ```python
   manual_currency_rate = fields.Float(
       tracking=True,  # ← Registra cambios en chatter
       help='Tipo de cambio para convertir a pesos. '
            'Se autocompleta con el TC de la fecha, pero puede modificarse.',
   )
   ```
   - Cada cambio genera un mensaje en el chatter
   - Incluye: valor anterior, valor nuevo, usuario, fecha
   - Auditoría completa de modificaciones

4. **Transferencia Automática**
   ```python
   # En sale_order.py y purchase_order.py
   def _prepare_invoice(self):
       invoice_vals = super()._prepare_invoice()
       if self.manual_currency_rate:
           invoice_vals['manual_currency_rate'] = self.manual_currency_rate
       return invoice_vals
   ```
   - Al crear factura desde presupuesto/orden: TC se copia
   - Garantiza consistencia entre documentos
   - Evita discrepancias contables

**Visualización:**

```
┌────────────────────────────────────────────┐
│ Presupuesto de Venta - PRE/001             │
├────────────────────────────────────────────┤
│ Cliente: ABC SA                            │
│ Fecha: 05/02/2026                          │
│ Moneda: USD                                │
│ Tipo de Cambio: 1,250.0000 ←─── Editable  │
│                                            │
│ Productos:                                 │
│  - Producto A   USD $1,000.00              │
│                                            │
│ Total: USD $1,000.00                       │
└────────────────────────────────────────────┘
        ↓ Chatter
┌────────────────────────────────────────────┐
│ Usuario cambió Tipo de Cambio             │
│  1,180.0000 → 1,250.0000                   │
│  Hace 2 minutos                            │
└────────────────────────────────────────────┘
```

---

### 2. Impresión en Pesos

**Campo:** `print_in_pesos` (Boolean)

**Control:** Smart Button en formulario

**Flujo:**

1. **Usuario abre documento en USD**
   - Smart button aparece automáticamente
   - Estado inicial: "$ USD | Impresión" (gris)

2. **Usuario activa impresión en pesos**
   - Clic en smart button
   - Estado cambia: "$ Pesos | Impresión" (negro)
   - `print_in_pesos = True`

3. **Al imprimir PDF**
   - Todos los montos se muestran en ARS
   - Usa `manual_currency_rate` para conversión
   - Incluye nota con TC y fecha

**Conversión en Reportes:**

```python
# Por qué: Override del método que genera totales para el PDF
def _l10n_ar_get_invoice_totals_for_report(self):
    result = super()._l10n_ar_get_invoice_totals_for_report()
    if self.print_in_pesos and self._is_foreign_currency():
        return self._convert_tax_totals_to_pesos(result)
    return result

def _convert_tax_totals_to_pesos(self, tax_totals_dict):
    """Convierte tax_totals usando TC manual."""
    def convert(amount):
        # Por qué: Si hay TC manual, lo usa; sino usa TC nativo
        if self.manual_currency_rate:
            return amount * self.manual_currency_rate
        return currency._convert(amount, company_currency, company, date)

    # Convierte: totales, subtotales, impuestos, detalles AR
```

**Ejemplo de PDF Generado:**

```
════════════════════════════════════════════════════════════════
                        PRESUPUESTO PRE/001
════════════════════════════════════════════════════════════════
Cliente: ABC SA                          Fecha: 05/02/2026
Moneda Original: USD | Impreso en: ARS

────────────────────────────────────────────────────────────────
Descripción              Cantidad    P.Unit.          Subtotal
────────────────────────────────────────────────────────────────
Producto A               1.00        $ 1,250,000.00   $ 1,250,000.00
Producto B               2.00        $   625,000.00   $ 1,250,000.00

────────────────────────────────────────────────────────────────
Subtotal:                                             $ 2,500,000.00
IVA 21%:                                              $   525,000.00
════════════════════════════════════════════════════════════════
TOTAL:                                                $ 3,025,000.00
════════════════════════════════════════════════════════════════

Valores expresados en ARS — Moneda original: USD
Tipo de Cambio: 1,250.0000 — Fecha: 05/02/2026

🤖 Generado con Odoo 17.0
```

---

### 3. Registración Contable con TC Manual

**Problema Resuelto:**

En Odoo estándar:
- Factura en USD $1,000
- TC nativo de Odoo: 1,180.00
- Asiento contable: Debit $1,180,000 / Credit $1,180,000

Con TC manual:
- Factura en USD $1,000
- TC manual: 1,250.00 (TC real del banco)
- Asiento contable: Debit $1,250,000 / Credit $1,250,000 ✓

**Implementación Técnica:**

```python
# Por qué: Interceptar create() para aplicar TC manual al crear factura
@api.model_create_multi
def create(self, vals_list):
    moves = super().create(vals_list)
    for move in moves:
        if move.manual_currency_rate and move._is_foreign_currency():
            move._apply_manual_currency_rate()
    return moves

# Por qué: Interceptar write() para recalcular si cambia el TC
def write(self, vals):
    result = super().write(vals)
    if 'manual_currency_rate' in vals:
        for move in self:
            if move.manual_currency_rate and move._is_foreign_currency():
                move._apply_manual_currency_rate()
    return result

def _apply_manual_currency_rate(self):
    """Aplica TC manual a líneas contables."""
    self.ensure_one()
    # Por qué: Filtrar líneas con amount_currency (en USD)
    for line in self.line_ids.filtered(
        lambda l: l.amount_currency and l.currency_id == self.currency_id
    ):
        # Por qué: Calcular balance con TC manual
        balance = line.amount_currency * self.manual_currency_rate
        # Por qué: write() triggera recálculo automático de debit/credit
        line.with_context(check_move_validity=False).write({
            'balance': balance,
        })
```

**Flujo de Registración:**

```
Presupuesto USD $1,000 con TC manual 1,250
            ↓
Crear Factura (copia TC = 1,250)
            ↓
create() ejecuta _apply_manual_currency_rate()
            ↓
Para cada línea contable:
  - Producto: amount_currency = -$1,000 (USD)
    → balance = -$1,000 × 1,250 = -$1,250,000
    → credit = $1,250,000, debit = $0

  - Cliente: amount_currency = $1,000 (USD)
    → balance = $1,000 × 1,250 = $1,250,000
    → debit = $1,250,000, credit = $0
            ↓
Asiento balanceado: Debit = Credit = $1,250,000 ✓
```

**Protección contra Desbalanceo:**

```python
# Contexto especial para evitar validación prematura
line.with_context(check_move_validity=False).write({
    'balance': balance,
})

# Por qué:
# - Odoo valida que debit = credit después de cada write()
# - Al recalcular línea por línea, temporalmente está desbalanceado
# - check_move_validity=False suspende la validación
# - Al final, todas las líneas están recalculadas y el asiento balancea
```

---

### 4. Análisis de Órdenes de Compra

**Objetivo:** Facilitar análisis multidimensional de compras

**Vistas Implementadas:**

1. **Vista Lista**
   - Todas las líneas de órdenes de compra
   - Filtros: Estado, Proveedor, Categoría, Fecha
   - Suma automática de cantidades y subtotales

2. **Vista Pivot**
   - Análisis tipo tabla dinámica
   - Agrupaciones: Moneda, Proveedor, Categoría, Producto, Mes
   - Medidas: Cantidad comprada, Subtotal

3. **Menú:** Compras → Informes → Líneas de Compra

**Campos Agregados:**

```python
# En purchase.order.line
product_categ_id = fields.Many2one(
    'product.category',
    related='product_id.categ_id',
    store=True,  # ← Crítico para pivot
)

product_uom_id = fields.Many2one(
    'uom.uom',
    related='product_id.uom_id',
    store=True,
)
```

**Por qué store=True:**
- Permite agrupaciones en pivot sin joins complejos
- Mejora performance en reportes con muchas líneas
- Permite índices en base de datos

---

## Arquitectura Técnica

### Modelos Extendidos

```python
# Patrón: Herencia por extensión (no crea tablas nuevas)
class AccountMove(models.Model):
    _inherit = 'account.move'

    # Nuevos campos
    print_in_pesos = fields.Boolean(...)
    manual_currency_rate = fields.Float(...)
    amount_untaxed_pesos = fields.Monetary(compute='...')
    amount_tax_pesos = fields.Monetary(compute='...')
    amount_total_pesos = fields.Monetary(compute='...')

    # Métodos sobrescritos
    def _l10n_ar_get_invoice_totals_for_report(self): ...
    def create(self, vals_list): ...
    def write(self, vals): ...
    def _recompute_dynamic_lines(self, ...): ...

    # Métodos nuevos
    def _apply_manual_currency_rate(self): ...
    def _convert_tax_totals_to_pesos(self, tax_totals_dict): ...
    def action_toggle_print_pesos(self): ...
    def _is_foreign_currency(self): ...
```

### Flujo de Datos: Presupuesto → Factura

```
┌─────────────────────────────────────────────────────────────┐
│ PRESUPUESTO DE VENTA (sale.order)                          │
├─────────────────────────────────────────────────────────────┤
│ • currency_id = USD                                         │
│ • date_order = 05/02/2026                                   │
│ • manual_currency_rate = 1,250.0000 (usuario lo editó)     │
│ • print_in_pesos = True                                     │
│ • amount_total = USD $1,000.00                              │
│ • amount_total_pesos = $ 1,250,000.00 (computed)            │
└─────────────────────────────────────────────────────────────┘
                        ↓
            Usuario → Crear Factura
                        ↓
    _prepare_invoice() ← Override de sale.order
                        ↓
    invoice_vals = {
        'partner_id': ...,
        'currency_id': USD,
        'invoice_date': 05/02/2026,
        'manual_currency_rate': 1,250.0000,  ← Copiado
        'invoice_line_ids': [...],
    }
                        ↓
    account.move.create(invoice_vals)
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ FACTURA (account.move)                                      │
├─────────────────────────────────────────────────────────────┤
│ • currency_id = USD                                         │
│ • invoice_date = 05/02/2026                                 │
│ • manual_currency_rate = 1,250.0000 ← Preservado           │
│ • print_in_pesos = False (default, usuario puede activar)  │
│ • amount_total = USD $1,000.00                              │
│                                                             │
│ Líneas contables (account.move.line):                      │
│   1. Cliente (Cuenta por cobrar)                            │
│      amount_currency = USD $1,000.00                        │
│      balance = $ 1,250,000.00 ← TC manual aplicado          │
│      debit = $ 1,250,000.00                                 │
│      credit = $0                                            │
│                                                             │
│   2. Ingreso (Venta)                                        │
│      amount_currency = USD -$1,000.00                       │
│      balance = $ -1,250,000.00 ← TC manual aplicado         │
│      debit = $0                                             │
│      credit = $ 1,250,000.00                                │
│                                                             │
│ Balance: ✓ Debit ($1,250,000) = Credit ($1,250,000)        │
└─────────────────────────────────────────────────────────────┘
```

### Métodos Clave

#### 1. Conversión con TC Manual

```python
def _convert_tax_totals_to_pesos(self, tax_totals_dict):
    """Convierte tax_totals a pesos usando TC manual.

    Por qué: Método reutilizable para convertir cualquier dict de totales.
    Patrón: Deep copy para no mutar el original (inmutabilidad).
    """
    self.ensure_one()
    tax_totals = copy.deepcopy(tax_totals_dict)

    def convert(amount):
        # Por qué: Priorizar TC manual sobre TC nativo
        if self.manual_currency_rate:
            return amount * self.manual_currency_rate
        return currency._convert(amount, company_currency, company, date)

    def fmt(amount):
        return formatLang(self.env, amount, currency_obj=company_currency)

    # Convertir estructura completa
    tax_totals['amount_total'] = convert(tax_totals['amount_total'])
    tax_totals['formatted_amount_total'] = fmt(tax_totals['amount_total'])
    # ... (subtotales, grupos de impuestos, detalles AR)

    return tax_totals
```

#### 2. Aplicación de TC a Líneas Contables

```python
def _apply_manual_currency_rate(self):
    """Recalcula debit/credit de líneas contables con TC manual.

    Por qué: Garantiza que los asientos usen TC manual, no TC nativo.
    Patrón: Filtrado + contexto especial para evitar validación prematura.
    """
    self.ensure_one()

    for line in self.line_ids.filtered(
        lambda l: l.amount_currency and l.currency_id == self.currency_id
    ):
        balance = line.amount_currency * self.manual_currency_rate

        # Por qué: write() triggera recálculo de debit/credit desde balance
        # check_move_validity=False evita validación mientras recalculamos
        line.with_context(check_move_validity=False).write({
            'balance': balance,
        })
```

#### 3. Override de Reportes l10n_ar

```python
def _l10n_ar_get_invoice_totals_for_report(self):
    """Override para PDFs argentinos.

    Por qué: l10n_ar.report_invoice_document tiene primary=True.
    Es el template que realmente se usa en Argentina.
    Heredar de account.report_invoice_document NO funcionaría.
    """
    result = super()._l10n_ar_get_invoice_totals_for_report()

    if self.print_in_pesos and self._is_foreign_currency():
        return self._convert_tax_totals_to_pesos(result)

    return result
```

### Patrones de Diseño Aplicados

**1. Template Method Pattern**
```python
def method(self):
    result = super().method()  # ← Llama original
    # Modifica result
    return result
```
- Respeta comportamiento base
- Agrega funcionalidad sin romper original
- Compatible con otros módulos

**2. Strategy Pattern (Conversión)**
```python
def convert(amount):
    if self.manual_currency_rate:
        return amount * self.manual_currency_rate  # ← Estrategia manual
    return currency._convert(...)  # ← Estrategia estándar
```
- Selecciona estrategia de conversión en runtime
- Fácil de extender (ej: agregar más estrategias)

**3. Observer Pattern (Computed Fields)**
```python
@api.depends('amount_total', 'manual_currency_rate')
def _compute_amounts_pesos(self):
    # Se ejecuta automáticamente cuando cambian dependencias
```
- Reactividad automática
- Sincronización de datos
- Reduce código manual

**4. Immutability Pattern**
```python
tax_totals = copy.deepcopy(tax_totals_dict)  # ← No mutar original
```
- Previene efectos secundarios
- Facilita debugging
- Más seguro en sistemas concurrentes

---

## Flujos de Uso

### Caso 1: Presupuesto en USD con TC Específico

**Escenario:**
- Cliente local solicita presupuesto
- Precios en USD (estabilidad)
- Cliente necesita aprobación interna en ARS
- TC del día: 1,180 ARS/USD (oficial)
- TC del banco: 1,250 ARS/USD (real)

**Flujo:**

```
1. Usuario crea presupuesto
   ├─ Ventas → Presupuestos → Crear
   ├─ Cliente: ABC SA
   ├─ Moneda: USD (desde pricelist)
   └─ Producto: Consultoría - USD $1,000

2. Campo TC se auto-completa
   ├─ manual_currency_rate = 1,180.00 (TC oficial de la fecha)
   └─ Usuario lo edita manualmente a 1,250.00 (TC real del banco)

   → Chatter registra:
     "Usuario cambió Tipo de Cambio: 1,180.0000 → 1,250.0000"

3. Usuario activa impresión en pesos
   ├─ Clic en Smart Button
   └─ Estado: "$ Pesos | Impresión" ✓

4. Usuario imprime y envía PDF
   ├─ Muestra: Total $ 1,250,000.00
   ├─ Nota: "TC: 1,250.0000 - Fecha: 05/02/2026"
   └─ Cliente aprueba basándose en monto en ARS

5. Usuario confirma presupuesto
   └─ Estado: Orden de Venta

6. Usuario crea factura desde presupuesto
   ├─ Presupuesto → Crear Factura
   ├─ TC copiado automáticamente: 1,250.00 ✓
   └─ Asientos contables usan TC 1,250.00 (no 1,180.00)

7. Registración contable final
   ├─ Debit (Clientes): $ 1,250,000.00
   ├─ Credit (Ingresos): $ 1,250,000.00
   └─ Balance cuadra con TC real del banco ✓
```

---

### Caso 2: Factura de Proveedor con TC Acordado

**Escenario:**
- Proveedor extranjero
- Factura en USD $5,000
- TC acordado contractualmente: 1,200 ARS/USD
- TC oficial del día: 1,180 ARS/USD

**Flujo:**

```
1. Usuario crea factura de proveedor
   ├─ Contabilidad → Proveedores → Facturas
   ├─ Proveedor: USA Corp
   ├─ Moneda: USD
   └─ Monto: USD $5,000

2. Campo TC se auto-completa
   ├─ manual_currency_rate = 1,180.00 (TC oficial)
   └─ Usuario lo edita a 1,200.00 (TC contractual)

3. Usuario valida factura
   └─ Asientos contables:
       ├─ Debit (Gastos): $ 6,000,000.00  (5,000 × 1,200)
       └─ Credit (Proveedores): $ 6,000,000.00

4. Al pagar la factura
   ├─ Pago efectivo: $ 6,000,000.00
   └─ Concilia perfectamente con el asiento (mismo TC) ✓

5. Auditoría
   └─ Chatter muestra: "TC modificado a 1,200.0000"
       Justificación: TC acordado en contrato
```

---

### Caso 3: Análisis de Compras Multimoneda

**Escenario:**
- Empresa compra en USD y ARS
- Necesita análisis mensual por categoría

**Flujo:**

```
1. Usuario accede al análisis
   └─ Compras → Informes → Líneas de Compra

2. Cambia a vista Pivot
   └─ Botón: [ Lista | Pivot | Gráfico ]

3. Configura agrupaciones
   ├─ Filas: Categoría de Producto
   ├─ Columnas: Fecha Prevista (Mes)
   └─ Medida: Subtotal

4. Aplica filtro
   └─ Moneda = USD

5. Resultado
   ┌─────────────────┬─────────┬─────────┬─────────┐
   │ Categoría       │ Enero   │ Febrero │ Total   │
   ├─────────────────┼─────────┼─────────┼─────────┤
   │ Materia Prima   │ $10,000 │ $15,000 │ $25,000 │
   │ Servicios       │  $5,000 │  $8,000 │ $13,000 │
   │ TOTAL           │ $15,000 │ $23,000 │ $38,000 │
   └─────────────────┴─────────┴─────────┴─────────┘

6. Usuario exporta a Excel
   └─ Botón: Descargar
```

---

## Instalación y Configuración

### Requisitos

**Odoo:** 17.0 Enterprise

**Dependencias:**
```python
'depends': ['purchase', 'account', 'sale', 'l10n_ar']
```

- `purchase`: Órdenes de compra
- `account`: Facturas y contabilidad
- `sale`: Presupuestos de venta
- `l10n_ar`: Localización Argentina (**crítico para facturas**)

### Instalación

1. **Clonar/copiar módulo**
   ```bash
   cd /path/to/odoo/addons
   git clone <repo-url> surtecnica-reportes-dolar-peso
   ```

2. **Actualizar lista de aplicaciones**
   ```
   Aplicaciones → Actualizar Lista de Aplicaciones
   ```

3. **Instalar módulo**
   ```
   Aplicaciones → Buscar "Reportes Dólar/Peso"
   → Instalar
   ```

4. **Verificar instalación**
   - Abrir factura en USD
   - Verificar presencia de smart button "Impresión"
   - Verificar campo "Tipo de Cambio"

### Configuración Inicial

**1. Configurar Tipos de Cambio**
```
Contabilidad → Configuración → Monedas
→ Seleccionar USD
→ Ver Tasas
→ Agregar tasas para fechas relevantes
```

**2. Configurar Pricelist en USD (para ventas)**
```
Ventas → Configuración → Tarifas
→ Crear "Tarifa USD"
→ Moneda: USD
→ Asignar a clientes que operan en USD
```

**3. Configurar Proveedores USD**
```
Compras → Proveedores
→ Editar proveedor
→ Moneda de Compra: USD
```

### Permisos

No requiere permisos especiales. Los usuarios con acceso a:
- Ventas: Pueden usar funcionalidad en presupuestos
- Compras: Pueden usar funcionalidad en órdenes
- Contabilidad: Pueden usar funcionalidad en facturas

---

## Troubleshooting

### Problema 1: Smart Button No Aparece

**Síntomas:**
- Documento en USD pero no se ve el smart button

**Causas posibles:**

1. **Moneda igual a moneda de compañía**
   ```python
   # El botón está invisible cuando:
   invisible="currency_id == company_currency_id"
   ```
   **Solución:** Verificar que el documento esté en USD, no en ARS

2. **Vista no actualizada**
   **Solución:**
   ```
   Modo desarrollador → Actualizar vista → Recargar página
   ```

3. **Campo print_in_pesos no está en la vista**
   **Solución:** Verificar en XML:
   ```xml
   <field name="print_in_pesos" invisible="1"/>
   ```

### Problema 2: TC Manual No Se Copia a Factura

**Síntomas:**
- Presupuesto tiene TC 1,250
- Factura creada tiene TC 1,180 (TC oficial)

**Causa:**
El onchange sobrescribe el valor copiado

**Diagnóstico:**
```python
# En account_move.py, verificar:
@api.onchange('currency_id', 'company_id', 'invoice_date', 'date')
def _onchange_currency_rate(self):
    for move in self:
        if not move.manual_currency_rate:  # ← Debe tener esta validación
            # Solo calcular si no hay TC manual
```

**Solución:**
El código ya tiene protección, verificar que esté actualizado

### Problema 3: Asiento Desbalanceado

**Síntomas:**
```
Error: El movimiento no está saldado.
Total débito: $0
Total crédito: $1,250,000
```

**Causa:**
Problema en `_apply_manual_currency_rate()`

**Diagnóstico:**
```python
# Verificar que use write() con contexto:
line.with_context(check_move_validity=False).write({
    'balance': balance,
})
```

**Solución:**
Verificar versión del módulo, debe tener el fix del contexto

### Problema 4: PDF Sigue Mostrando USD

**Síntomas:**
- `print_in_pesos = True`
- PDF muestra USD $1,000 en lugar de $ 1,250,000

**Diagnóstico:**

1. **Verificar template correcto (facturas)**
   ```xml
   <!-- CORRECTO -->
   <template id="..." inherit_id="l10n_ar.report_invoice_document">

   <!-- INCORRECTO -->
   <template id="..." inherit_id="account.report_invoice_document">
   ```

2. **Verificar override de método**
   ```python
   # En account_move.py
   def _l10n_ar_get_invoice_totals_for_report(self):
       result = super()._l10n_ar_get_invoice_totals_for_report()
       if self.print_in_pesos and self._is_foreign_currency():
           return self._convert_tax_totals_to_pesos(result)
       return result
   ```

3. **Debug con log**
   ```python
   import logging
   _logger = logging.getLogger(__name__)

   def _convert_tax_totals_to_pesos(self, tax_totals_dict):
       _logger.info(f"Convirtiendo totales: {tax_totals_dict}")
       # ...
   ```

### Problema 5: TC No Se Auto-completa

**Síntomas:**
- Al crear documento en USD, TC queda en 0

**Causas:**

1. **No hay TC configurado para la fecha**
   **Solución:**
   ```
   Contabilidad → Configuración → Monedas → USD → Tasas
   → Agregar tasa para la fecha
   ```

2. **Onchange no se ejecuta**
   **Solución:**
   - Cambiar fecha del documento (triggera onchange)
   - O ingresar TC manualmente

### Problema 6: Totales en PDF No Cuadran

**Síntomas:**
- Suma de líneas: $ 1,250,000
- Total mostrado: $ 1,180,000

**Causa:**
No se sobrescribió `_l10n_ar_prices_and_taxes()` en líneas

**Solución:**
Verificar en `account_move_line.py`:
```python
def _l10n_ar_prices_and_taxes(self):
    result = super()._l10n_ar_prices_and_taxes()
    move = self.move_id
    if move.print_in_pesos and move._is_foreign_currency():
        if move.manual_currency_rate:
            for key in ('price_unit', 'price_subtotal', 'price_total', 'vat_amount'):
                if key in result:
                    result[key] = result[key] * move.manual_currency_rate
    return result
```

---

## Buenas Prácticas Implementadas

### 1. Override Defensivo

```python
# ✅ CORRECTO: Llama super() primero
def method(self):
    result = super().method()
    # Modifica solo si aplica
    if self.condition:
        result = self.transform(result)
    return result

# ❌ INCORRECTO: Reemplaza completamente
def method(self):
    # Lógica propia sin llamar super()
    return custom_result
```

**Ventajas:**
- Respeta otras customizaciones
- Compatible con módulos de terceros
- Fácil de debuggear

### 2. Campos Computados vs Stored

```python
# Computed sin store (recalcula siempre)
amount_total_pesos = fields.Monetary(
    compute='_compute_amounts_pesos',
    # NO store=True
)

# Related con store (performance)
product_categ_id = fields.Many2one(
    related='product_id.categ_id',
    store=True,  # ✅ Para reportes
)
```

**Cuándo usar store=True:**
- Campos usados en agrupaciones (pivot)
- Búsquedas frecuentes
- Reportes de performance

**Cuándo NO usar store:**
- Valores que cambian frecuentemente (TC, totales)
- Basados en fecha actual
- Requieren datos actualizados siempre

### 3. Inmutabilidad en Diccionarios

```python
# ✅ CORRECTO: Deep copy
def transform_dict(self, data):
    result = copy.deepcopy(data)
    result['key'] = new_value
    return result

# ❌ INCORRECTO: Mutar original
def transform_dict(self, data):
    data['key'] = new_value  # ← Afecta al caller
    return data
```

### 4. Contextos Especiales

```python
# Por qué: Evitar validaciones/recursiones durante operaciones batch
line.with_context(check_move_validity=False).write({...})

# Otros contextos útiles:
# - tracking_disable: No crear mensajes en chatter
# - mail_create_nosubscribe: No suscribir al creador
# - mail_notrack: No trackear cambios
```

### 5. Depends Completos

```python
# ✅ CORRECTO: Incluir todas las dependencias
@api.depends('amount_untaxed', 'amount_tax', 'amount_total',
             'currency_id', 'company_currency_id',
             'invoice_date', 'date', 'manual_currency_rate')
def _compute_amounts_pesos(self):
    pass

# ❌ INCORRECTO: Faltan dependencias
@api.depends('amount_total')  # ← Falta manual_currency_rate
def _compute_amounts_pesos(self):
    # No se recalcula cuando cambia el TC
    pass
```

### 6. Validaciones Defensivas

```python
# ✅ CORRECTO: Validar antes de operar
for move in self:
    if move.manual_currency_rate and move._is_foreign_currency():
        # Operación segura
    else:
        # Caso alternativo
        pass

# ❌ INCORRECTO: Asumir condiciones
for move in self:
    result = move.amount_total * move.manual_currency_rate  # ← Puede ser 0 o False
```

### 7. Comentarios Didácticos

```python
# Por qué: Explica la razón (el "por qué")
# Patrón: Nombra el patrón de diseño
# Tip: Consejo para aprender

# Ejemplo:
# Por qué: invoice_date es la fecha fiscal que determina el TC legal
date = move.invoice_date or move.date

# Patrón: Deep copy para no mutar el diccionario original
tax_totals = copy.deepcopy(tax_totals_dict)

# Tip: formatLang respeta el idioma y formato regional del usuario
formatted = formatLang(self.env, amount, currency_obj=currency)
```

### 8. Uso de Métodos Estándar

```python
# ✅ CORRECTO: Usar API de Odoo
amount_ars = currency_id._convert(
    amount_usd, ars_currency, company, date
)

# ❌ INCORRECTO: Calcular manualmente
amount_ars = amount_usd * 1250.00  # Hardcoded, no respeta config
```

**Ventajas métodos estándar:**
- Respeta configuración de redondeo
- Maneja multicompañía correctamente
- Compatible con otros módulos
- Probado y mantenido por Odoo

---

## Extensiones Futuras

### 1. Histórico de TC

Mostrar gráfico de evolución del TC en el formulario:

```python
tc_history_ids = fields.One2many(
    'currency.rate.history',
    compute='_compute_tc_history'
)

def _compute_tc_history(self):
    # Últimos 30 días de TC para esta moneda
```

### 2. Alertas de Variación

Notificar cuando TC varía más de X%:

```python
def write(self, vals):
    if 'manual_currency_rate' in vals:
        old_rate = self.manual_currency_rate
        new_rate = vals['manual_currency_rate']
        variation = abs((new_rate - old_rate) / old_rate * 100)

        if variation > 5:  # 5% de variación
            self.message_post(
                body=f"⚠️ Variación de TC mayor a 5%: {variation:.2f}%"
            )
```

### 3. TC por Método de Pago

Diferentes TC según forma de pago:

```python
manual_currency_rate_cash = fields.Float('TC Efectivo')
manual_currency_rate_bank = fields.Float('TC Transferencia')
```

### 4. Exportación Dual a Excel

Botón para exportar con ambas monedas:

```
| Producto | Cantidad | P.Unit USD | Subtotal USD | P.Unit ARS | Subtotal ARS |
|----------|----------|------------|--------------|------------|--------------|
| Prod A   | 10       | $100       | $1,000       | $125,000   | $1,250,000   |
```

### 5. Conversión Masiva

Wizard para convertir múltiples documentos a la vez:

```python
class MassConvertWizard(models.TransientModel):
    _name = 'mass.convert.wizard'

    invoice_ids = fields.Many2many('account.move')
    target_currency_id = fields.Many2one('res.currency')
    manual_rate = fields.Float()

    def action_convert(self):
        # Aplicar TC a todos los documentos seleccionados
```

---

## Licencia y Soporte

**Licencia:** LGPL-3

**Autor:** Surtecnica

**Versión:** 17.0.1.0.0

**Categoría:** Accounting / Reporting

**Soporte:**
- Issues: [GitHub Repository]
- Email: [email de soporte]

---

## Notas de Versión

### v17.0.1.0.0 (Actual)

**Nuevas Funcionalidades:**
- ✅ Tipo de cambio manual editable en presupuestos, órdenes y facturas
- ✅ Auto-completado de TC con TC de la fecha
- ✅ Tracking de cambios de TC en chatter
- ✅ Transferencia automática de TC desde presupuestos/órdenes a facturas
- ✅ Impresión en pesos para facturas (con l10n_ar)
- ✅ Impresión en pesos para presupuestos de venta
- ✅ Impresión en pesos para órdenes de compra
- ✅ Registración contable usando TC manual (no TC nativo de Odoo)
- ✅ Análisis de líneas de compra con vistas pivot
- ✅ Smart buttons para toggle de impresión

**Correcciones:**
- ✅ Fix: Asientos desbalanceados al aplicar TC manual
- ✅ Fix: TC manual sobrescrito por onchange al crear factura
- ✅ Fix: Totales en PDF no cuadraban con líneas

**Arquitectura:**
- Herencia por extensión (no invasiva)
- Override de métodos l10n_ar para facturas argentinas
- Computed fields con depends para reactividad
- Deep copy para inmutabilidad de diccionarios
- Contextos especiales para operaciones batch

---

## Resumen de Archivos

```
surtecnica-reportes-dolar-peso/
├── __manifest__.py                   # Metadata del módulo
├── README.md                         # Este archivo
│
├── models/
│   ├── account_move.py              # Facturas: TC manual, impresión, contabilidad
│   ├── account_move_line.py         # Líneas factura: conversión de precios
│   ├── sale_order.py                # Presupuestos: TC manual, impresión
│   ├── sale_order_line.py           # Líneas presupuesto: conversión
│   ├── purchase_order.py            # Órdenes: TC manual, impresión
│   └── purchase_order_line.py       # Líneas orden: conversión + análisis
│
├── views/
│   ├── account_move_views.xml       # Smart button + campo TC en facturas
│   ├── sale_order_views.xml         # Smart button + campo TC en presupuestos
│   ├── purchase_order_views.xml     # Smart button + campo TC en órdenes
│   └── purchase_order_line_views.xml # Vistas análisis (list/pivot/search)
│
└── report/
    ├── account_move_report.xml      # PDF facturas con conversión a pesos
    ├── sale_order_report.xml        # PDF presupuestos con conversión
    └── purchase_order_report.xml    # PDF órdenes con conversión
```

---

**Fin del documento**

Para consultas técnicas o reportar issues, consultar la sección de Soporte.
