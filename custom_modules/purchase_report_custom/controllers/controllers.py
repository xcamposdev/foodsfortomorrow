# -*- coding: utf-8 -*-
from odoo import http

# class PurchaseReportCustom(http.Controller):
#     @http.route('/purchase_report_custom/purchase_report_custom/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/purchase_report_custom/purchase_report_custom/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('purchase_report_custom.listing', {
#             'root': '/purchase_report_custom/purchase_report_custom',
#             'objects': http.request.env['purchase_report_custom.purchase_report_custom'].search([]),
#         })

#     @http.route('/purchase_report_custom/purchase_report_custom/objects/<model("purchase_report_custom.purchase_report_custom"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('purchase_report_custom.object', {
#             'object': obj
#         })