import xmlrpc.client

url = 'https://xcamposdev-foodsfortomorrow-preprod-1141072.dev.odoo.com'
db = 'xcamposdev-foodsfortomorrow-preprod-1141072'
username = 'acastillo@develoop.net'
password = 'Temp1243'

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
version = common.version()
print("Detalles...", version)

uid = common.authenticate(db, username, password, {})
print("UID", uid)

models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
# permission = models.execute_kw(db, uid, password, 
#     'x_orders_salida', 'check_access_rights',
#     ['read'], {'raise_exception': False})
# print("Tiene permisos", permission)
models.execute_kw(db, uid, password, 'x_orders_salida','search',[[['id', '!=', -1]]])
models.execute_kw(db, uid, password,
    'res.partner', 'search',
    [[['is_company', '=', False]]])
# print("UID", orders_salida)
# models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
# partners = models.execute_kw(db, uid, password, 'res.company','create',[[]])
#partners = models.execute_kw(db, uid, password, 'res_company','search',[[['is_company', '=', True]]], {'offset': 10, 'limit': 5})
# limit: cantidad de registros a devolver, offset: cantidad de registros a saltar
# print("Partners", partners)

# partner_rec = models.execute_kw(db, uid, password, 'res.company','read',[partners], {'fields':['id', 'name']})
# print("Partners_rec", partner_rec)