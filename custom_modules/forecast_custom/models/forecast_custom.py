# -*- coding: utf-8 -*-

import logging
import time
import calendar
from datetime import date
from odoo import api, fields, models, exceptions, _
from odoo.exceptions import AccessError, UserError, ValidationError

_logger = logging.getLogger(__name__)

class forecast_custom_0(models.Model):
    
    _name = "x_forecast_ventas"


class forecast_generado_custom_0(models.Model):
    
    _name = "x.forecast.ventas.generado"

    x_date = fields.Date("Fecha")
    x_producto = fields.Many2one("product.product", "Producto")
    x_comercial = fields.Many2one("res.users", "Comercial")
    x_contacto = fields.Many2one("res.partner", "Contacto")
    x_cuenta_analitica = fields.Many2one("account.analytic.account", "Cuenta Analítica")
    x_studio_tipo = fields.Selection(selection=[
            ('cliente', 'Cliente'),
            ('canal', 'Canal'),
        ], string='Tipo')




class forecast_wizard_custom_0(models.TransientModel):
    
    _name = 'x.forecast.ventas.wizard'

    date = fields.Date('Mes', default=date.today())

    def generate_forecast(self):
        self.ensure_one()
        startMonth = self.env.context.get('date', time.strftime('%Y-%m-01'))
        lastDay = calendar.monthrange(self.date.year, self.date.month)[1]
        endMonth = self.env.context.get('date', time.strftime('%Y-%m-' + str(lastDay)))
        exists = self.env['x.forecast.ventas.generado'].search(['&','&',('x_comercial','=',self.env.user.id),('x_date','>=',startMonth),('x_date','<=',endMonth)], limit=1)
        if(exists):
            raise ValidationError("Ya existe registros generados para el mes: %s" % (startMonth))

        allproducts = self.env['product.product'].search([('id','>','0')])
        allcontact = self.env['res.partner'].search([('id','>','0'),('parent_id','=',False)])
        for product in allproducts:
            for contact in allcontact:
                self.env['x.forecast.ventas.generado'].create({
                    'x_date': self.date.today(),
                    'x_producto': product.id,
                    'x_comercial': self.env.user.id,
                    'x_contacto': contact.id,
                    'x_cuenta_analitica': False,
                    'x_studio_tipo': 'cliente'
                })
        
        return {
            'name': "Generado",
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'x.forecast.ventas.generado',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'current',
            'nodestroy': True
        }

         

        # context = dict(self.env.context or {})

        # def ref(module, xml_id):
        #     proxy = self.env['ir.model.data']
        #     return proxy.get_object_reference(module, xml_id)

        # model, search_view_id = ref('product', 'product_search_form_view')
        # model, graph_view_id = ref('product_margin', 'view_product_margin_graph')
        # model, form_view_id = ref('product_margin', 'view_product_margin_form')
        # model, tree_view_id = ref('product_margin', 'view_product_margin_tree')

        # context.update(invoice_state=self.invoice_state)

        # if self.from_date:
        #     context.update(date_from=self.from_date)

        # if self.to_date:
        #     context.update(date_to=self.to_date)

        # views = [
        #     (tree_view_id, 'tree'),
        #     (form_view_id, 'form'),
        #     (graph_view_id, 'graph')
        # ]
        # return {
        #     'name': _('Product Margins'),
        #     'context': context,
        #     "view_mode": 'tree,form,graph',
        #     'res_model': 'product.product',
        #     'type': 'ir.actions.act_window',
        #     'views': views,
        #     'view_id': False,
        #     'search_view_id': search_view_id,
        # }
