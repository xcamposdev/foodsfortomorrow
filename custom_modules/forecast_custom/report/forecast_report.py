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
    x_unidades = fields.Integer(string="Unidades", readonly=True)
    x_kg = fields.Float(string="Kg", readonly=True)
    x_cajas = fields.Integer(string="Cajas", readonly=True)
    
    x_date = fields.Date(string="Forecast Fecha", readonly=True)
    x_producto = fields.Many2one('product.product', string='Product', readonly=True)
    x_client = fields.Many2one('res.partner', string='Partner', readonly=True)
    x_real_previsto = fields.Float(string='Real', readonly=True)
    x_desviacion = fields.Float(string='Desviación', readonly=True)

    @api.model
    def _select(self):
        return '''
            SELECT
                sale.id,
                sale.x_rotacion AS x_rotacion, 
                sale.x_unidades AS x_unidades, 
                sale.x_kg AS x_kg, 
                sale.x_cajas AS x_cajas,
	            sale.x_mes AS x_date, 
                sale.x_producto AS x_producto, 
                sale.x_contacto AS x_client, 
                sale.x_unidades AS x_real_previsto,
	            0 AS x_desviacion
        '''

    @api.model
    def _from(self):
        return '''
            FROM x_forecast_catalog catalog 
                INNER JOIN x_forecast_sale sale ON catalog.Id = x_forecast_catalog_id
        '''

    @api.model
    def _where(self):
        return '''
        '''

    @api.model
    def _group_by(self):
        return '''
            GROUP BY 
                sale.id,
                sale.x_rotacion, 
                sale.x_unidades, 
                sale.x_kg, 
                sale.x_cajas,
	            sale.x_mes, 
                sale.x_producto, 
                sale.x_contacto
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
