# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

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
        
        args = list(args or [])
        if not self._rec_name:
            _logger.warning("Cannot execute name_search, no _rec_name defined on %s", self._name)
        elif not (name == '' and operator == 'ilike'):
            args += [(self._rec_name, operator, name)]
        ids = self._search(args, limit=limit, access_rights_uid=name_get_uid)
        recs = self.browse(ids)
        return models.lazy_name_get(recs.with_user(name_get_uid))