# -*- coding: utf-8 -*-

import logging
import calendar
import datetime
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, exceptions, _
from odoo.exceptions import AccessError, UserError, ValidationError

_logger = logging.getLogger(__name__)


class ForecastSales(models.Model):
    
    _name = 'x.forecast.sale'
    _description = "forecast sale"
    _order = 'x_mes desc, x_producto asc, id desc'

    x_cajas = fields.Integer(string="Cajas", default=0)
    x_comercial = fields.Many2one('res.users', string="Comercial", readonly=True)
    x_contacto = fields.Many2one('res.partner', string="Contacto", readonly=True)
    x_cuenta_analitica = fields.Many2one('account.analytic.account', string="Cuenta analítica", readonly=True)
    x_kg = fields.Float(string="Kg", default=0)
    x_mes = fields.Date(string="Mes", readonly=True)
    x_mes_format = fields.Char(string="Mes/Año", readonly=True, required=True)
    x_producto = fields.Many2one('product.product', string="Producto", readonly=True, required=True)
    x_rotacion = fields.Float(string="Rotación", compute="x_rotacion_compute")
    x_tipo = fields.Selection([
        ('cliente','Cliente'),
        ('canal','Canal')
        ], string="Tipo", readonly=True)
    x_unidades = fields.Integer(string="Unidades", default=0)
    x_locked = fields.Boolean("Bloqueado", default=False)

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        if(self._context.get('is_tree',False)):
            args += [('x_comercial', '=', self.env.user.id)]
        return super(ForecastSales, self)._search(args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)

    @api.onchange('x_unidades')
    def x_unidades_onchange(self):
        self.x_cajas = self.x_unidades * self.x_producto.x_studio_unidades_por_caja
        self.x_kg = self.x_cajas * self.x_producto.x_studio_peso_umb_gr / 1000

    @api.onchange('x_cajas')
    def x_cajas_onchange(self):
        self.x_unidades = self.x_cajas / (self.x_producto.x_studio_unidades_por_caja if self.x_producto.x_studio_unidades_por_caja > 0 else 1)
        self.x_kg = self.x_cajas * self.x_producto.x_studio_peso_umb_gr / 1000

    @api.onchange('x_kg')
    def x_kg_onchange(self):
        self.x_cajas = self.x_kg * 1000 / (self.x_producto.x_studio_peso_umb_gr if self.x_producto.x_studio_peso_umb_gr > 0 else 1)
        self.x_unidades = self.x_cajas / (self.x_producto.x_studio_unidades_por_caja if self.x_producto.x_studio_unidades_por_caja > 0 else 1)
        
    def x_rotacion_compute(self):
        for record in self:
            quantity_sale = 0
            end_date = datetime.datetime(datetime.date.today().year,datetime.date.today().month,1)
            start_date = end_date + relativedelta(months=-1)
            
            days_previous_month = (end_date + relativedelta(days=-1)).day
            number_of_sundays = len([1 for i in calendar.monthcalendar(start_date.year, start_date.month) if i[6] != 0])

            if(record.x_contacto):
                quantity_record = self.env['sale.order.line'].search([('product_id','=',record.x_producto.id),\
                        ('order_id.state','=','sale'),\
                        ('order_id.partner_invoice_id','=',record.x_contacto.id),\
                        ('order_id.date_order','>=',start_date),('order_id.date_order','<',end_date)])
                for line in quantity_record:
                    quantity_sale = quantity_sale + ((line.product_uom_qty * record.x_producto.x_studio_peso_umb_gr)/1000)
                record['x_rotacion'] = quantity_sale / (days_previous_month - number_of_sundays) / (record.x_contacto.x_studio_puntos_de_venta_foods if record.x_contacto.x_studio_puntos_de_venta_foods > 0 else 1)
                
            elif(record.x_cuenta_analitica):
                quantity_record = self.env['sale.order.line'].search([('product_id','=',record.x_producto.id),\
                        ('order_id.state','=','sale'),\
                        ('order_id.analytic_account_id','=',record.x_cuenta_analitica.id),\
                        ('order_id.date_order','>=',start_date),('order_id.date_order','<',end_date)])
                for line in quantity_record:
                    quantity_sale = quantity_sale + ((line.product_uom_qty * record.x_producto.x_studio_peso_umb_gr)/1000)
                record['x_rotacion'] = quantity_sale / (days_previous_month - number_of_sundays)
                
            else:
                record['x_rotacion'] = 0

    def forecast_change_field_locked(self):

        if(datetime.date.today().day > 25):
            test=""

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


    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        if(self._context.get('is_tree',False)):
            args += [('x_comercial', '=', self.env.user.id)]
        return super(ForecastCatalog, self)._search(args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)
