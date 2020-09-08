# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import groupby

from odoo import api, fields, models, exceptions, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import float_is_zero, float_compare


class PurchaseOrderCustom0(models.Model):

    _inherit = 'purchase.order'

    READONLY_STATES = {
        'purchase': [('readonly', True)],
        'done': [('readonly', True)],
        'cancel': [('readonly', True)],
    }

    partner_id = fields.Many2one(
        'res.partner', string='Vendor', required=True, states=READONLY_STATES, 
        change_default=True, tracking=True, 
        domain="['|','&','&', ('company_id', '=', False), ('company_id', '=', company_id), ('parent_id', '=', False), ('supplier_rank', '>', 0)]", 
        help="You can find a vendor by its Name, TIN, Email or Internal Reference.")
