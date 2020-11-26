# -*- coding: utf-8 -*-

import logging
import math
from math import log10
from collections import defaultdict, namedtuple
from odoo import api, fields, models, exceptions, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.date_utils import add, subtract
from odoo.tools.float_utils import float_round
import datetime
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)

class mrp_production_schedule_custom_0(models.Model):
    
    _inherit = 'mrp.production.schedule'


    def get_production_schedule_view_state(self):
        company_id = self.env.company
        date_range = company_id._get_date_range()

        schedules_to_compute = self.env['mrp.production.schedule'].browse(self.get_impacted_schedule()) | self

        indirect_demand_trees = schedules_to_compute._get_indirect_demand_tree()
        
        indirect_demand_order = schedules_to_compute._get_indirect_demand_order(indirect_demand_trees)
        indirect_demand_qty = defaultdict(float)
        incoming_qty, incoming_qty_done = self._get_incoming_qty(date_range)
        outgoing_qty, outgoing_qty_done = self._get_outgoing_qty(date_range)
        read_fields = [
            'forecast_target_qty',
            'min_to_replenish_qty',
            'max_to_replenish_qty',
            'product_id',
        ]
        if self.env.user.has_group('stock.group_stock_multi_warehouses'):
            read_fields.append('warehouse_id')
        if self.env.user.has_group('uom.group_uom'):
            read_fields.append('product_uom_id')
        production_schedule_states = schedules_to_compute.read(read_fields)
        production_schedule_states_by_id = {mps['id']: mps for mps in production_schedule_states}
        for production_schedule in indirect_demand_order:
            # Bypass if the schedule is only used in order to compute indirect
            # demand.

            ########################################
            data = self.moq_of_product(production_schedule.product_tmpl_id)
            quantity_week = data['quantity_week']
            moq = data['moq']
            unidad_redondeo = data['unidad_redondeo']
            ########################################

            rounding = production_schedule.product_id.uom_id.rounding
            lead_time = production_schedule._get_lead_times()
            production_schedule_state = production_schedule_states_by_id[production_schedule['id']]
            if production_schedule in self:
                procurement_date = add(fields.Date.today(), days=lead_time)
                precision_digits = max(0, int(-(log10(production_schedule.product_uom_id.rounding))))
                production_schedule_state['precision_digits'] = precision_digits
                production_schedule_state['forecast_ids'] = []
            indirect_demand_ratio = production_schedule._get_indirect_demand_ratio(indirect_demand_trees, schedules_to_compute)

            starting_inventory_qty = production_schedule.product_id.with_context(warehouse=production_schedule.warehouse_id.id).qty_available
            if len(date_range):
                starting_inventory_qty -= incoming_qty_done.get((date_range[0], production_schedule.product_id, production_schedule.warehouse_id), 0.0)
                starting_inventory_qty += outgoing_qty_done.get((date_range[0], production_schedule.product_id, production_schedule.warehouse_id), 0.0)

            pos = 0
            for date_start, date_stop in date_range:
                forecast_values = {}
                key = ((date_start, date_stop), production_schedule.product_id, production_schedule.warehouse_id)
                existing_forecasts = production_schedule.forecast_ids.filtered(lambda p: p.date >= date_start and p.date <= date_stop)
                if production_schedule in self:
                    forecast_values['date_start'] = date_start
                    forecast_values['date_stop'] = date_stop
                    forecast_values['incoming_qty'] = float_round(incoming_qty.get(key, 0.0) + incoming_qty_done.get(key, 0.0), precision_rounding=rounding)
                    forecast_values['outgoing_qty'] = float_round(outgoing_qty.get(key, 0.0) + outgoing_qty_done.get(key, 0.0), precision_rounding=rounding)

                forecast_values['indirect_demand_qty'] = float_round(indirect_demand_qty.get(key, 0.0), precision_rounding=rounding)
                replenish_qty_updated = False
                if existing_forecasts:
                    forecast_values['forecast_qty'] = float_round(sum(existing_forecasts.mapped('forecast_qty')), precision_rounding=rounding)
                    forecast_values['replenish_qty'] = float_round(sum(existing_forecasts.mapped('replenish_qty')), precision_rounding=rounding)

                    # Check if the to replenish quantity has been manually set or
                    # if it needs to be computed.
                    replenish_qty_updated = any(existing_forecasts.mapped('replenish_qty_updated'))
                    forecast_values['replenish_qty_updated'] = replenish_qty_updated
                else:
                    forecast_values['forecast_qty'] = 0.0

                # if not replenish_qty_updated:
                #     replenish_qty = production_schedule._get_replenish_qty(starting_inventory_qty - forecast_values['forecast_qty'] - forecast_values['indirect_demand_qty'])
                #     forecast_values['replenish_qty'] = float_round(replenish_qty, precision_rounding=rounding)
                #     forecast_values['replenish_qty_updated'] = False

                ########################################
                if replenish_qty_updated:
                    if(pos >= quantity_week and forecast_values['replenish_qty'] > 0 and forecast_values['replenish_qty'] < moq):
                        forecast_values['replenish_qty'] = moq
                else:
                    if(pos < quantity_week and forecast_values.get('replenish_qty',0) == 0):
                        forecast_values['replenish_qty'] = 0
                    else:
                        replenish_qty = production_schedule._get_replenish_qty(starting_inventory_qty - forecast_values['forecast_qty'] - forecast_values['indirect_demand_qty'])
                        if unidad_redondeo > 0 and (replenish_qty % unidad_redondeo) > 0:
                            resto = unidad_redondeo - (replenish_qty % unidad_redondeo)
                            replenish_qty = replenish_qty + resto
                        
                        replenish_qty = float_round(replenish_qty, precision_rounding=rounding)
                        if(replenish_qty > 0 and replenish_qty < moq):
                            forecast_values['replenish_qty'] = moq
                        else:
                            forecast_values['replenish_qty'] = float_round(replenish_qty, precision_rounding=rounding)
                        forecast_values['replenish_qty_updated'] = False

                pos = pos + 1
                ########################################

                forecast_values['starting_inventory_qty'] = float_round(starting_inventory_qty, precision_rounding=rounding)
                forecast_values['safety_stock_qty'] = float_round(starting_inventory_qty - forecast_values['forecast_qty'] - forecast_values['indirect_demand_qty'] + forecast_values['replenish_qty'], precision_rounding=rounding)

                if production_schedule in self:
                    production_schedule_state['forecast_ids'].append(forecast_values)
                starting_inventory_qty = forecast_values['safety_stock_qty']
                # Set the indirect demand qty for children schedules.
                for (mps, ratio) in indirect_demand_ratio:
                    if not forecast_values['replenish_qty']:
                        continue
                    related_date = max(subtract(date_start, days=lead_time), fields.Date.today())
                    index = next(i for i, (dstart, dstop) in enumerate(date_range) if related_date <= dstart or (related_date >= dstart and related_date <= dstop))
                    related_key = (date_range[index], mps.product_id, mps.warehouse_id)
                    indirect_demand_qty[related_key] += ratio * forecast_values['replenish_qty']

            if production_schedule in self:
                # The state is computed after all because it needs the final
                # quantity to replenish.
                forecasts_state = production_schedule._get_forecasts_state(production_schedule_states_by_id, date_range, procurement_date)
                forecasts_state = forecasts_state[production_schedule.id]
                for index, forecast_state in enumerate(forecasts_state):

                    ########################################
                    if(index < quantity_week):
                        forecast_state['state'] = 'to_custom'
                    ########################################

                    production_schedule_state['forecast_ids'][index].update(forecast_state)

                # The purpose is to hide indirect demand row if the schedule do not
                # depends from another.
                has_indirect_demand = any(forecast['indirect_demand_qty'] != 0 for forecast in production_schedule_state['forecast_ids'])
                production_schedule_state['has_indirect_demand'] = has_indirect_demand
        return [p for p in production_schedule_states if p['id'] in self.ids]


    def set_replenish_qty(self, date_index, quantity):
        """ Save the replenish quantity and mark the cells as manually updated.

        params quantity: The new quantity to replenish
        params date_index: The manufacturing period
        """
        # Get the last date of current period
        self.ensure_one()
        date_start, date_stop = self.company_id._get_date_range()[date_index]
        existing_forecast = self.forecast_ids.filtered(lambda f:
            f.date >= date_start and f.date <= date_stop)

        ######################################
        if(existing_forecast):
            data = self.moq_of_product(existing_forecast.production_schedule_id.product_tmpl_id)
            if(date_index >= data['quantity_week'] and quantity > 0 and quantity < data['moq']):
                quantity = data['moq']
        ######################################

        quantity = float_round(float(quantity), precision_rounding=self.product_uom_id.rounding)
        quantity_to_add = quantity - sum(existing_forecast.mapped('replenish_qty'))
        if existing_forecast:
            new_qty = existing_forecast[0].replenish_qty + quantity_to_add
            new_qty = float_round(new_qty, precision_rounding=self.product_uom_id.rounding)
            existing_forecast[0].write({
                'replenish_qty': new_qty,
                'replenish_qty_updated': True
            })
        else:
            existing_forecast.create({
                'forecast_qty': 0,
                'date': date_stop,
                'replenish_qty': quantity,
                'replenish_qty_updated': True,
                'production_schedule_id': self.id
            })
        return True

    def _get_indirect_demand_ratio(self, indirect_demand_trees, other_mps):
        """ return the schedules in arg 'other_mps' directly linked to
        schedule self and the quantity nescessary in order to produce 1 unit of
        the product defined on the given schedule.
        """
        self.ensure_one()
        other_mps = other_mps.filtered(lambda s: s.warehouse_id == self.warehouse_id)
        related_mps = []

        def _first_matching_mps(node, ratio, related_mps):
            if node.product == self.product_id:
                ratio = 1.0
            elif ratio and node.product in other_mps.mapped('product_id'):
                related_mps.append((other_mps.filtered(lambda s: s.product_id == node.product), ratio))
                return related_mps
            for child in node.children:
                related_mps = _first_matching_mps(child, ratio * child.ratio, related_mps)
                if not ratio and related_mps:
                    return related_mps
            return related_mps

        for tree in indirect_demand_trees:
            if not related_mps:
                related_mps = _first_matching_mps(tree, False, [])
        return related_mps



    def moq_of_product(self, product_tmpl_id):
        toReturn = { "route": "", "quantity_week": 0, "moq": 0, "unidad_redondeo": 0 }
        if(product_tmpl_id):
            if(product_tmpl_id.route_ids):
                for route in product_tmpl_id.route_ids:
                    if(route.name == "Comprar"):
                        toReturn['route'] = "Comprar"
                        if(product_tmpl_id.seller_ids):
                            time_days = product_tmpl_id.seller_ids[0].x_studio_transit_time + product_tmpl_id.seller_ids[0].delay
                            toReturn['quantity_week'] = math.ceil(time_days/7)

                            peso_umb_gr = (product_tmpl_id.x_studio_unidades_caja_ud + product_tmpl_id.x_studio_n_bolsas) * product_tmpl_id.x_studio_peso_neto_unitario_gr
                            moq = (product_tmpl_id.seller_ids[0].x_studio_moq_kg * 1000) / (peso_umb_gr if peso_umb_gr > 0 else 1)
                            unidad_redondeo = (product_tmpl_id.seller_ids[0].x_studio_unidad_de_redondeo_kg * 1000) / (peso_umb_gr if peso_umb_gr > 0 else 1)

                            if unidad_redondeo > 0 and (moq % unidad_redondeo) > 0:
                                resto = unidad_redondeo - (moq % unidad_redondeo)
                                moq = moq + resto
                            
                            toReturn['moq'] = moq
                            toReturn['unidad_redondeo'] = unidad_redondeo
                            break

                    if(route.name == "Fabricar"):
                        toReturn['route'] = "Fabricar"
                        if(product_tmpl_id.bom_ids):
                            time_days = product_tmpl_id.bom_ids[-1].x_studio_lead_time
                            toReturn['quantity_week'] = math.ceil(time_days/7)

                            peso_umb_gr = (product_tmpl_id.x_studio_unidades_caja_ud + product_tmpl_id.x_studio_n_bolsas) * product_tmpl_id.x_studio_peso_neto_unitario_gr
                            moq = product_tmpl_id.bom_ids[-1].x_studio_moq_kg * 1000 / (peso_umb_gr if peso_umb_gr > 0 else 1)
                            unidad_redondeo = (product_tmpl_id.bom_ids[-1].x_studio_unidad_de_redondeo_kg * 1000) / (peso_umb_gr if peso_umb_gr > 0 else 1)
                            
                            if unidad_redondeo > 0 and (moq % unidad_redondeo) > 0:
                                resto = unidad_redondeo - (moq % unidad_redondeo)
                                moq = moq + resto

                            toReturn['moq'] = moq
                            toReturn['unidad_redondeo'] = unidad_redondeo
                            break

        return toReturn

    @api.model
    def create(self, vals):
        result = super(mrp_production_schedule_custom_0, self).create(vals)
        company_id = self.env.company
        date_range = company_id._get_date_range()
        forecast_month = []

        data = []
        for date_start, date_stop in date_range:
            if(date_start.month not in forecast_month):
                start_month = datetime.datetime(date_start.year, date_start.month, 1)
                end_month = start_month + relativedelta(months=1)
                forecast = self.env['x.forecast.sale'].search([
                    ('x_producto','=',result.product_id.id),
                    ('x_mes','>=',start_month),
                    ('x_mes','<',end_month),
                    ('x_locked','=',True)
                    ])
                forecast_unit = 0
                for fore in forecast:
                    forecast_unit += fore.x_cajas
                data.append({
                    'start_month':start_month,
                    'end_month':end_month,
                    'forecast':forecast_unit,
                    'qty_week': 1
                })
                forecast_month.append(date_start.month)
            else:
                for i in data:
                    if(i['start_month'].month == date_start.month):
                        i['qty_week'] = i['qty_week'] + 1

        for date_start, date_stop in date_range:
            existing_forecast = self.forecast_ids.filtered(lambda f:f.date >= date_start and f.date <= date_stop)
            
            quantity = 0
            for i in data:
                if(i['start_month'].month == date_start.month):
                    quantity = i['forecast'] / i['qty_week']
                    quantity = float_round(float(quantity), precision_rounding=result.product_uom_id.rounding)
            
            existing_forecast.create({
                'forecast_qty': quantity,
                'date': date_stop,
                'replenish_qty': 0,
                'production_schedule_id': result.id
            })

        return result