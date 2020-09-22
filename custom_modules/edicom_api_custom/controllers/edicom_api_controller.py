# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import json
import datetime
import copy 

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class EdicomAPIController(http.Controller):

    STATUS_PROCCESS = 'status1'
    STATUS_SENT = 'status2'
    STATUS_CANCELLED = 'status3'
    STATUS_ERROR = 'Error'
    INTENTS = 0

    @http.route('/edicom/input_desadv', auth='user', type='json', methods=['POST'], csrf=False)
    def edicom_api_order_desav(self):
        try:
            body_data = json.loads(request.httprequest.data)
            albaran_edicom = body_data['albaran']
            albaran_lines = body_data['albaran_detail']
            albaran_lines_verify = copy.deepcopy(albaran_lines)  
            
            _logger.info("Albaran y Detalle")
            _logger.info(albaran_edicom)
            _logger.info(albaran_lines)

            #request.session.authenticate('Andres_Test', 'acastillo@develoop.net', 'Temp1243')
            ##session_info =  request.env['ir.http'].session_info()
            self.create_move_for_new_item(albaran_edicom, albaran_lines_verify)
            
            return self.process_albaran(albaran_edicom, albaran_lines)
        
        except Exception as e:
            self.save_odoo_log('x_orders_desav', None, 'Error general', str(e), self.STATUS_ERROR)
            _logger.info(str(e))
            return { 'status_code':500, 'message':'Error de tipo ' + str(e) }

    def create_move_for_new_item(self, albaran_edicom, albaran_lines_verify):
        try:
            _logger.info("create_move_for_new_item")
            purchase = request.env['purchase.order'].search([('name','=', albaran_edicom['numcontrato'])], limit=1)
            if(purchase):
                a1 = request.env['product.supplierinfo'].search_read([('product_tmpl_id','in',purchase.order_line.product_id.ids)], ['id','product_code','product_tmpl_id'])
                a2 = request.env['product.template'].search_read([('product_variant_ids','in',purchase.order_line.product_id.ids)], ['id','x_studio_ean13','product_variant_ids'])

                _logger.info("Antes del for")
                for purchase_line in purchase.order_line:
                    for index in range(len(albaran_lines_verify)):
                        if (self.exists_product_in(a1, purchase_line.product_id.id, 'product_code', 'product_tmpl_id', albaran_lines_verify[index]['ean']) or \
                            self.exists_product_in(a2, purchase_line.product_id.id, 'x_studio_ean13', 'product_variant_ids', albaran_lines_verify[index]['ean'])):
                            albaran_lines_verify[index]['status'] = 'exist'
                
                _logger.info("Despues del for")
                for albaran_lines in albaran_lines_verify:
                    if(albaran_lines['status'] != 'exist'):
                        _logger.info("PILLO ALGO INDEXISTEN")
                        product_search = request.env['product.template'].search([('x_studio_ean13','=',albaran_lines['ean'])], limit=1)
    
                        picking_id = purchase.picking_ids[0].id
                        stock_move_stock = request.env['stock.picking'].search([('id','=', picking_id)], limit=1)
    
                        if(product_search):
                            _logger.info(stock_move_stock)
                            id_create = request.env['stock.move'].create({
                                'picking_id': stock_move_stock.id,
                                'name': product_search.name,
                                'product_uom_qty': 0,
                                'product_id': product_search.id,
                                'product_uom': product_search.uom_id.id,
                                'location_id': stock_move_stock.location_id[0].id,
                                'location_dest_id': stock_move_stock.location_dest_id[0].id
                            })
                            
                        else:
                            _logger.info("PRODUCTO NO EXISTENTE CON EAN: " + str(albaran_lines['ean']))
            test = ""
        except Exception as e:
            _logger.info(str(e))
        
    def process_albaran(self, albaran_edicom, albaran_lines):
        all_process_successfully = True
        
        purchase = request.env['purchase.order'].search([('name','=', albaran_edicom['numcontrato'])], limit=1)
        if(purchase):
            order_lines = purchase.order_line
            picking_ids = purchase.picking_ids.ids
            _logger.info("order_lines y pickings")
            _logger.info(order_lines)
            _logger.info(picking_ids)
                
            if(order_lines and picking_ids):
                picking_id = purchase.picking_ids[0].id
                stock_move_stock = request.env['stock.picking'].search([('id','=', picking_id)], limit=1)
                if (stock_move_stock):
                    locationId = stock_move_stock.location_id[0].id
                    locationDestId = stock_move_stock.location_dest_id[0].id
                    _logger.info("locationId y locationDestId")
                    _logger.info(locationId)
                    _logger.info(locationDestId)
                        
                    if(self.saveAlbaranData(picking_id, albaran_edicom['numalb'], self.getDateTime(albaran_edicom['fecenvio']))):
                        _logger.info("Paso saveAlbaranData")
                            
                        products_ids = self.get_Product_ids(purchase.order_line)
                        moves_ids = self.get_moves_ids(purchase.order_line)
                        a1 = request.env['product.supplierinfo'].search_read([('product_tmpl_id','in',products_ids)], ['id','product_code','product_tmpl_id'])
                        a2 = request.env['product.template'].search_read([('product_variant_ids','in',products_ids)], ['id','x_studio_ean13','product_variant_ids'])
                        ap = [];
                        firtsOrderLineId = 0
                        _logger.info("products_ids, moves_ids, a1, a2, ap")
                        _logger.info(products_ids)
                        _logger.info(moves_ids)
                        _logger.info(a1)
                        _logger.info(a2)
                        _logger.info(ap)

                        for index in range(len(order_lines)):
                            order_line_id = order_lines[index]['id']
                            productId = products_ids[index] #?
                            arrayMoveId = moves_ids[index]  #?
                            productUomId = order_lines[index]['product_uom'][0].id
                            linAlbObj = None
                            indexLineObj = -1

                            if(index == 0):
                                firtsOrderLineId = order_line_id
                            
                            _logger.info("Dentro del primer FOR: order_line_id, productId, arrayMoveId, productUomId")
                            _logger.info(order_line_id)
                            _logger.info(productId)
                            _logger.info(arrayMoveId)
                            _logger.info(productUomId)
                                
                            for index_line in range(len(albaran_lines)):
                                if(albaran_lines[index_line]['status'] == 0):
                                    if (self.exists_product_in(a1, productId, 'product_code', 'product_tmpl_id', albaran_lines[index_line]['ean']) or \
                                        self.exists_product_in(a2, productId, 'x_studio_ean13', 'product_variant_ids', albaran_lines[index_line]['ean'])):
                                        _logger.info("exists_product_in paso con exito")
                                        linAlbObj = albaran_lines[index_line]
                                        ap.append(linAlbObj)
                                        if (self.saveAlbaranDetailData(picking_ids, order_line_id, productId, arrayMoveId, productUomId, locationId, locationDestId, linAlbObj['cenvfac'], linAlbObj['lote'], self.getDateTime(linAlbObj['feccon']))):
                                            albaran_lines[index_line]['status'] = True
                                            _logger.info("Se creo el registro")
                                        else:
                                            all_process_successfully = False
                                            _logger.info("ocurrio un error")
                        
                        test = "Test"
                        if(all_process_successfully == False and self.INTENTS < 3):
                            _logger.info("INTENTO NRO " + str(self.INTENTS))
                            INTENTS = INTENTS + 1
                            self.process_albaran(albaran_edicom, albaran_lines, self.INTENTS)
                
                        return { 'status_code':200, 'message':'success' }


        
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
            _logger.info(id_log)
            _logger.info(model_name)
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
            
            lot_id = 0
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
                'qty_done': float(cenvfac.replace(',', '.')),
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
                'move_line_ids': [(4, move_id_create.id)],
                'state': 'confirmed'
            })
            
            if(lot_id and move_id_create and stock_move_update):
                return True
            else:
                _logger.info(lot_id)
                _logger.info(move_id_create)
                _logger.info(stock_move_update)
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
        
    def get_Product_ids(self, order_lines):
        products_id = []
        for line in order_lines:
            products_id.append(line.product_id[0].id)
        return products_id

    def get_moves_ids(self, order_lines):
        moves_id = []
        for line in order_lines:
            moves_id.append(line.move_ids.ids)
        return moves_id