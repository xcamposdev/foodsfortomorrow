# -*- coding: utf-8 -*-

import requests
import logging
import json
from odoo import api, fields, models, exceptions
from requests.auth import HTTPBasicAuth
import datetime

_logger = logging.getLogger(__name__)


class edicom_form(models.Model):

    _inherit = 'purchase.order'

    is_sent_edicom = fields.Boolean(default=False)

    def truncate_data(self, data, _len):
        to_return = ""
        if(data):
            to_return = data or ""
            if(len(data) > _len):
                to_return = data[0:_len]
        return to_return

    def date_format(self, data, format):
        to_return = ""
        if(data):
            to_return = data or ""
            if(data != ""):
                to_return = data.strftime(format)
        return to_return
    
    def send_by_edicom(self):

        url = self.env['ir.config_parameter'].get_param('edicom_api_url')
        username = self.env['ir.config_parameter'].get_param('edicom_api_username')
        password = self.env['ir.config_parameter'].get_param('edicom_api_password')

        sale_partner_id = ''
        sale_order_origin = self.env['sale.order'].search([('name', '=', self.origin)], limit=1)
        if(sale_order_origin):
            if(sale_order_origin.partner_id):
                sale_partner_id = sale_order_origin.partner_id.x_studio_gln

        name = ""
        if(len(self.name) > 5):
            _posInit = len(self.name)-5
            _posEnd = len(self.name)
            name = self.name[_posInit:_posEnd]

        detail = []
        if(self.order_line):
            for order_line in self.order_line:
                detail.append({
                    'clave1': name,
                    'clave2': order_line.id or "",
                    'refean': order_line.product_id.x_studio_ean13 or "",
                    'dun14': order_line.product_id.x_studio_gtin14 or "",
                    'refetiq': order_line.product_id.x_studio_gtin14 or "",
                    'descmer': order_line.product_id.name or "",
                    'cantped': order_line.product_qty or "0",
                })

        current_register_log = self.env['x_orders_salida'].create({
            'x_name': self.name,
            'x_studio_fecha_ltimo_intento_1': datetime.datetime.now(),
            'x_studio_descripcin_estado_1': "",
            'x_studio_field_rGeUU': "status1"
        })
        
        header = {
            'clave1': name,
            'nodo': 220,
            'numped': self.truncate_data(self.partner_ref, 15),
            'fecha': self.date_format(self.date_approve, "%Y%m%d"),
            'fechaepr': self.date_format(self.x_studio_fecha_solicitud_entrega, "%Y%m%d"),
            'fechatop': self.date_format(self.x_studio_fecha_solicitud_entrega, "%Y%m%d"),
            'emisor': self.truncate_data(self.company_id.x_studio_gln, 17),
            'comprador': self.truncate_data(self.company_id.x_studio_gln, 17),
            'cliente': self.truncate_data(self.company_id.x_studio_gln, 17),
            'receptor': self.truncate_data(sale_partner_id, 17),
            'vendedor': self.truncate_data(self.partner_id.x_studio_gln, 17),
            'qpaga': self.truncate_data(self.company_id.x_studio_gln, 17),
            'destmsg': self.truncate_data(self.partner_id.x_studio_gln, 17),
            'details': detail,
            'id_log': current_register_log.id
        }
        
        response = requests.post(url+"/api/order-register",
                                 data=json.dumps(header),
                                 headers={'Content-type': 'application/json'},
                                 auth=HTTPBasicAuth(username, password),
                                 timeout=60)

        _message = ""

        if (response.status_code == 500):
            _message = "Ocurrio un error en el servidor."
            current_register_log.write({
                'x_name': self.name,
                'x_studio_fecha_ltimo_intento_1': datetime.datetime.now(),
                'x_studio_descripcin_estado_1': "Ocurrió un error en el envió de pedido",
                'x_studio_field_rGeUU': "Error"
            })
        elif (response.status_code == 401):
            _message = "Las credenciales de autenticidad son incorrectas."
        elif (response.status_code == 200):
            _message = "La solicitud de presupuesto se envio correctamente."
            current_register_log.write({
                'x_name': self.name,
                'x_studio_fecha_ltimo_intento_1': datetime.datetime.now(),
                'x_studio_descripcin_estado_1': "Estado del pedido en proceso",
                'x_studio_field_rGeUU': "status1"
            })
            self.is_sent_edicom = True

        new = self.env['purchase.edicom.modal.notification'].create({'msg': _message})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Información',
            'res_model': 'purchase.edicom.modal.notification',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': new.id,
            'target': 'new',
        }
    
class edicom_form_notification_0(models.TransientModel):
    _name = "purchase.edicom.modal.notification"

    msg = fields.Text(readonly=True)
