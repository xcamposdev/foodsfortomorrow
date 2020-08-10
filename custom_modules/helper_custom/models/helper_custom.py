# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, exceptions, _
from odoo.exceptions import AccessError, UserError, ValidationError

_logger = logging.getLogger(__name__)

class Update_Data_form(models.Model):
    
    _inherit = 'sale.order'

    def update_data(self):
        all_sales = self.env['sale.order'].search([('id','>',0)])
        count = 0
        for sale in all_sales:
            if(sale.analytic_account_id == False or sale.analytic_account_id.id == False):
                if(sale.partner_id):
                    sale.write({ 'analytic_account_id': sale.partner_id.x_studio_canal_de_venta.id })
                    _logger.info("ACTUALIZADO %s", sale.name)
                    count = count + 1
        _logger.info("CANTIDAD TOTAL %s", count)