# -*- coding: utf-8 -*-

import logging
import calendar
import datetime
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, exceptions, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.float_utils import float_round

_logger = logging.getLogger(__name__)

#x_studio_unidades_por_caja
class ForecastSales(models.Model):
    
    _name = 'x.forecast.sale'
    _description = "forecast sale"
    _order = 'x_mes desc, x_producto asc, id desc'

    x_cajas = fields.Integer(string="Cajas")
    x_comercial = fields.Many2one('res.users', string="Comercial", readonly=True)
    x_contacto = fields.Many2one('res.partner', string="Contacto", readonly=True)
    x_cuenta_analitica = fields.Many2one('account.analytic.account', string="Cuenta analítica", readonly=True)
    x_kg = fields.Float(string="Kg")
    x_mes = fields.Date(string="Mes", readonly=True)
    x_mes_format = fields.Char(string="Mes/Año", readonly=True, required=True)
    x_producto = fields.Many2one('product.product', string="Producto", readonly=True, required=True)
    x_rotacion = fields.Float(string="Rotación", readonly=True)
    x_tipo = fields.Selection([
        ('cliente','Cliente'),
        ('canal','Canal')
        ], string="Tipo", readonly=True)
    x_unidades = fields.Integer(string="Unidades")
    x_locked = fields.Boolean("Bloqueado", default=False)
    
    x_forecast_catalog_id = fields.Many2one('x.forecast.catalog', required=True, ondelete='cascade', index=True, copy=False)

    def onchange(self, values, field_name, field_onchange):
        # OVERRIDE
        # As the dynamic lines in this model are quite complex, we need to ensure some computations are done exactly
        # at the beginning / at the end of the onchange mechanism. So, the onchange recursivity is disabled.
        return super(ForecastSales, self.with_context(recursive_onchanges=False)).onchange(values, field_name, field_onchange)

    @api.onchange('x_unidades')
    def x_unidades_change(self):
        unidades_cajas = self.x_producto.x_studio_unidades_caja_ud + self.x_producto.x_studio_n_bolsas
        self.x_cajas = self.x_unidades / (unidades_cajas if unidades_cajas > 0 else 1)
        self.x_kg = self.x_cajas * self.x_producto.x_studio_peso_umb_gr / 1000
        
        resto = self.x_unidades % (unidades_cajas if unidades_cajas > 0 else 1)
        #recursive_onchanges
        if(resto > 0):
            return {
                'warning':{
                    'title': "Información: División inexacta",
                    'message': "La división entre " + str(self.x_unidades) + " (unidades) y " + str(unidades_cajas) + " (unidades por caja) genera un resto de " + str(resto)
                }
            }
    
    @api.onchange('x_cajas')
    def x_cajas_change(self):
        unidades_cajas = self.x_producto.x_studio_unidades_caja_ud + self.x_producto.x_studio_n_bolsas
        self.x_unidades = self.x_cajas * unidades_cajas
        self.x_kg = self.x_cajas * self.x_producto.x_studio_peso_umb_gr / 1000
        

    @api.onchange('x_kg')
    def x_kg_change(self):
        unidades_cajas = self.x_producto.x_studio_unidades_caja_ud + self.x_producto.x_studio_n_bolsas
        self.x_cajas = self.x_kg * 1000 / (self.x_producto.x_studio_peso_umb_gr if self.x_producto.x_studio_peso_umb_gr > 0 else 1)
        self.x_unidades = self.x_cajas * unidades_cajas
        resto = self.x_kg * 1000 % (self.x_producto.x_studio_peso_umb_gr if self.x_producto.x_studio_peso_umb_gr > 0 else 1)
        if(resto > 0):
            return {
                'warning':{
                    'title': "Información: División inexacta",
                    'message': "La división entre " + str(self.x_kg * 1000) + " (gramos) y " + str(self.x_producto.x_studio_peso_umb_gr) + " (peso neto UMB gr) genera un resto de " + str(resto)
                }
            }

    @api.onchange('x_locked')
    def x_locked_onchange(self):
        if self.x_locked:
            self.forecast_change_field_locked(self.x_producto.id)

    def forecast_change_field_locked(self, product_id=False):
        day = int(self.env['ir.config_parameter'].sudo().get_param('x_day_of_month_to_close_forecast'))
        if(datetime.date.today().day == day):
            start_month = datetime.datetime(datetime.date.today().year, datetime.date.today().month, 1)
            start_month = start_month + relativedelta(months=1)
            end_month = start_month + relativedelta(months=1)
            month = start_month.month
            producto_caja = []

            forecast = self.env['x.forecast.sale'].sudo().search([('x_mes','>=',start_month),('x_mes','<',end_month)])
            if(product_id):
                forecast = self.env['x.forecast.sale'].sudo().search([('x_mes','>=',start_month),('x_mes','<',end_month),('x_producto','=',product_id)])
            
            for record in forecast:
                record.write({ 'x_locked': True })
                prod_caja = list(filter(lambda f:f['product_id'] == record.x_producto.id, producto_caja))
                if(prod_caja):
                    prod_caja[0]['quantity'] = int(prod_caja[0]['quantity']) + record.x_cajas
                else:
                    producto_caja.append({ 'product_id': record.x_producto.id, 'quantity': record.x_cajas })
            
            date_range = self.env.company._get_date_range()
            qty_week = 0
            for date_start, date_stop in date_range: 
                # Una semana repartida en dos meses pertenece al mes en el que tiene más días
                if (date_start.month != date_stop.month and date_stop.day > 3 and date_stop.month == month) or \
                    (date_start.month == date_stop.month and date_start.month == month) or \
                    (date_start.month != date_stop.month and date_stop.day <= 4 and date_start.month == month):
                    qty_week = qty_week + 1
            
            for pro_caj in producto_caja:
                quantity = int(pro_caj['quantity']) / qty_week
                mrp_production_schedule = self.env['mrp.production.schedule'].search([('product_id','=',int(pro_caj['product_id']))])
                if(quantity > 0 and mrp_production_schedule):
                    for date_start, date_stop in date_range:
                        if (date_start.month != date_stop.month and date_stop.day > 3 and date_stop.month == month) or \
                            (date_start.month == date_stop.month and date_start.month == month) or \
                            (date_start.month != date_stop.month and date_stop.day <= 4 and date_start.month == month):

                            existing_forecast = mrp_production_schedule.forecast_ids.filtered(lambda f:f.date >= date_start and f.date <= date_stop)
                            quantity = float_round(float(quantity), precision_rounding=mrp_production_schedule.product_uom_id.rounding)
                            quantity_to_add = quantity # - sum(existing_forecast.mapped('forecast_qty'))
                            if existing_forecast:
                                new_qty = quantity_to_add #existing_forecast[0].forecast_qty + quantity_to_add
                                new_qty = float_round(new_qty, precision_rounding=mrp_production_schedule.product_uom_id.rounding)
                                existing_forecast[0].write({'forecast_qty': new_qty})
                            else:
                                existing_forecast.create({
                                    'forecast_qty': quantity,
                                    'date': date_stop,
                                    'replenish_qty': 0,
                                    'production_schedule_id': mrp_production_schedule.id
                                })

class ForecastCatalog(models.Model):

    _name = 'x.forecast.catalog'
    _description = "forecast catalog"
    _order = 'x_producto asc, x_contacto asc, id asc'


    def _get_domain_x_comercial(self):
        return [('id','=',self.env.user.id)]

    x_comercial = fields.Many2one('res.users', string="Comercial", required=True, 
        default=lambda self: self.env.user.id, domain=_get_domain_x_comercial)
    x_contacto = fields.Many2one('res.partner', string="Contacto", domain="[('parent_id', '=', False)]")
    x_cuenta_analitica = fields.Many2one('account.analytic.account', string="Cuenta analítica")
    x_producto = fields.Many2one('product.product', string="Producto", required=True)
    x_tipo = fields.Selection([
        ('cliente','Cliente'),
        ('canal','Canal')
        ], string="Tipo", required=True)

    x_forecast_sales = fields.One2many('x.forecast.sale', 'x_forecast_catalog_id', copy=True, auto_join=True)
