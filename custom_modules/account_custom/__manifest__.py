# -*- coding: utf-8 -*-
{
    'name': "account_custom",
    'version': '0.1',
    'author': "Develoop Software",
    'category': 'Uncategorized',
    'summary': 'Modificar contabilidad',
    'website': "https://www.develoop.net/",
    'description': """
        - Modificala interface de facturas, si el dato analytic es vacio recupera el del cliente
        - Duplica los datos de la cabecera en la exportacion
        """,
    'depends': ['base','sale','account'],
    'data': [
        # 'security/ir.model.access.csv',
        'view/account.xml',
    ],
    'demo': [],
    'installable': True,
}