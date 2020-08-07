# -*- coding: utf-8 -*-
import collections
from odoo import api, fields, models, exceptions, _
from odoo.exceptions import AccessError, UserError, ValidationError


class AccountCustom0(models.Model):

    _inherit = 'account.move.line'

    custom_analytic = fields.Integer(compute='_compute_data_analytic')
    
    @api.depends('account_id','partner_id')
    def _compute_data_analytic(self):
        for rec in self:
            rec.custom_analytic = 0
            if (rec.analytic_account_id == False or rec.analytic_account_id.id == False) and \
                rec.partner_id != False and rec.partner_id.id != False and \
                rec.account_id != False and rec.account_id.id != False:
                if (rec.account_id.code.startswith('6') or rec.account_id.code.startswith('7')):
                    rec.analytic_account_id = rec.partner_id.x_studio_canal_de_venta

            if (rec.analytic_tag_ids == False or rec.analytic_tag_ids.id == False) and \
                rec.partner_id != False and rec.partner_id.id != False and \
                rec.account_id != False and rec.account_id.id != False:
                if (rec.account_id.code.startswith('6') or rec.account_id.code.startswith('7')):
                    listOfValue = []
                    listOfValue.append(rec.partner_id.x_studio_canal_de_venta_1)
                    rec.analytic_tag_ids = listOfValue

    @api.onchange('account_id','partner_id')
    def _onchange_data_analytic(self):
        for rec in self:
            rec.custom_analytic = 0
            if (rec.analytic_account_id == False or rec.analytic_account_id.id == False) and \
                rec.partner_id != False and rec.partner_id.id != False and \
                rec.account_id != False and rec.account_id.id != False:
                if (rec.account_id.code.startswith('6') or rec.account_id.code.startswith('7')):
                    rec.analytic_account_id = rec.partner_id.x_studio_canal_de_venta

            if (rec.analytic_tag_ids == False or rec.analytic_tag_ids.id == False) and \
                rec.partner_id != False and rec.partner_id.id != False and \
                rec.account_id != False and rec.account_id.id != False:
                if (rec.account_id.code.startswith('6') or rec.account_id.code.startswith('7')):
                    listOfValue = []
                    if(rec.partner_id.x_studio_canal_de_venta_1 != False and rec.partner_id.x_studio_canal_de_venta_1.id != False):
                        listOfValue.append(rec.partner_id.x_studio_canal_de_venta_1.id)
                    rec.analytic_tag_ids = listOfValue    


class BaseModelCustom0(models.AbstractModel):
        
    _inherit = 'base'

    def _export_rows(self, fields, *, _is_toplevel_call=True):
        """ Export fields of the records in ``self``.

            :param fields: list of lists of fields to traverse
            :param bool _is_toplevel_call:
                used when recursing, avoid using when calling from outside
            :return: list of lists of corresponding values
        """
        import_compatible = self.env.context.get('import_compat', True)
        lines = []

        def splittor(rs):
            """ Splits the self recordset in batches of 1000 (to avoid
            entire-recordset-prefetch-effects) & removes the previous batch
            from the cache after it's been iterated in full
            """
            for idx in range(0, len(rs), 1000):
                sub = rs[idx:idx+1000]
                for rec in sub:
                    yield rec
                rs.invalidate_cache(ids=sub.ids)
        if not _is_toplevel_call:
            splittor = lambda rs: rs

        # memory stable but ends up prefetching 275 fields (???)
        for record in splittor(self):
            # main line of record, initially empty
            current = [''] * len(fields)
            lines.append(current)

            # list of primary fields followed by secondary field(s)
            primary_done = []

            # process column by column
            for i, path in enumerate(fields):
                if not path:
                    continue

                name = path[0]
                if name in primary_done:
                    continue

                if name == '.id':
                    current[i] = str(record.id)
                elif name == 'id':
                    current[i] = (record._name, record.id)
                else:
                    field = record._fields[name]
                    value = record[name]

                    # this part could be simpler, but it has to be done this way
                    # in order to reproduce the former behavior
                    if not isinstance(value, BaseModelCustom0):
                        current[i] = field.convert_to_export(value, record)
                    else:
                        primary_done.append(name)

                        # in import_compat mode, m2m should always be exported as
                        # a comma-separated list of xids in a single cell
                        if import_compatible and field.type == 'many2many' and len(path) > 1 and path[1] == 'id':
                            xml_ids = [xid for _, xid in value.__ensure_xml_id()]
                            current[i] = ','.join(xml_ids) or False
                            continue

                        # recursively export the fields that follow name; use
                        # 'display_name' where no subfield is exported
                        fields2 = [(p[1:] or ['display_name'] if p and p[0] == name else [])
                                   for p in fields]
                        lines2 = value._export_rows(fields2, _is_toplevel_call=False)
                        if lines2:
                            # merge first line with record's main line
                            for j, val in enumerate(lines2[0]):
                                if val or isinstance(val, bool):
                                    current[j] = val
                            # append the other lines at the end
                            # lines += lines2[1:]
                            if(len(lines2[1:]) > 0):
                                for line_custom in lines2[1:]:
                                    line_to_add = lines[len(lines)-1].copy()
                                    lines.append(line_to_add)
                                    for i_custom in range(len(line_custom)):
                                        if(line_custom[i_custom]):
                                            lines[len(lines) - 1][i_custom] = line_custom[i_custom]
                            else:
                                lines += lines2[1:]
                        else:
                            current[i] = False

        # if any xid should be exported, only do so at toplevel
        if _is_toplevel_call and any(f[-1] == 'id' for f in fields):
            bymodels = collections.defaultdict(set)
            xidmap = collections.defaultdict(list)
            # collect all the tuples in "lines" (along with their coordinates)
            for i, line in enumerate(lines):
                for j, cell in enumerate(line):
                    if type(cell) is tuple:
                        bymodels[cell[0]].add(cell[1])
                        xidmap[cell].append((i, j))
            # for each model, xid-export everything and inject in matrix
            for model, ids in bymodels.items():
                for record, xid in self.env[model].browse(ids).__ensure_xml_id():
                    for i, j in xidmap.pop((record._name, record.id)):
                        lines[i][j] = xid
            assert not xidmap, "failed to export xids for %s" % ', '.join('{}:{}' % it for it in xidmap.items())

        return lines