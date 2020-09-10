# -*- coding: utf-8 -*-

from odoo import api, fields, models, exceptions, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError, ValidationError


class contact_custom_0(models.Model):

    _inherit = 'res.partner'

    @api.onchange('parent_id')
    def onchange_parent_id(self):
        # return values in result, as this method is used by _fields_sync()
        if not self.parent_id:
            return
        result = {}
        partner = self._origin
        if partner.parent_id and partner.parent_id != self.parent_id:
            result['warning'] = {
                'title': _('Warning'),
                'message': _('Changing the company of a contact should only be done if it '
                             'was never correctly set. If an existing contact starts working for a new '
                             'company then a new contact should be created under that new '
                             'company. You can use the "Discard" button to abandon this change.')}
        if partner.type == 'contact' or self.type == 'contact':
            # for contacts: copy the parent address, if set (aka, at least one
            # value is set in the address: otherwise, keep the one from the
            # contact)
            address_fields = self._address_fields()
            if any(self.parent_id[key] for key in address_fields):
                def convert(value):
                    return value.id if isinstance(value, models.BaseModel) else value
                result['value'] = {key: convert(self.parent_id[key]) for key in address_fields}
        
        self.set_value_of_partner()
        
        return result

    @api.onchange('type')
    def onchange_type(self):
        self.set_value_of_partner()

    def set_value_of_partner(self):
        if((self.type == 'contact' or self.type == 'delivery') and (self.parent_id and self.parent_id.id)):
            self.x_studio_canal_de_venta = self.parent_id.x_studio_canal_de_venta
            self.x_studio_canal_de_venta_1 = self.parent_id.x_studio_canal_de_venta_1
            self.user_id = self.parent_id.user_id
            self.x_studio_notificar_pedido = self.parent_id.x_studio_notificar_pedido
    
    def create(self, vals_list):
        for vals in vals_list:
            if(vals.get('type') is not None and (vals['type'] == 'contact' or vals['type'] == 'delivery') and (vals.get('parent_id') is not None and vals['parent_id'] != False)):
                parent = self.env['res.partner'].search([('id','=',vals['parent_id'])], limit=1)
                vals['x_studio_canal_de_venta'] = parent.x_studio_canal_de_venta.id
                vals['x_studio_canal_de_venta_1'] = parent.x_studio_canal_de_venta_1.id
                vals['user_id'] = parent.user_id.id
                vals['x_studio_notificar_pedido'] = parent.x_studio_notificar_pedido
        return super(contact_custom_0, self).create(vals_list)

    def write(self, vals):
        for partner in self:
            if(partner.id):
                childs = self.env['res.partner'].search([('parent_id','=',partner.id)])
                for child in childs:
                    if(child.type is not None and (child.type == 'contact' or child.type == 'delivery') and ('x_studio_notificar_pedido' in vals)):
                        child.x_studio_notificar_pedido = vals['x_studio_notificar_pedido']
        return super(contact_custom_0, self).write(vals)