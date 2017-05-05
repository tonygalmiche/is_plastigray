## -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import osv
from openerp.report import report_sxw
from openerp.addons.mrp.report import bom_structure


class bom_structure1(bom_structure.bom_structure):

    def get_children(self, object, level=0):
        result = []

        def _get_rec(object, level):
            for l in object:
                res = {}
                res['pname'] = l.product_id.name
                res['pcode'] = l.product_id.is_code
                res['pqty'] = l.product_qty
                res['uname'] = l.product_uom.name
                res['level'] = level
                res['code'] = l.bom_id.code
                res['segment'] = l.bom_id.segment_id and l.bom_id.segment_id.name or ''
                res['is_category_id'] = l.product_id.product_tmpl_id.is_category_id and l.product_id.product_tmpl_id.is_category_id.name or ''
                res['is_qt_uc'] = l.bom_id.is_qt_uc
                res['is_qt_um'] = l.bom_id.is_qt_um
                res['routing_id'] = l.bom_id.routing_id and l.bom_id.routing_id.name or ''
                res['is_gamme_generique_id'] = l.bom_id.is_gamme_generique_id and l.bom_id.is_gamme_generique_id.name or ''
                
                
                result.append(res)
                if l.child_line_ids:
                    if level<6:
                        level += 1
                    _get_rec(l.child_line_ids,level)
                    if level>0 and level<6:
                        level -= 1
            return result

        children = _get_rec(object,level)

        return children


class report_mrpbomstructure(osv.AbstractModel):
    _name = 'report.mrp.report_mrpbomstructure'
    _inherit = 'report.abstract_report'
    _template = 'mrp.report_mrpbomstructure'
    _wrapped_report_class = bom_structure1

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
