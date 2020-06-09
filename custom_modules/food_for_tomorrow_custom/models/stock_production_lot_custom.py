# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class stock_production_lot_custom_search(models.Model):

    _inherit = 'stock.production.lot'


    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        if not args:
            args = []
        if name:
            stock_production_lot = []
            stock_production_lot = self._search([('id', '=', name)] + args, limit=limit, access_rights_uid=name_get_uid)
            if not stock_production_lot:
                stock_production_lot = self._search([('name', '=', name)] + args, limit=limit, access_rights_uid=name_get_uid)
        return models.lazy_name_get(self.browse(stock_production_lot).with_user(name_get_uid))