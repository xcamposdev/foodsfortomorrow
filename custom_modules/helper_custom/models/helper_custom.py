# -*- coding: utf-8 -*-
from odoo import api, fields, models, exceptions, _
from odoo.exceptions import AccessError, UserError, ValidationError


class Update_Data_form(models.Model):
    
    _inherit = 'sale.order'

    def update_data(self):
        all_sales = self.env['sale.order'].search([('id','>',0)])
        for sale in all_sales:
            if(sale.analytic_account_id == False or sale.analytic_account_id.id == False):
                if(sale.partner_id):
                    sale.analytic_account_id = sale.partner_id.x_studio_canal_de_venta
        raise exceptions.Warning("COMPLETADO") 