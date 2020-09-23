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

class EdicomAPIController(http.Controller):

    STATUS_PROCCESS = 'status1'
    STATUS_RECEIVED = 'status2'
    STATUS_CANCELLED = 'status3'
    STATUS_ERROR = 'Error'
    ID_LOG = 0
    INTENTS = 0
    
    @http.route('/edicom/input_desadv', auth='user', type='json', methods=['POST'], csrf=False)
    def edicom_api_order_desav(self):
        try:
            request.session.authenticate('Andres_Test', 'acastillo@develoop.net', 'Temp1243')

            #INICIALIZACION
            self.ID_LOG = 0
            self.INTENTS = 0
            body_data = json.loads(request.httprequest.data)
            albaran_edicom = body_data['albaran']
            albaran_lines = body_data['albaran_detail']
            
            #CREACION DE LOG
            self.save_odoo_log(albaran_edicom['numcontrato'], 'En Proceso...', self.STATUS_PROCCESS)
            _logger.info("Albaran y Detalle")
            _logger.info(albaran_edicom)
            _logger.info(albaran_lines)

            #VERIFICACION DE TODOS LOS DATOS QUE SE UTILIZA
            self.verify_data(albaran_edicom, albaran_lines)

            self.process_albaran(albaran_edicom, albaran_lines)

            self.save_odoo_log('', 'Completado exitosamente', self.STATUS_RECEIVED)
            return { 'status_code':200, 'message':'success' }
        except Exception as e:
            _logger.info(str(e))
            self.save_odoo_log('', 'Error general ' + str(e), self.STATUS_ERROR)
            return { 'status_code':500, 'message':'Error de tipo ' + str(e) }


    def verify_data(self, albaran_edicom, albaran_lines):
        msg = ""
        if(albaran_edicom):
            msg = msg + ('' if albaran_edicom['numcontrato'] else ' Falta el valor de: numcontrato \n')
            msg = msg + ('' if albaran_edicom['numalb'] else ' Falta el valor de: numalb \n')
            msg = msg + ('' if albaran_edicom['fecenvio'] else ' Falta el valor de: fecenvio \n')

        if(albaran_lines):
            for index in range(len(albaran_lines)):
                msg = msg + ('' if albaran_lines[index]['ean'] else ' Linea: ' + str(index) + ': Falta el valor de: ean \n')
                msg = msg + ('' if albaran_lines[index]['cenvfac'] else ' Linea: ' + str(index) + ': Falta el valor de: cenvfac \n')
                msg = msg + ('' if albaran_lines[index]['lote'] else ' Linea: ' + str(index) + ': Falta el valor de: lote \n')
                msg = msg + ('' if albaran_lines[index]['feccon'] else ' Linea: ' + str(index) + ': Falta el valor de: lote \n')
                msg = msg + ('' if albaran_lines[index]['sscc1'] else ' Linea: ' + str(index) + ': Falta el valor de: lote \n')

        if(msg != ''):
            raise exceptions.UserError("Faltan los siguientes datos " +  msg)


    def process_albaran(self, albaran_edicom, albaran_lines, company_id=1):
        _logger.info('Inicio del proceso: process_albaran')
        
        purchase = request.env['purchase.order'].search([('name','=', albaran_edicom['numcontrato'])], limit=1)
        if(purchase):

            pickings = request.env['stock.picking'].search(['&',('id','in', purchase.picking_ids.ids),('state','=','confirmed')], limit=1)
            pickings[0].write({
                'carrier_tracking_ref': albaran_edicom['numalb'],
                'date_done': self.getDateTime(albaran_edicom['fecenvio'])
            })

            if(purchase.order_line and pickings):
                for linea_alb in albaran_lines:
                    stock_move = self.search_in_stocks_moves(linea_alb, pickings, purchase.partner_id.id)
                    stock_production_lot = self.search_stock_production_lot(stock_move.product_id.id, linea_alb['lote'], self.getDateTime(linea_alb['feccon']), company_id)

                    stock_move_line = request.env['stock.move.line'].create({
                        'lot_id': stock_production_lot.id,
                        'qty_done': float(linea_alb['cenvfac'].replace(',', '.')),
                        'picking_id': pickings[0].id,
                        'move_id': stock_move.id,
                        'product_id': stock_move.product_id.id,
                        'company_id': company_id,
                        'product_uom_id': stock_move.product_uom.id,
                        'location_id': pickings[0].location_id.id,
                        'location_dest_id': pickings[0].location_dest_id.id,
                        'x_studio_sscc_1': linea_alb['sscc1']
                    })

                    stock_move.write({
                        'move_line_ids': [(4, stock_move_line.id)],
                        'state': 'confirmed'
                    })
                    _logger.info("Se termino de procesar linea")


    def search_in_stocks_moves(self, linea_alb, pickings, purchase_partner_id):
        exists = False
        _stock_move = False
        for picking in pickings:
            for stock_move in picking.move_ids_without_package:
                if(stock_move.product_id.x_studio_ean13 == linea_alb['ean']):
                    exists = True
                    _stock_move = stock_move
                    break
            if(exists == True):
                break

        if(exists):
            _logger.info("Se encontro en los stock moves del picking")
            return _stock_move
        else:
            product_supplierinfo = request.env['product.supplierinfo'].search('&',[('product_code','=',linea_alb['ean']),('partner_id','=',purchase_partner_id)], limit=1)
            if(product_supplierinfo):
                for picking in pickings:
                    for stock_move in picking.move_ids_without_package:
                        if(stock_move.product_id.id == product_supplierinfo.product_id.id):
                            exists = True
                            _stock_move = stock_move
                            break
                    if(exists == True):
                        break
            if(exists):
                _logger.info("Se encontro en supplierinfo del proveedor")
                return _stock_move
            else:
                product_search = request.env['product.template'].search([('x_studio_ean13','=',linea_alb['ean'])], limit=1)
                if(product_search):
                    _stock_move = request.env['stock.move'].create({
                        'picking_id': pickings[0].id,
                        'product_id': product_search.id,
                        'name': product_search.name,
                        'product_uom_qty': 0,
                        'product_uom': product_search.uom_id.id,
                        'location_id': pickings[0].location_id.id,
                        'location_dest_id': pickings[0].location_dest_id.id,
                        'state': 'confirmed'
                    })
                    pickings[0].write({
                        'move_ids_without_package': [(4, _stock_move.id)]
                    })
                    _logger.info("Se lo creo a partir del producto existente")
                    return _stock_move
                else:
                    raise exceptions.UserError("El codigo ean: " + linea_alb['ean'] + " no existe en productos")

    def search_stock_production_lot(self, product_id, lot_name, fec_envio, company_id):
        lot_search = request.env['stock.production.lot'].search(['&','&',('name','=',lot_name),('product_id','=',product_id),('company_id','=',company_id)])
        if(lot_search):
            _logger.info("Encontro stock_production_lot")
            return lot_search
        else:
            lot_id = request.env['stock.production.lot'].create({
                'name': lot_name,
                'life_date': fec_envio,
                'product_id': product_id,
                'company_id': company_id
            })
            _logger.info("Creo stock_production_lot")
            return lot_search

    def getDateTime(self, date):
        if(date):
            yyyy = int(date[0: 4])
            mm = int(date[4: 6])
            dd = int(date[6: 8])
            _datetime = datetime.date(yyyy, mm, dd)
            return _datetime
        else:
            return ""

    def save_odoo_log(self, name, description, status):
        try:
            if(self.ID_LOG > 0):
                _log = request.env['x_orders_desav'].search([('id','=',self.ID_LOG)], limit=1)
                _log.write({
                    'x_studio_fecha_ltimo_intento': datetime.datetime.now(),
                    'x_studio_descripcin_estado': description,
                    'x_studio_estado': status
                })
            else:
                _log = request.env['x_orders_desav'].create({
                    'x_name': name,
                    'x_studio_fecha_ltimo_intento': datetime.datetime.now(),
                    'x_studio_descripcin_estado': description,
                    'x_studio_estado': status
                })
                self.ID_LOG = _log.id
        except Exception as e:
            _logger.info(str(e))