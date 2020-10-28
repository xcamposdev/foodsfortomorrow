# -*- coding: utf-8 -*-

import logging
import calendar
import datetime
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, exceptions, _
from odoo.exceptions import AccessError, UserError, ValidationError

_logger = logging.getLogger(__name__)


class forecast_wizard_custom_0(models.TransientModel):
    
    _name = 'x.forecast.catalogo.wizard'
    _description = "Modal To Generate"
    
    date_generate = fields.Date('Mes', default=datetime.date.today())

    def generate_forecast_ventas(self):
        self.ensure_one()
        startMonth = datetime.datetime(self.date_generate.year, self.date_generate.month, 1)
        endMonth = startMonth + relativedelta(months=1)
        _logger.info(startMonth)
        _logger.info(endMonth)
        
        exists = self.env['x_forecast_ventas'].search(['&','&',('x_studio_comercial','=',self.env.user.id),('x_studio_mes','>=',startMonth),('x_studio_mes','<',endMonth)], limit=1)
        if(exists):
            raise ValidationError("Ya existe registros generados para el mes: %s" % (startMonth.strftime('%m/%Y1')))

        data_catalogo = self.env['x_forecast_catalogo'].search([('x_comercial','=',self.env.user.id)])
        if(data_catalogo):
            for catalogo in data_catalogo:
                date_format = (str(self.date_generate.month) if len(str(self.date_generate.month))==2 else "0" + str(self.date_generate.month)) + "/" + str(self.date_generate.year)
                
                self.env['x_forecast_ventas'].create({
                    'x_studio_mes_format': date_format,
                    'x_studio_mes': self.date_generate,
                    'x_studio_producto': catalogo.x_producto.id,
                    'x_studio_rotacion': 0,
                    'x_studio_kg': 0,
                    'x_studio_cajas': 0,
                    'x_studio_tipo': catalogo.x_tipo,
                    'x_studio_contacto': catalogo.x_contacto.id,
                    'x_studio_cuenta_analitica': catalogo.x_cuenta_analitica.id,
                    'x_studio_comercial': catalogo.x_comercial.id
                })
        
        return {
            'name': "Forecast-ventas",
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'x_forecast_ventas',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'main',
            'nodestroy': True
        }