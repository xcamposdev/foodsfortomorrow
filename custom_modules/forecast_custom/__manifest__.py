# -*- coding: utf-8 -*-
{
    'name': 'forecast_custom',
    'version': '1.0.0.0',
    'author': 'Develoop Software S.A.',
    'category': 'Forecast',
    'website': 'https://www.develoop.net/',
    'depends': ['base','web','analytic','product'],
    'summary': 'Forecast custom funcionality',
    'description': """
        Forecast custom funcionality
        """,
    'data': [
        'security/ir.model.access.csv',
        'views/assets.xml',
        'views/forecast_custom.xml',
        'wizard/forecast_wizard.xml',
    ],
    'qweb': [
        "static/src/xml/forecast_custom_qweb.xml",
    ],
    'images': ['static/description/icon.png'],
    'demo': [],
    'installable': True,
}
