# -*- coding: utf-8 -*-

import logging
import calendar
import datetime
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, exceptions, _
from odoo.exceptions import AccessError, UserError, ValidationError

_logger = logging.getLogger(__name__)


class forecast_wizard_custom_0(models.TransientModel):
    
    _name = 'x.forecast.catalog.wizard'
    _description = "Modal To Generate"
    
    date_generate = fields.Date('Mes', default=datetime.date.today())

    def generate_forecast_ventas(self):
        self.ensure_one()
        startMonth = datetime.datetime(self.date_generate.year, self.date_generate.month, 1)
        endMonth = startMonth + relativedelta(months=1)
        _logger.info(startMonth)
        _logger.info(endMonth)
        
        exists = self.env['x.forecast.sale'].search(['&','&',('x_comercial','=',self.env.user.id),('x_mes','>=',startMonth),('x_mes','<',endMonth)], limit=1)
        if(exists):
            raise ValidationError("Ya existe registros generados para el mes: %s" % (startMonth.strftime('%m/%Y')))

        data_catalogo = self.env['x.forecast.catalog'].search([('x_comercial','=',self.env.user.id)])
        if(data_catalogo):
            for catalogo in data_catalogo:
                date_format = (str(self.date_generate.month) if len(str(self.date_generate.month))==2 else "0" + str(self.date_generate.month)) + "/" + str(self.date_generate.year)
                
                rotacion = self.x_rotacion_compute(catalogo)

                self.env['x.forecast.sale'].create({
                    'x_mes_format': date_format,
                    'x_mes': self.date_generate,
                    'x_producto': catalogo.x_producto.id,
                    'x_rotacion': rotacion,
                    'x_kg': 0,
                    'x_cajas': 0,
                    'x_tipo': catalogo.x_tipo,
                    'x_contacto': catalogo.x_contacto.id,
                    'x_cuenta_analitica': catalogo.x_cuenta_analitica.id,
                    'x_comercial': catalogo.x_comercial.id,
                    'x_locked': False
                })
        
        return {
            'name': "Ventas",
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'x.forecast.sale',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'main',
            'nodestroy': True
        }

    def x_rotacion_compute(self, catalog):
        quantity_sale = 0
        end_date = datetime.datetime(datetime.date.today().year,datetime.date.today().month,1)
        start_date = end_date + relativedelta(months=-1)
        
        days_previous_month = (end_date + relativedelta(days=-1)).day
        number_of_sundays = len([1 for i in calendar.monthcalendar(start_date.year, start_date.month) if i[6] != 0])

        if(catalog.x_contacto):
            quantity_record = self.env['sale.order.line'].search([('product_id','=',catalog.x_producto.id),\
                    ('order_id.state','=','sale'),\
                    ('order_id.partner_invoice_id','=',catalog.x_contacto.id),\
                    ('order_id.date_order','>=',start_date),('order_id.date_order','<',end_date)])
            for line in quantity_record:
                quantity_sale = quantity_sale + (line.product_uom_qty * (catalog.x_producto.x_studio_unidades_por_caja if catalog.x_producto.x_studio_unidades_por_caja > 0 else 1))
            return quantity_sale / (days_previous_month - number_of_sundays) / (catalog.x_contacto.x_studio_puntos_de_venta_foods if catalog.x_contacto.x_studio_puntos_de_venta_foods > 0 else 1)
            
        elif(catalog.x_cuenta_analitica):
            quantity_record = self.env['sale.order.line'].search([('product_id','=',catalog.x_producto.id),\
                    ('order_id.state','=','sale'),\
                    ('order_id.analytic_account_id','=',catalog.x_cuenta_analitica.id),\
                    ('order_id.date_order','>=',start_date),('order_id.date_order','<',end_date)])
            for line in quantity_record:
                quantity_sale = quantity_sale + (line.product_uom_qty * (catalog.x_producto.x_studio_unidades_por_caja if catalog.x_producto.x_studio_unidades_por_caja > 0 else 1))
            return quantity_sale / (days_previous_month - number_of_sundays)
            
        else:
            return 0