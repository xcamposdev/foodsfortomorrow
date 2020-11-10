# -*- coding: utf-8 -*-

from odoo import tools
from odoo import models, fields, api

from functools import lru_cache


class ForecastReport(models.Model):
    _name = "x.forecast.report"
    _description = "Forecast Statistics"
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
    x_client = fields.Many2one('res.partner', string='Cliente', readonly=True)

    @api.model
    def _select(self):
        return '''
            SELECT min(sale.id) AS id,

            (SELECT DATE_PART('days', DATE_TRUNC('month',min(sale.date_order)) + '1 MONTH'::INTERVAL - '1 DAY'::INTERVAL )) /
            (SELECT COUNT(*) FROM generate_series(DATE_TRUNC('month',MIN(sale.date_order)), (SELECT (date_trunc('month', MIN(sale.date_order)) + interval '1 month' - interval '1 day')::date), '1 day') AS g(mydate) WHERE EXTRACT(DOW FROM mydate) = 0) /
            (CASE WHEN MIN(contact.x_studio_puntos_de_venta_foods) > 0 THEN MIN(contact.x_studio_puntos_de_venta_foods) ELSE 1 END) AS x_rotacion,

            (CASE WHEN MIN(product_template.x_studio_unidades_por_caja) > 0 THEN 
            sum(sale_line.product_uom_qty) / MIN(product_template.x_studio_unidades_por_caja)
            ELSE sum(sale_line.product_uom_qty) END * MIN(product_template.x_studio_peso_umb_gr) / 1000) AS x_kg,

            CASE WHEN MIN(product_template.x_studio_unidades_por_caja) > 0 THEN 
            sum(sale_line.product_uom_qty) / MIN(product_template.x_studio_unidades_por_caja)
            ELSE sum(sale_line.product_uom_qty) END AS x_cajas,

            sum(sale_line.product_uom_qty) AS x_unidades,
            (Select x_unidades From x_forecast_sale Where x_contacto=sale.partner_invoice_id and x_producto=sale_line.product_id and DATE_TRUNC('month',x_mes) = DATE_TRUNC('month',min(sale.date_order)) limit 1) AS x_forecast,
            (Select x_unidades From x_forecast_sale Where x_contacto=sale.partner_invoice_id and x_producto=sale_line.product_id and DATE_TRUNC('month',x_mes) = DATE_TRUNC('month',min(sale.date_order)) limit 1) / NULLIF(sum(sale_line.product_uom_qty),0) AS x_desviacion,
            DATE_TRUNC('month',sale.date_order) AS x_date,
            sale_line.product_id AS x_producto,
            sale.partner_invoice_id AS x_client
        '''

    @api.model
    def _from(self):
        return '''
            FROM sale_order sale INNER JOIN sale_order_line sale_line ON sale.id = sale_line.order_id
		     INNER JOIN product_product product on sale_line.product_id = product.id
		     INNER JOIN product_template on product.product_tmpl_id = product_template.id
		     INNER JOIN res_partner contact on sale.partner_invoice_id = contact.id
        '''

    @api.model
    def _where(self):
        return '''
        WHERE sale.state = 'sale' and sale_line.product_id in (SELECT DISTINCT x_producto FROM x_forecast_catalog) 
        and sale.partner_invoice_id in (SELECT DISTINCT x_contacto FROM x_forecast_catalog)
        '''

    @api.model
    def _group_by(self):
        return '''
            GROUP BY DATE_TRUNC('month',sale.date_order), sale_line.product_id, sale.partner_invoice_id
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

    # @api.model
    # def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
    #     result = super(ForecastReport, self).read_group(
    #         domain, fields + ['ids:array_agg(id)'], groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    #     return result

    # _depends = {
    #     'account.move': [
    #         'name', 'state', 'type', 'partner_id', 'invoice_user_id', 'fiscal_position_id',
    #         'invoice_date', 'invoice_date_due', 'invoice_payment_term_id', 'invoice_partner_bank_id',
    #     ],
    #     'account.move.line': [
    #         'quantity', 'price_subtotal', 'amount_residual', 'balance', 'amount_currency',
    #         'move_id', 'product_id', 'product_uom_id', 'account_id', 'analytic_account_id',
    #         'journal_id', 'company_id', 'currency_id', 'partner_id',
    #     ],
    #     'product.product': ['product_tmpl_id'],
    #     'product.template': ['categ_id'],
    #     'uom.uom': ['category_id', 'factor', 'name', 'uom_type'],
    #     'res.currency.rate': ['currency_id', 'name'],
    #     'res.partner': ['country_id'],
    # }

    # @api.model
    # def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
    #     @lru_cache(maxsize=32)  # cache to prevent a SQL query for each data point
    #     def get_rate(currency_id):
    #         return self.env['res.currency']._get_conversion_rate(
    #             self.env['res.currency'].browse(currency_id),
    #             self.env.company.currency_id,
    #             self.env.company,
    #             self._fields['invoice_date'].today()
    #         )

    #     # First we get the structure of the results. The results won't be correct in multi-currency,
    #     # but we need this result structure.
    #     # By adding 'ids:array_agg(id)' to the fields, we will be able to map the results of the
    #     # second step in the structure of the first step.
    #     result_ref = super(ForecastReport, self).read_group(
    #         domain, fields + ['ids:array_agg(id)'], groupby, offset, limit, orderby, lazy
    #     )

    #     # In mono-currency, the results are correct, so we don't need the second step.
    #     if len(self.env.companies.mapped('currency_id')) <= 1:
    #         return result_ref
