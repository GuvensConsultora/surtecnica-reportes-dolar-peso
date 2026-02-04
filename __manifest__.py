{
    'name': 'Reportes Dólar/Peso - Surtecnica',
    'version': '17.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Imprime facturas y presupuestos en USD mostrando valores en pesos',
    'description': """
        Módulo que permite:
        - Vista lista y pivot de líneas de orden de compra
        - Imprimir facturas en dólares con valores convertidos a pesos
        - Imprimir presupuestos de venta en dólares con valores en pesos
        - Imprimir órdenes de compra en dólares con valores en pesos
    """,
    'author': 'Surtecnica',
    'website': '',
    # Por qué: l10n_ar es necesario porque la factura argentina usa
    # l10n_ar.report_invoice_document (primary=True), un template independiente
    'depends': ['purchase', 'account', 'sale', 'l10n_ar'],
    'data': [
        'views/purchase_order_line_views.xml',
        'views/purchase_order_views.xml',
        'views/account_move_views.xml',
        'views/sale_order_views.xml',
        'report/account_move_report.xml',
        'report/purchase_order_report.xml',
        'report/sale_order_report.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
