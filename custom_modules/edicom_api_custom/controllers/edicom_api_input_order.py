# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import json
import datetime
import copy 

from odoo import http
from odoo.http import request
from odoo import exceptions

_logger = logging.getLogger(__name__)

class EdicomAPIInputOrder(http.Controller):

    STATUS_PROCCESS = 'status1'
    STATUS_RECEIVED = 'status2'
    STATUS_CANCELLED = 'status3'
    STATUS_ERROR = 'Error'
    ID_LOG = 0
    INTENTS = 0
    
    @http.route('/edicom/input_order', auth='user', type='json', methods=['POST'], csrf=False)
    def edicom_api_input_order(self):
        try:
            #request.session.authenticate('Andres_Test', 'acastillo@develoop.net', 'Temp1243')
            #INICIALIZACION
            self.ID_LOG = 0
            self.INTENTS = 0
            body_data = json.loads(request.httprequest.data)
            order_edicom = body_data['order']
            order_lines = body_data['order_detail']
            
            #CREACION DE LOG
            self.save_log_input_order(order_edicom['numped'], 'En Proceso...', self.STATUS_PROCCESS)
            #request.env.cr.commit()
            #self._cr.execute('SAVEPOINT import')
            _logger.info("Order de entrada: Order y Detalle")
            _logger.info(order_edicom)
            _logger.info(order_lines)

            #VERIFICACION DE TODOS LOS DATOS QUE SE UTILIZA
            self.verify_data(order_edicom, order_lines)

            self.process_order(order_edicom, order_lines)

            self.save_log_input_order('', 'Completado exitosamente', self.STATUS_RECEIVED)
            #request.env.cr.commit()
            #self._cr.execute('RELEASE SAVEPOINT import')
            return { 'status_code':200, 'message':'success' }
        except Exception as e:
            _logger.info(str(e))
            #request.env.cr.rollback()
            #self._cr.execute('ROLLBACK TO SAVEPOINT import')
            if(e.name is None):
                self.save_log_input_order('', 'Error general: ' + str(e), self.STATUS_ERROR)
            else:
                self.save_log_input_order('', 'Error general: ' + str(e.name), self.STATUS_ERROR)
            return { 'status_code':500, 'message':'Error de tipo ' + str(e) }


    def verify_data(self, order_edicom, order_lines):
        msg = ""
        if(order_edicom):
            msg += '' if order_edicom['numped'] else 'Falta el valor de: numped \r\n'
            msg += '' if order_edicom['fecha'] else 'Falta el valor de: fecha \r\n'
            msg += '' if order_edicom['fechaepr'] else 'Falta el valor de: fechaepr \r\n'
            
            if(order_edicom['cliente'] is None):
                msg += 'Falta el valor de: cliente \r\n'
            elif(not request.env['res.partner'].search([('x_studio_gln','=',order_edicom['cliente'])])):
                msg += 'No se encontro el cliente con GLN: ' + str(order_edicom['cliente']) + '\r\n'
            
            if(order_edicom['receptor'] is None):
                msg += 'Falta el valor de: receptor \r\n'
            elif(not request.env['res.partner'].search([('x_studio_gln','=',order_edicom['receptor'])])):
                msg += 'No se encontro el receptor con GLN: ' + str(order_edicom['receptor']) + '\r\n'

            if(order_edicom['qpaga'] is None):
                msg += 'Falta el valor de: qpaga \r\n'
            elif(not request.env['res.partner'].search([('x_studio_gln','=',order_edicom['qpaga'])])):
                msg += 'No se encontro el qpaga con GLN: ' + str(order_edicom['qpaga']) + '\r\n'

        if(order_lines):
            for index in range(len(order_lines)):
                if(order_lines[index]['refean'] is None):
                    msg += 'Linea: ' + str(index) + ': Falta el valor de: refean \r\n'
                elif(not request.env['product.product'].search([('x_studio_ean13','=',order_lines[index]['refean'])], limit=1)):
                    msg += 'Linea: ' + str(index) + ': Falta el valor de: refean \r\n'

                msg += '' if order_lines[index]['cantped'] else 'Linea: ' + str(index) + ': Falta el valor de: cantped \r\n'
                

        if(msg != ''):
            raise exceptions.UserError("Faltan los siguientes datos \r\n" +  msg)


    def process_order(self, order_edicom, order_lines, company_id=1):
        _logger.info('Order de entrada: Inicio del proceso: process_order')

        # super(EdicomAPIInputOrder, self).onchange_partner_id()
        client = request.env['res.partner'].search([('x_studio_gln','=',order_edicom['cliente'])], limit=1)
        client_shipping = request.env['res.partner'].search([('x_studio_gln','=',order_edicom['receptor'])], limit=1)
        client_invoice = request.env['res.partner'].search([('x_studio_gln','=',order_edicom['qpaga'])], limit=1)

        order = request.env['sale.order'].create({
            'client_order_ref': order_edicom['numped'],
            'date_order': self.getDateTime(order_edicom['fecha']),
            'commitment_date': self.getDateTime(order_edicom['fechaepr']),
            'partner_id': client.id,
            'partner_shipping_id': client_shipping.id,
            'partner_invoice_id': client_invoice.id,
            # 'pricelist_id' => intval($inputOrder->tarifa),
            # 'payment_term_id'=> intval($inputOrder->plazopago),
            # 'user_id' => intval($inputOrder->comercial),
            # 'warehouse_id' => intval($inputOrder->almacen)
        })
        #new_line.product_id_change()
        if(order):
            for index in range(len(order_lines)):

                product_id = request.env['product.product'].search([('x_studio_ean13','=',order_lines[index]['refean'])], limit=1)

                request.env['sale.order.line'].create({
                    'order_id': order.id,
                    'product_id': product_id.id,
                    'product_uom_qty': order_lines[index]['cantped']
#					'price_unit' => floatval($detail->precio),
#					'tax_id' => array($detail->impuestos)
                })
       
    def getDateTime(self, date):
        if(date):
            yyyy = int(date[0: 4])
            mm = int(date[4: 6])
            dd = int(date[6: 8])
            _datetime = datetime.date(yyyy, mm, dd)
            return _datetime
        else:
            return ""

    def save_log_input_order(self, name, description, status):
        try:
            if(self.ID_LOG > 0):
                _log = request.env['x_orders_entrada'].search([('id','=',self.ID_LOG)], limit=1)
                _log.write({
                    'x_studio_fecha_ltimo_intento': datetime.datetime.now(),
                    'x_studio_descripcin_estado': description,
                    'x_studio_estado': status
                })
            else:
                _log = request.env['x_orders_entrada'].create({
                    'x_name': name,
                    'x_studio_fecha_ltimo_intento': datetime.datetime.now(),
                    'x_studio_descripcin_estado': description,
                    'x_studio_estado': status
                })
                self.ID_LOG = _log.id
        except Exception as e:
            _logger.info(str(e))
