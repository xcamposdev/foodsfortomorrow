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
            self.ID_LOG = 0
            self.INTENTS = 0
            #Creo el log de en processo
            body_data = json.loads(request.httprequest.data)
            albaran_edicom = body_data['albaran']
            albaran_lines = body_data['albaran_detail']
            albaran_lines_verify = copy.deepcopy(albaran_lines)  
            
            
            self.save_odoo_log(albaran_edicom['numcontrato'], 'En Proceso...', self.STATUS_PROCCESS)
            _logger.info("Albaran y Detalle")
            _logger.info(albaran_edicom)
            _logger.info(albaran_lines)

            #request.session.authenticate('Andres_Test', 'acastillo@develoop.net', 'Temp1243')
            ##session_info =  request.env['ir.http'].session_info()
            self.create_move_for_new_item(albaran_edicom, albaran_lines_verify)
            
            _logger.info("JALAAA")
            cr, uid, context, registry = request.cr, request.uid, request.context, request.registry
            _logger.info("ACTUALIZO EL CONTEXTO")
            
            return self.process_albaran(albaran_edicom, albaran_lines)
            #actualizar log de completado
        
        except Exception as e:
            #actualizar log de error
            self.save_odoo_log('', 'Error general ' + str(e), self.STATUS_ERROR)
            _logger.info(str(e))
            return { 'status_code':500, 'message':'Error de tipo ' + str(e) }

    def create_move_for_new_item(self, albaran_edicom, albaran_lines_verify):
        try:
            _logger.info("INICIO create_move_for_new_item")
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
                        _logger.info("se encontro move nuevo para agregar")
                        product_search = request.env['product.template'].search([('x_studio_ean13','=',albaran_lines['ean'])], limit=1)
    
                        stock_move_stock = request.env['stock.picking'].search(['&',('id','in', purchase.picking_ids.ids),('state','=','confirmed')], limit=1)[0]
    
                        if(product_search):
                            _logger.info(stock_move_stock)
                            id_create = request.env['stock.move'].create({
                                'picking_id': stock_move_stock.id,
                                'name': product_search.name,
                                'product_uom_qty': 0,
                                'product_id': product_search.id,
                                'product_uom': product_search.uom_id.id,
                                'location_id': stock_move_stock.location_id[0].id,
                                'location_dest_id': stock_move_stock.location_dest_id[0].id,
                                'state': 'confirmed'
                            })
                            _logger.info("SE CREATE: " + str(id_create))
                        else:
                            _logger.info("PRODUCTO NO EXISTENTE CON EAN: " + str(albaran_lines['ean']))
            test = ""
        except Exception as e:
            _logger.info(str(e))
            raise exceptions.UserError(str(e))
        
    def process_albaran(self, albaran_edicom, albaran_lines):
        all_process_successfully = True
        
        purchase = request.env['purchase.order'].search([('name','=', albaran_edicom['numcontrato'])], limit=1)
        if(purchase):
            order_lines = purchase.order_line
            picking_ids = request.env['stock.picking'].search(['&',('id','in', purchase.picking_ids.ids),('state','=','confirmed')], limit=1).ids
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
                        _logger.info("Paso get_Product_ids")
                        moves_ids = self.get_moves_ids(purchase.order_line)
                        _logger.info("Paso get_moves_ids")
                        a1 = request.env['product.supplierinfo'].search_read([('product_tmpl_id','in',products_ids)], ['id','product_code','product_tmpl_id'])
                        _logger.info("Paso a1")
                        a2 = request.env['product.template'].search_read([('product_variant_ids','in',products_ids)], ['id','x_studio_ean13','product_variant_ids'])
                        _logger.info("Paso a2")
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
                                        if (self.saveAlbaranDetailData(picking_ids, order_line_id, productId, arrayMoveId, productUomId, locationId, locationDestId, linAlbObj['cenvfac'], linAlbObj['lote'], self.getDateTime(linAlbObj['feccon']), linAlbObj['sscc1'])):
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
                        
                        self.save_odoo_log('', 'Completado exitosamente', self.STATUS_RECEIVED)
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
            return True

        except Exception as e:
            _logger.info(str(e))
            raise exceptions.UserError(str(e))

    def save_odoo_log(self, name, description, status):
        result = False
        try:
            if(self.ID_LOG > 0):
                _log = request.env['x_orders_desav'].search([('id','=',self.ID_LOG)], limit=1)
                _log.write({
                    #'x_name': name,
                    'x_studio_fecha_ltimo_intento': datetime.datetime.now(),
                    'x_studio_descripcin_estado': description,
                    'x_studio_estado': status
                })
                result = True
                _logger.info("Se modifico el log: " + str(self.ID_LOG))
            else:
                _log = request.env['x_orders_desav'].create({
                    'x_name': name,
                    'x_studio_fecha_ltimo_intento': datetime.datetime.now(),
                    'x_studio_descripcin_estado': description,
                    'x_studio_estado': status
                })
                self.ID_LOG = _log.id
                _logger.info("Se creo el log: " + str(self.ID_LOG))
                result = True
            
        except Exception as e:
            _logger.info(str(e))
		
        return result

    def saveAlbaranDetailData(self, pickingIds, orderLineId, productId, arrayMoveId, productUomId, locationId, locationDestId, cenvfac, lotName, lifeDate, sscc1):
        try:
            stock_move_search = request.env['stock.move'].search_read(['&',('id','in',arrayMoveId),('picking_id','in',pickingIds)], ['id', 'move_line_ids', 'picking_id'])

            for stock_move in stock_move_search:
                stockMoveId = stock_move['id']
                moveLineIds = stock_move['move_line_ids']
                idStockPicking = stock_move['picking_id'][0]
                self.registerStockMoveLinkLot(idStockPicking, orderLineId, productId, stockMoveId, moveLineIds, productUomId, locationId, locationDestId, cenvfac, lotName, lifeDate, sscc1)
            return True

        except Exception as e:
            _logger.info(str(e))
            raise exceptions.UserError(str(e))


    def registerStockMoveLinkLot(self, idStockPicking, orderLineId, productId, stockMoveId, moveLineIds, productUomId, locationId, locationDestId, cenvfac, lotName, lifeDate, sscc1):
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
                'location_dest_id': locationDestId,
                'x_studio_sscc_1': sscc1
            })

            _logger.info("STOCK MOVE LINE CREADO ES: " + str(move_id_create.id))
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
                elif(move_id_create is None or move_id_create.id == False):
                    _logger.info('Problema al guardar el move ' + move_id_create)
                elif(stock_move_update is None or stock_move_update.id == False):
                    _logger.info('Problema al guardar el move ' + stock_move_update)
                return False

        except Exception as e:
            _logger.info(str(e))
            raise exceptions.UserError(str(e))
        
    def get_Product_ids(self, order_lines):
        products_id = []
        for line in order_lines:
            if(line.display_type == False):
                products_id.append(line.product_id.id)
        return products_id

    def get_moves_ids(self, order_lines):
        moves_id = []
        for line in order_lines:
            moves_id.append(line.move_ids.ids)
        return moves_id