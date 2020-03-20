# -*- coding: utf-8 -*-
from odoo import http

# class AccountInvoicingCustom(http.Controller):
#     @http.route('/account_invoicing_custom/account_invoicing_custom/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/account_invoicing_custom/account_invoicing_custom/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('account_invoicing_custom.listing', {
#             'root': '/account_invoicing_custom/account_invoicing_custom',
#             'objects': http.request.env['account_invoicing_custom.account_invoicing_custom'].search([]),
#         })

#     @http.route('/account_invoicing_custom/account_invoicing_custom/objects/<model("account_invoicing_custom.account_invoicing_custom"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('account_invoicing_custom.object', {
#             'object': obj
#         })