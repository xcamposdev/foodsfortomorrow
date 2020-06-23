# -*- coding: utf-8 -*-

import logging
import psycopg2

from odoo import models, api

_logger = logging.getLogger(__name__)


class Import(models.TransientModel):

    _inherit = 'base_import.import'

    def do(self, fields, columns, options, dryrun=False):
        """ Actual execution of the import

        :param fields: import mapping: maps each column to a field,
                       ``False`` for the columns to ignore
        :type fields: list(str|bool)
        :param columns: columns label
        :type columns: list(str|bool)
        :param dict options:
        :param bool dryrun: performs all import operations (and
                            validations) but rollbacks writes, allows
                            getting as much errors as possible without
                            the risk of clobbering the database.
        :returns: A list of errors. If the list is empty the import
                  executed fully and correctly. If the list is
                  non-empty it contains dicts with 3 keys ``type`` the
                  type of error (``error|warning``); ``message`` the
                  error message associated with the error (a string)
                  and ``record`` the data which failed to import (or
                  ``false`` if that data isn't available or provided)
        :rtype: dict(ids: list(int), messages: list({type, message, record}))
        """
        self.ensure_one()
        self._cr.execute('SAVEPOINT import')

        try:
            data, import_fields = self._convert_import_data(fields, options)

            if(self.res_model=='stock.picking'):
                pos_product = [index for index in range(len(fields)) if fields[index] == 'move_line_nosuggest_ids/product_id']
                lote_nro_serie = [index for index in range(len(fields)) if fields[index] == 'move_line_nosuggest_ids/lot_id']
                if(len(pos_product) > 0 and len(lote_nro_serie) > 0):
                    for x in data:
                        product_ids = self.env['product.product'].name_search(name=x[pos_product[0]], operator='=')
                        if(product_ids):
                            product_id, _name = product_ids[0]
                            stock_production_lot = self.env['stock.production.lot'].search([('product_id','=',product_id),('name','=',x[lote_nro_serie[0]-1])], limit=1)
                            if(stock_production_lot):
                                x[lote_nro_serie[0]-1] = str(stock_production_lot.id)

            # Parse date and float field
            data = self._parse_import_data(data, import_fields, options)
        except ValueError as error:
            return {
                'messages': [{
                    'type': 'error',
                    'message': str(error),
                    'record': False,
                }]
            }

        _logger.info('importing %d rows...', len(data))

        name_create_enabled_fields = options.pop('name_create_enabled_fields', {})
        import_limit = options.pop('limit', None)
        model = self.env[self.res_model].with_context(import_file=True, name_create_enabled_fields=name_create_enabled_fields, _import_limit=import_limit)
        import_result = model.load(import_fields, data)
        _logger.info('done')

        # If transaction aborted, RELEASE SAVEPOINT is going to raise
        # an InternalError (ROLLBACK should work, maybe). Ignore that.
        # TODO: to handle multiple errors, create savepoint around
        #       write and release it in case of write error (after
        #       adding error to errors array) => can keep on trying to
        #       import stuff, and rollback at the end if there is any
        #       error in the results.
        try:
            if dryrun:
                self._cr.execute('ROLLBACK TO SAVEPOINT import')
                # cancel all changes done to the registry/ormcache
                self.pool.clear_caches()
                self.pool.reset_changes()
            else:
                self._cr.execute('RELEASE SAVEPOINT import')
        except psycopg2.InternalError:
            pass

        # Insert/Update mapping columns when import complete successfully
        if import_result['ids'] and options.get('headers'):
            BaseImportMapping = self.env['base_import.mapping']
            for index, column_name in enumerate(columns):
                if column_name:
                    # Update to latest selected field
                    exist_records = BaseImportMapping.search([('res_model', '=', self.res_model), ('column_name', '=', column_name)])
                    if exist_records:
                        exist_records.write({'field_name': fields[index]})
                    else:
                        BaseImportMapping.create({
                            'res_model': self.res_model,
                            'column_name': column_name,
                            'field_name': fields[index]
                        })
        if 'name' in import_fields:
            index_of_name = import_fields.index('name')
            skipped = options.get('skip', 0)
            # pad front as data doesn't contain anythig for skipped lines
            r = import_result['name'] = [''] * skipped
            # only add names for the window being imported
            r.extend(x[index_of_name] for x in data[:import_limit])
            # pad back (though that's probably not useful)
            r.extend([''] * (len(data) - (import_limit or 0)))
        else:
            import_result['name'] = []

        skip = options.get('skip', 0)
        # convert load's internal nextrow to the imported file's
        if import_result['nextrow']: # don't update if nextrow = 0 (= no nextrow)
            import_result['nextrow'] += skip

        return import_result