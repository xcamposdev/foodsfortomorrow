# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import json
import datetime

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class EdicomAPIController(http.Controller):

    STATUS_PROCCESS = 'status1'
    STATUS_SENT = 'status2'
    STATUS_CANCELLED = 'status3'
    STATUS_ERROR = 'Error'

    def authentication(self):
        try:
            username = request.httprequest.headers.environ['HTTP_USERNAME']
            password = request.httprequest.headers.environ['HTTP_PASSWORD']

            if(username == 'secret' and password == 'secret'):
                return True
            else:
                return False
        except Exception as e:
            _logger.info(str(e))
            return False

    @http.route('/edicom/input_desadv', auth='user', type='json', methods=['POST'], csrf=False)
    def edicom_api_order_desav(self):
        try:
            if(self.authentication() == True):
                body_data = json.loads(request.httprequest.data)
                albaran_edicom = body_data['albaran']
                albaran_lines = body_data['albaran_detail']

                request.session.authenticate('Andres_Test', 'acastillo@develoop.net', 'Temp1243')
                session_info =  request.env['ir.http'].session_info()

                purchase = request.env['purchase.order'].search_read([('name','=', albaran_edicom['numcontrato'])], ['order_line','picking_ids'], limit=1)
                if(purchase):
                    order_lines = purchase[0]['order_line']
                    picking_ids = purchase[0]['picking_ids']

                    if(order_lines and picking_ids):
                        picking_id = purchase[0]['picking_ids'][0]
                        stock_move_stock = request.env['stock.picking'].search_read([('id','=', picking_id)], ['id', 'location_id', 'location_dest_id'])
                        if (stock_move_stock):
                            locationId = stock_move_stock[0]['location_id'][0]
                            locationDestId = stock_move_stock[0]['location_dest_id'][0]

                        order_lines_search = request.env['purchase.order.line'].search_read([('id','in', order_lines)], ['id','name','display_name','product_id','product_uom','move_ids'])
                        if(order_lines_search):
                            if(self.saveAlbaranData(picking_id, body_data['albaran']['numalb'], self.getDateTime(albaran_edicom['fecenvio']))):

                                products_ids = self.get_Product_ids(order_lines_search)
                                moves_ids = self.get_moves_ids(order_lines_search)
                                a1 = request.env['product.supplierinfo'].search_read([('product_tmpl_id','in',products_ids)], ['id','product_code','product_tmpl_id'])
                                a2 = request.env['product.template'].search_read([('product_variant_ids','in',products_ids)], ['id','x_studio_ean13','product_variant_ids'])
                                ap = [];
                                firtsOrderLineId = 0

                                for index in range(len(order_lines_search)):
                                    order_line_id = order_lines_search[index]['id']
                                    productId = products_ids[index] #?
                                    arrayMoveId = moves_ids[index]  #?
                                    productUomId = order_lines_search[index]['product_uom'][0]
                                    linAlbObj = None
                                    indexLineObj = -1

                                    if(index == 0):
                                        firtsOrderLineId = order_line_id
								
                                    for index_line in range(len(albaran_lines)):
                                        if(albaran_lines[index_line]['status'] == 0):
                                            if (self.exists_product_in(a1, productId, 'product_code', 'product_tmpl_id', albaran_lines[index_line]['ean']) or \
                                                self.exists_product_in(a2, productId, 'x_studio_ean13', 'product_variant_ids', albaran_lines[index_line]['ean'])):
                                                linAlbObj = albaran_lines[index_line]
                                                ap.append(linAlbObj)
                                                if (self.saveAlbaranDetailData(picking_ids, order_line_id, productId, arrayMoveId, productUomId, locationId, locationDestId, linAlbObj['cenvfac'], linAlbObj['lote'], self.getDateTime(linAlbObj['feccon']))):
                                                    albaran_lines['status'] = True
                                                else:
                                                    raise Exception("ERROR")
                                                    #return False
                        _contenido = {
                            'status_code':200, 
                            'message':'success'
                        }
                        return _contenido

        except Exception as e:
            self.save_odoo_log('x_orders_desav', '', 'Error general', str(e), self.STATUS_ERROR)
            _logger.info(str(e))
            _contenido = {
                'status_code':500,
                'message':'Error de tipo ' + str(e)
            }

    def get_Product_ids(self, order_lines_search):
        products_id = []
        for line in order_lines_search:
            product_id = line['product_id'][0]
            products_id.append(product_id)
        return products_id

    def get_moves_ids(self, order_lines_search):
        moves_id = []
        for line in order_lines_search:
            move_id = line['move_ids']
            moves_id.append(move_id)
        return moves_id

    def exists_product_in(self, arrayItems, productId, field, field_index, value):
        exists = False
        for item in range(len(arrayItems)):
            id = arrayItems[item][field_index][0]
            if(arrayItems[item][field] == value and id == productId):
                exists = True
                break
        return exists

    def getDateTime(self, date):
        if(date):
            yyyy = int(date[0: 4])
            mm = int(date[4: 6])
            dd = int(date[6: 8])
            _datetime = datetime.date(yyyy, mm, dd)
            return _datetime
        else:
            return ""

    def saveAlbaranData(self, picking_id, carrier, date):
        try:
            stock_picking = request.env['stock.picking'].search([('id','=',picking_id)])
            stock_picking.write({
                'carrier_tracking_ref': carrier,
                'date_done': date
            })
            if (stock_picking):
                return True
            else:
                self.save_odoo_log('x_orders_desav', None, picking_id, 'Problema al guardar el albaran ' + carrier, self.STATUS_ERROR);
                _logger.info(picking_id)
            return False

        except Exception as e:
            self.save_odoo_log('x_orders_desav', None, 'Error al guardar', str(e), self.STATUS_ERROR)
            _logger.info(str(e))
            return False

    def save_odoo_log(self, model_name, id_log, name, description, status):
        result = False
        try:
            if(id_log):
                _log = request.env[''+ model_name + ''].search([('id','=',id_log)], limit=1)
                _log.write({
                    'x_name': name,
                    'x_studio_fecha_ltimo_intento': datetime.datetime.now(),
                    'x_studio_descripcin_estado': description,
                    'x_studio_estado': status
                })
                result = True
            else:
                _log = request.env[''+ model_name + ''].create({
                    'x_name': name,
                    'x_studio_fecha_ltimo_intento': datetime.datetime.now(),
                    'x_studio_descripcin_estado': description,
                    'x_studio_estado': status
                })
                result = True

        except Exception as e:
            _logger.info(str(e))
		
        return result

    def saveAlbaranDetailData(self, pickingIds, orderLineId, productId, arrayMoveId, productUomId, locationId, locationDestId, cenvfac, lotName, lifeDate):
        try:
            stock_move_search = request.env['stock.move'].search_read(['&',('id','in',arrayMoveId),('picking_id','in',pickingIds)], ['id', 'move_line_ids', 'picking_id'])

            for stock_move in stock_move_search:
                stockMoveId = stock_move['id']
                moveLineIds = stock_move['move_line_ids']
                idStockPicking = stock_move['picking_id'][0]
                self.registerStockMoveLinkLot(idStockPicking, orderLineId, productId, stockMoveId, moveLineIds, productUomId, locationId, locationDestId, cenvfac, lotName, lifeDate)
            return True

        except Exception as e:
            _logger.info(str(e))
            self.save_odoo_log('x_orders_desav', None, 'Error al guardar', str(e), self.STATUS_ERROR);
            return False


    def registerStockMoveLinkLot(self, idStockPicking, orderLineId, productId, stockMoveId, moveLineIds, productUomId, locationId, locationDestId, cenvfac, lotName, lifeDate):
        try:
            lot_search = request.env['stock.production.lot'].search(['&','&',('name','=',lotName),('product_id','=',productId),('company_id','=',1)])
			
            if(lot_search is None or lot_search.id == False):
                lot_id = request.env['stock.production.lot'].create({
                    'name': lotName,
                    'life_date': lifeDate,
                    'product_id': productId,
                    'company_id': 1
                })
            else:
               lot_id = lot_search.id

            move_id_create = request.env['stock.move.line'].create({
                'lot_id': lot_id,
                'qty_done': float(cenvfac),
                'picking_id': idStockPicking,
                'move_id': orderLineId,
                'product_id': productId,
                'company_id': 1,
                'product_uom_id': productUomId,
                'location_id': locationId,
                'location_dest_id': locationDestId
            })

            moveLineIds.append(move_id_create)
            stock_move_update = request.env['stock.move'].search([('id','=',stockMoveId)])
            stock_move_update.write({
                'move_line_ids': moveLineIds,
                'state': 'confirmed'
            })

            if(lot_id and move_id_create and stock_move_update):
                return True
            else:
                if(lot_id is None or lot_id.id == False):
                    _logger.info('Problema al guardar la linea del albaran ' + lotName)
                    self.save_odoo_log('x_orders_desav', None, 'lote', 'Problema al guardar la linea del albaran ' + lotName, self.STATUS_ERROR)
                elif(move_id_create is None or move_id_create.id == False):
                    _logger.info('Problema al guardar el move ' + move_id_create)
                    self.save_odoo_log('x_orders_desav', None, 'move_id', 'Problema al guardar el move ' + move_id_create, self.STATUS_ERROR)
                elif(stock_move_update is None or stock_move_update.id == False):
                    _logger.info('Problema al guardar el move ' + stock_move_update)
                    self.save_odoo_log('x_orders_desav', None, 'move.line', 'Problema al guardar la linea del albaran ' + stock_move_update, self.STATUS_ERROR)
                return False

        except Exception as e:
            _logger.info(str(e))
            self.save_odoo_log('x_orders_desav', None, 'Error al guardar', str(e), self.STATUS_ERROR);
            return False