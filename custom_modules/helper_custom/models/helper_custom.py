# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, exceptions, _
from odoo.exceptions import AccessError, UserError, ValidationError

_logger = logging.getLogger(__name__)

class Update_Data_form(models.Model):
    
    _inherit = 'sale.order'


    def update_client(self):
        all_partner = self.env['res.partner'].search([('id','>',0)])
        count = 0
        for partner in all_partner:
            if((partner.type == 'contact' or partner.type == 'delivery') and (partner.parent_id and partner.parent_id.id)):
                partner.write({
                    'x_studio_canal_de_venta': partner.parent_id.x_studio_canal_de_venta,
                    'x_studio_canal_de_venta_1': partner.parent_id.x_studio_canal_de_venta_1,
                    'user_id': partner.parent_id.user_id})
                _logger.info("ACTUALIZADO %s", partner.name)
                count = count + 1
        _logger.info("CANTIDAD TOTAL %s", count)


    def update_sale(self):
        all_sales = self.env['sale.order'].search([('id','>',0)])
        count = 0
        for sale in all_sales:
            sale.write({ 'user_id': sale.partner_id.user_id })
            _logger.info("ACTUALIZADO %s", sale.name)
            count = count + 1
        _logger.info("CANTIDAD TOTAL %s", count)