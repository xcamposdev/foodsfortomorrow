# -*- coding: utf-8 -*-
from odoo import http

# class WebLayoutCustom(http.Controller):
#     @http.route('/web_layout_custom/web_layout_custom/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/web_layout_custom/web_layout_custom/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('web_layout_custom.listing', {
#             'root': '/web_layout_custom/web_layout_custom',
#             'objects': http.request.env['web_layout_custom.web_layout_custom'].search([]),
#         })

#     @http.route('/web_layout_custom/web_layout_custom/objects/<model("web_layout_custom.web_layout_custom"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('web_layout_custom.object', {
#             'object': obj
#         })