# -*- coding: utf-8 -*-
{
    'name': "product_custom",

    'summary': """
        Generar ficha tecnica""",

    'description': """
        Generar ficha tecnica
    """,

    'author': "Develoop Software",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/11.0/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'uom'],

    # always loaded
    'data': [
        # report
        'reports/fichatecnica_report.xml',
        'reports/fichatecnica.xml',
        'reports/fichatecnica_plus.xml',
        'reports/fichatecnica_logistica.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
}