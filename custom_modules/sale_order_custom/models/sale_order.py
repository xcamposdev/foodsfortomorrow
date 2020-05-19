# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, exceptions

class SaleOrderCustom0(models.Model):
    _name = 'sale.order'
    _inherit = 'sale.order'

    # partner_invoice_id = fields.Many2one('res.partner', string='Invoice Address', readonly=True, required=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, help="Invoice address for current sales order.")
    
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        """
        Update the following fields when the partner is changed:
        - Pricelist
        - Payment terms
        - Invoice address
        - Delivery address
        """
        if not self.partner_id:
            self.update({
                'partner_invoice_id': False,
                'partner_shipping_id': False,
                'fiscal_position_id': False,
            })
            return

        addr = self.partner_id.address_get(['delivery', 'invoice'])
        partner_user = self.partner_id.user_id or self.partner_id.commercial_partner_id.user_id
        values = {
            'pricelist_id': self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.id or False,
            'payment_term_id': self.partner_id.property_payment_term_id and self.partner_id.property_payment_term_id.id or False,
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
        }
        user_id = partner_user.id
        if not self.env.context.get('not_self_saleperson'):
            user_id = user_id or self.env.uid
        if self.user_id.id != user_id:
            values['user_id'] = user_id

        if self.env['ir.config_parameter'].sudo().get_param('account.use_invoice_terms') and self.env.company.invoice_terms:
            values['note'] = self.with_context(lang=self.partner_id.lang).env.company.invoice_terms
        values['team_id'] = self.env['crm.team']._get_default_team_id(domain=['|', ('company_id', '=', self.company_id.id), ('company_id', '=', False)],user_id=user_id)

        if self.partner_id and self.partner_id.parent_id:
            values['partner_invoice_id']=self.partner_id.parent_id.id
        self.update(values)
        # return {
        #     'domain': {
        #         'partner_invoice_id':[('id','=',self.partner_id.parent_id.id)],
        #     },
        # }

# class AccountCustom0(models.Model):
#     _name = 'account.move'
#     _inherit = 'account.move'

#     @api.model
#     def default_get(self, default_fields):
#         # OVERRIDE linea 3455
#         values = super(AccountMoveLine, self).default_get(default_fields)

#         if 'account_id' in default_fields \
#             and (self._context.get('journal_id') or self._context.get('default_journal_id')) \
#             and not values.get('account_id') \
#             and self._context.get('default_type') in self.move_id.get_inbound_types():
#             # Fill missing 'account_id'.
#             journal = self.env['account.journal'].browse(self._context.get('default_journal_id') or self._context['journal_id'])
#             values['account_id'] = journal.default_credit_account_id.id
#         elif 'account_id' in default_fields \
#             and (self._context.get('journal_id') or self._context.get('default_journal_id')) \
#             and not values.get('account_id') \
#             and self._context.get('default_type') in self.move_id.get_outbound_types():
#             # Fill missing 'account_id'.
#             journal = self.env['account.journal'].browse(self._context.get('default_journal_id') or self._context['journal_id'])
#             values['account_id'] = journal.default_debit_account_id.id
#         elif self._context.get('line_ids') and any(field_name in default_fields for field_name in ('debit', 'credit', 'account_id', 'partner_id')):
#             move = self.env['account.move'].new({'line_ids': self._context['line_ids']})

#             # Suggest default value for debit / credit to balance the journal entry.
#             balance = sum(line['debit'] - line['credit'] for line in move.line_ids)
#             # if we are here, line_ids is in context, so journal_id should also be.
#             journal = self.env['account.journal'].browse(self._context.get('default_journal_id') or self._context['journal_id'])
#             currency = journal.exists() and journal.company_id.currency_id
#             if currency:
#                 balance = currency.round(balance)
#             if balance < 0.0:
#                 values.update({'debit': -balance})
#             if balance > 0.0:
#                 values.update({'credit': balance})

#             # Suggest default value for 'partner_id'.
#             if 'partner_id' in default_fields and not values.get('partner_id'):
#                 if len(move.line_ids[-2:]) == 2 and  move.line_ids[-1].partner_id == move.line_ids[-2].partner_id != False:
#                     values['partner_id'] = move.line_ids[-2:].mapped('partner_id').id

#             # Suggest default value for 'account_id'.
#             if 'account_id' in default_fields and not values.get('account_id'):
#                 if len(move.line_ids[-2:]) == 2 and  move.line_ids[-1].account_id == move.line_ids[-2].account_id != False:
#                     values['account_id'] = move.line_ids[-2:].mapped('account_id').id
#         if values.get('display_type'):
#             values.pop('account_id', None)
#         if (values.get('partner_id')):
#             partner = self.env['res.partner'].search([('id', '=', values.get('partner_id') )], limit=1)
#             values['analytic_tag_ids'] = partner.x_studio_canal_de_venta_1_1.id
#             if(partner):
#                 if(partner.x_studio_canal_de_venta_1_1):
#                     listOfValue = []
#                     listOfValue.append(partner.x_studio_canal_de_venta_1_1.id)
#                     values['analytic_tag_ids'] = listOfValue
#                 if(partner.x_studio_canales_de_venta_23_1):
#                     values['analytic_account_id'] = partner.x_studio_canales_de_venta_23_1.id
#         return values