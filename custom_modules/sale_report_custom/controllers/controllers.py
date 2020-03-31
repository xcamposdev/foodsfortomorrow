# -*- coding: utf-8 -*-
from odoo import http

# class SaleReportCustom(http.Controller):
#     @http.route('/sale_report_custom/sale_report_custom/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/sale_report_custom/sale_report_custom/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('sale_report_custom.listing', {
#             'root': '/sale_report_custom/sale_report_custom',
#             'objects': http.request.env['sale_report_custom.sale_report_custom'].search([]),
#         })

#     @http.route('/sale_report_custom/sale_report_custom/objects/<model("sale_report_custom.sale_report_custom"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('sale_report_custom.object', {
#             'object': obj
#         })