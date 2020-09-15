# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import groupby

from odoo import api, fields, models, exceptions, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import float_is_zero, float_compare


class StockInventoryLineCustom0(models.Model):

    _inherit = 'stock.inventory.line'

    x_reason = fields.Char('Motivo')
    x_reason = fields.Selection(selection=[
            ('Rotura/Avería', 'Rotura/Avería'),
            ('Calidad', 'Calidad'),
            ('Devoluciones/Rechazos', 'Devoluciones/Rechazos'),
            ('Precaducado', 'Precaducado'),
            ('Caducado', 'Caducado'),
        ], string='Estado')