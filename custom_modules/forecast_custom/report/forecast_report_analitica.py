# -*- coding: utf-8 -*-

from odoo import tools
from odoo import models, fields, api

from functools import lru_cache


class ForecastReportAnalitica(models.Model):
    _name = "x.forecast.report.analytic"
    _description = "Forecast Statistics Analitic"
    _auto = False
    _rec_name = 'x_date'
    _order = 'x_date desc'

    x_rotacion = fields.Float(string='Rotación', readonly=True)
    x_kg = fields.Float(string="Kg", readonly=True)
    x_cajas = fields.Integer(string="Cajas", readonly=True)
    x_unidades = fields.Integer(string="Unidades", readonly=True) #unidades reales vendidas
    x_forecast = fields.Float(string='Forecast', readonly=True) #unidades puestas a mano
    x_desviacion = fields.Float(string='Desviación', readonly=True)

    x_date = fields.Date(string="Mes", readonly=True)
    x_producto = fields.Many2one('product.product', string='Producto', readonly=True)
    x_cuenta_analitica = fields.Many2one('account.analytic.account', string='Cuenta Analítica', readonly=True)

    @api.model
    def _select(self):
        return '''
            SELECT min(sale.id) AS id,

            sum(sale_line.product_uom_qty) * MIN(product_template.x_studio_unidades_por_caja) / 
            ((SELECT DATE_PART('days', DATE_TRUNC('month',min(sale.date_order)) + '1 MONTH'::INTERVAL - '1 DAY'::INTERVAL )) -
            (SELECT COUNT(*) FROM generate_series(DATE_TRUNC('month',MIN(sale.date_order)), (SELECT (date_trunc('month', MIN(sale.date_order)) + interval '1 month' - interval '1 day')::date), '1 day') AS g(mydate) WHERE EXTRACT(DOW FROM mydate) = 0)) AS x_rotacion,

            sum(sale_line.product_uom_qty) * MIN((product_template.x_studio_unidades_caja_ud + product_template.x_studio_n_bolsas) * product_template.x_studio_peso_neto_unitario_gr) / 1000 AS x_kg,
            sum(sale_line.product_uom_qty) AS x_cajas,
            sum(sale_line.product_uom_qty) * MIN(product_template.x_studio_unidades_por_caja) AS x_unidades,
            
            (Select x_unidades From x_forecast_sale Where x_cuenta_analitica=sale.analytic_account_id and x_producto=sale_line.product_id and DATE_TRUNC('month',x_mes) = DATE_TRUNC('month',min(sale.date_order)) limit 1) AS x_forecast,
            (Select x_unidades From x_forecast_sale Where x_cuenta_analitica=sale.analytic_account_id and x_producto=sale_line.product_id and DATE_TRUNC('month',x_mes) = DATE_TRUNC('month',min(sale.date_order)) limit 1) / NULLIF(sum(sale_line.product_uom_qty),0) AS x_desviacion,
            DATE_TRUNC('month',sale.date_order) AS x_date,
            sale_line.product_id AS x_producto,
            sale.analytic_account_id AS x_cuenta_analitica
        '''

    @api.model
    def _from(self):
        return '''
            FROM sale_order sale INNER JOIN sale_order_line sale_line ON sale.id = sale_line.order_id
		     INNER JOIN product_product product on sale_line.product_id = product.id
		     INNER JOIN product_template on product.product_tmpl_id = product_template.id
		     INNER JOIN account_analytic_account analytic_account on sale.analytic_account_id = analytic_account.id
        '''

    @api.model
    def _where(self):
        return '''
        WHERE sale.state = 'sale' and sale_line.product_id in (SELECT DISTINCT x_producto FROM x_forecast_catalog) 
        and sale.analytic_account_id in (SELECT DISTINCT x_cuenta_analitica FROM x_forecast_catalog)
        '''

    @api.model
    def _group_by(self):
        return '''
            GROUP BY DATE_TRUNC('month',sale.date_order), sale_line.product_id, sale.analytic_account_id
        '''

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute('''
            CREATE OR REPLACE VIEW %s AS (
                %s %s %s %s
            )
        ''' % (
            self._table, self._select(), self._from(), self._where(), self._group_by()
        ))
