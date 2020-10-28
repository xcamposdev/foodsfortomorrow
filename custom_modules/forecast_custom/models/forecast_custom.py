# -*- coding: utf-8 -*-

import logging
import time
import calendar
from datetime import date
from odoo import api, fields, models, exceptions, _
from odoo.exceptions import AccessError, UserError, ValidationError

_logger = logging.getLogger(__name__)


class forecast_wizard_custom_0(models.TransientModel):
    
    _name = 'x.forecast.catalogo.wizard'

    date = fields.Date('Mes', default=date.today())

    def generate_forecast_ventas(self):
        self.ensure_one()
        startMonth = self.env.context.get('date', time.strftime('%Y-%m-01'))
        lastDay = calendar.monthrange(self.date.year, self.date.month)[1]
        endMonth = self.env.context.get('date', time.strftime('%Y-%m-' + str(lastDay)))
        exists = self.env['x_forecast_ventas'].search(['&','&',('x_studio_comercial','=',self.env.user.id),('x_studio_mes','>=',startMonth),('x_studio_mes','<=',endMonth)], limit=1)
        if(exists):
            raise ValidationError("Ya existe registros generados para el mes: %s" % (startMonth))

        data_catalogo = self.env['x_forecast_catalogo'].search([('x_comercial','=',self.env.user.id)])
        if(data_catalogo):
            for catalogo in data_catalogo:
                self.env['x_forecast_ventas'].create({
                    'x_studio_mes': self.date.today(),
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