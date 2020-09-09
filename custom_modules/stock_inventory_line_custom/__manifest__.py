# -*- coding: utf-8 -*-
{
    'name': "stock_inventory_line_custom",
    'version': '0.1',
    'author': "Develoop Software",
    'category': 'Uncategorized',
    'summary': 'Modificar funcionalidad de ajuste de inventario',
    'website': "https://www.develoop.net/",
    'description': """
        Modificar funcionalidad de ajuste de inventario agregando un campo motivo
        """,
    'depends': ['stock'],
    'data': [
        'views/stock_inventory_line_custom.xml',
    ],
    'demo': [],
    'installable': True,
}