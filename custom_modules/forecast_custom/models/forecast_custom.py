# -*- coding: utf-8 -*-

import logging
import calendar
import datetime
import math
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, exceptions, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.float_utils import float_round
from odoo.tools.date_utils import start_of, end_of, add
from odoo.tools.misc import format_date

_logger = logging.getLogger(__name__)

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
    x_producto_pais = fields.Char('País', compute="get_product_country")
    x_rotacion = fields.Float(string="Rotación", readonly=True)
    x_tipo = fields.Selection([
        ('cliente','Cliente'),
        ('canal','Canal')
        ], string="Tipo", readonly=True)
    x_unidades = fields.Integer(string="Unidades")
    x_precio_caja = fields.Float("Precio €/caja", default=0)
    x_precio_importe = fields.Float("Importe", default=0, compute="calculate_importe")
    x_precio_kg = fields.Float("Precio €/kg", default=0, compute="calculate_kg")
    x_locked = fields.Boolean("Bloqueado", default=False)
    
    x_forecast_catalog_id = fields.Many2one('x.forecast.catalog', required=True, ondelete='cascade', index=True, copy=False)

    @api.depends('x_producto')
    def get_product_country(self):
        for record in self:
            record.x_producto_pais = record.x_producto.x_studio_familia

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

    @api.depends('x_precio_caja','x_cajas')
    def calculate_importe(self):
        for record in self:
            record.x_precio_importe = record.x_cajas * record.x_precio_caja

    @api.depends('x_precio_caja','x_kg')
    def calculate_kg(self):
        for record in self:
            record.x_precio_kg = record.x_kg * record.x_precio_caja

    def write(self, vals, is_cron=False):
        res = super(ForecastSales, self).write(vals)
        if is_cron == False and (vals.get('x_locked', False) or vals.get('x_cajas', False)):
            for record in self:
                month = record.x_mes + relativedelta(months=-1)
                self.process_forecast(month, record.x_producto.id)
        return res

    def forecast_change_field_locked(self, product_id=False, date=False):
        day = int(self.env['ir.config_parameter'].sudo().get_param('x_day_of_month_to_close_forecast'))
        if(datetime.date.today().day == day):
            self.process_forecast(datetime.date.today())
            self.process_forecast(datetime.date.today() + relativedelta(months=1))
            self.process_forecast(datetime.date.today() + relativedelta(months=2))

    def process_forecast(self, date_process, product_id=False, forecast_id=False, cajas=False):
        start_month = datetime.datetime(date_process.year, date_process.month, 1)
        start_month = start_month + relativedelta(months=1)
        end_month = start_month + relativedelta(months=1)
        month = start_month.month
        producto_caja = []

        #bloquear
        if product_id:
            forecast = self.env['x.forecast.sale'].sudo().search([('x_mes','>=',start_month),('x_mes','<',end_month),('x_producto','=',product_id)])
        else:
            forecast = self.env['x.forecast.sale'].sudo().search([('x_mes','>=',start_month),('x_mes','<',end_month)])
            for record in forecast:
                record.write({ 'x_locked': True }, True)
        
        for record in forecast:
            prod_caja = list(filter(lambda f:f['product_id'] == record.x_producto.id, producto_caja))
            cajas_val = record.x_cajas
            if forecast_id:
                if record.id == forecast_id[0]:
                    cajas_val = cajas
            if(prod_caja):
                prod_caja[0]['quantity'] = int(prod_caja[0]['quantity']) + cajas_val
            else:
                producto_caja.append({ 'product_id': record.x_producto.id, 'quantity': cajas_val })
        
        date_range = self._get_date_range()
        qty_week = 0
        for date_start, date_stop in date_range: 
            # Una semana repartida en dos meses pertenece al mes en el que tiene más días
            if (date_start.month != date_stop.month and date_stop.day > 3 and date_stop.month == month) or \
                (date_start.month == date_stop.month and date_start.month == month) or \
                (date_start.month != date_stop.month and date_stop.day <= 4 and date_start.month == month):
                qty_week = qty_week + 1
        
        for pro_caj in producto_caja:
            quantity = int(pro_caj['quantity']) / qty_week
            mrp_production_schedule = self.env['mrp.production.schedule'].sudo().search([('product_id','=',int(pro_caj['product_id']))])
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

    
    def _get_date_range(self):
        date_range = []
        first_day = start_of(fields.Date.today(), self.env.company.manufacturing_period)
        manufacturing_period = self.env.company.manufacturing_period_to_display
        week = (first_day.day // 7) + 1
        
        for i in range(week):
            first_day = first_day + relativedelta(days=-7)
            manufacturing_period = manufacturing_period + 1

        for columns in range(manufacturing_period):
            last_day = end_of(first_day, self.env.company.manufacturing_period)
            date_range.append((first_day, last_day))
            first_day = add(last_day, days=1)
        return date_range

    def block_forecast_selected(self, records):
        records.write({
            'x_locked': True
        })

    def unblock_forecast_selected(self, records):
        records.write({
            'x_locked': False
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
    x_producto_pais = fields.Char('País', compute="get_product_country")
    x_tipo = fields.Selection([
        ('cliente','Cliente'),
        ('canal','Canal')
        ], string="Tipo", required=True)
    x_precio_caja = fields.Float("Precio €/caja ", default=0)
    x_precio_caja_modificable = fields.Boolean(string="Es Modificable?")
    x_process = fields.Boolean("Accion", compute="get_price")

    x_forecast_sales = fields.One2many('x.forecast.sale', 'x_forecast_catalog_id', copy=True, auto_join=True)

    @api.depends('x_producto')
    def get_product_country(self):
        for record in self:
            record.x_producto_pais = record.x_producto.x_studio_familia

    @api.onchange('x_contacto','x_cuenta_analitica','x_tipo','x_producto')
    def get_price(self):
        for record in self:
            record.x_process = False
            if record.x_producto and record.x_contacto and record.x_tipo == "cliente" and record.x_contacto.property_product_pricelist:
                product = record.x_producto.with_context(
                    #lang=get_lang(self.env, self.order_id.partner_id.lang).code,
                    partner=record.x_contacto.id,
                    quantity=1,
                    date=datetime.date.today(),
                    pricelist=record.x_contacto.property_product_pricelist.id,
                    uom=record.x_producto.uom_id.id
                )
                if product.price:
                    record.x_precio_caja = product.price
                    record.x_precio_caja_modificable = False
                else:
                    #record.x_precio_caja = 0
                    record.x_precio_caja_modificable = True
            elif record.x_producto and record.x_cuenta_analitica and record.x_tipo == "canal" and record.x_cuenta_analitica.x_studio_tarifa:
                product = record.x_producto.with_context(
                    #lang=get_lang(self.env, self.order_id.partner_id.lang).code,
                    #partner=record.x_contacto.id,
                    quantity=1,
                    date=datetime.date.today(),
                    pricelist=record.x_cuenta_analitica.x_studio_tarifa.id,
                    uom=record.x_producto.uom_id.id
                )
                if product.price:
                    record.x_precio_caja = product.price
                    record.x_precio_caja_modificable = False
                else:
                    #record.x_precio_caja = 0
                    record.x_precio_caja_modificable = True
            else:
                #record.x_precio_caja = 0
                record.x_precio_caja_modificable = True

