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
    
    def send_by_edicom(self):
        
        url = self.env['ir.config_parameter'].get_param('edicom_api_url')
        username = self.env['ir.config_parameter'].get_param('edicom_api_username')
        password = self.env['ir.config_parameter'].get_param('edicom_api_password')
        
        sale_partner_id = ''
        sale_order_origin = self.env['sale.order'].search([('name','=',self.origin)], limit=1)
        if(sale_order_origin):
            if(sale_order_origin.partner_id):
                sale_partner_id = sale_order_origin.partner_id.x_studio_gln
                             
        detail = []
        if(self.order_line):
            for order_line in self.order_line:
                detail.append({ 
                    'clave1': self.name,
                    'clave2': order_line.sequence or "", 
                    'refean': order_line.product_id.x_studio_ean13 or "",
                    'dun14': order_line.product_id.x_studio_gtin14 or "",
                    'refetiq': order_line.product_id.x_studio_gtin14 or "",
                    'descmer': order_line.product_id.name or "",
                    'cantped': order_line.product_qty or "0",
                    })
        
        fecha = self.date_approve or ""
        fecha_solicitud_entrega = self.x_studio_fecha_solicitud_entrega or ""
        header = {
            'clave1': self.name,
            'nodo': 220,
            'numped': self.partner_ref or "", 
            'fecha': str(fecha),
            'fechaepr': str(fecha_solicitud_entrega),
            'fechatop': str(fecha_solicitud_entrega),
            'emisor': self.company_id.x_studio_gln or "",
            'comprador': self.company_id.x_studio_gln or "",
            'cliente': self.company_id.x_studio_gln or "",
            'receptor': sale_partner_id or "",
            'vendedor': self.partner_id.x_studio_gln or "",
            'qpaga': self.company_id.x_studio_gln or "",
            'destmsg': self.partner_id.x_studio_gln or "",
            'details': detail
        }
 
        response = requests.post(url+"/api/order-register", 
            data=json.dumps(header), 
            headers={'Content-type': 'application/json'}, 
            auth=HTTPBasicAuth(username,password),
            timeout=60)
        
        _message = ""
        if (response.status_code == 500):
            _message = "Ocurrio un error en el servidor."
            self.env['x_orders_salida'].create({
                'x_name': self.name,
                'x_studio_fecha_ltimo_intento_1': datetime.datetime.now(),
                'x_studio_descripcin_estado_1': "Ocurrió un error en el envió de pedido",
                'x_studio_field_rGeUU': "Error"
            })
        elif (response.status_code == 401):
            _message = "Las credenciales de autenticidad son incorrectas."
        elif (response.status_code == 200):
            _message = "La solicitud de presupuesto se envio correctamente."
            self.env['x_orders_salida'].create({
                'x_name': self.name,
                'x_studio_fecha_ltimo_intento_1': datetime.datetime.now(),
                'x_studio_descripcin_estado_1': "Estado del pedido en proceso",
                'x_studio_field_rGeUU': "status1"
            })
            
        new = self.env['purchase.edicom.modal.notification'].create({'msg':_message})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Información',
            'res_model': 'purchase.edicom.modal.notification',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id'    : new.id,
            'target': 'new',
        }

class edicom_form_notification_0(models.TransientModel):
    _name = "purchase.edicom.modal.notification"

    msg = fields.Text(readonly=True)
