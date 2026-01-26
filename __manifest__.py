{
    'name': 'Reportes Dólar/Peso - Surtecnica',
    'version': '17.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Imprime facturas en USD mostrando valores en pesos',
    'description': """
        Módulo que permite:
        - Vista lista y pivot de líneas de orden de compra
        - Imprimir facturas en dólares con valores convertidos a pesos
    """,
    'author': 'Surtecnica',
    'website': '',
    'depends': ['purchase', 'account'],
    'data': [
        'views/purchase_order_line_views.xml',
        'views/account_move_views.xml',
        'report/account_move_report.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
