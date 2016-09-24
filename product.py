# -*- coding: utf-8 -*-

import time
import datetime
from openerp import pooler
from openerp import models,fields,api
from openerp.tools.translate import _



class product_template(models.Model):
    _inherit = "product.template"


    @api.multi
    def copy(self,vals):
        for obj in self:
            vals.update({
                'is_code': obj.is_code + ' (copie)',
            })
            res=super(product_template, self).copy(vals)
            model = self.env['product.supplierinfo']
            for item in obj.seller_ids:
                vals = {
                    'product_tmpl_id': res.id,
                    'name'           : item.name.id,
                    'product_name'   : item.product_name,
                    'sequence'       : item.sequence,
                    'product_code'   : item.product_code,
                    'min_qty'        : item.min_qty,
                    'delay'          : item.delay,
                }
                id = model.create(vals)
            model = self.env['product.packaging']
            for item in obj.packaging_ids:
                
                vals = {
                    'product_tmpl_id': res.id,
                    'ean'            : item.ean,
                    'qty'            : item.qty,
                    'ul'             : item.ul.id,
                    'ul_qty'         : item.ul_qty,
                    'rows'           : item.rows,
                    'ul_container'   : item.ul_container.id,
                    'weight'         : item.weight,
                }
                id = model.create(vals)
        return res


    def get_uc(self):
        uc=0
        for obj in self:
            if obj.packaging_ids:
                uc=obj.packaging_ids[0].qty
        if uc==0:
            uc=1
        return uc

    def get_um(self):
        um=0
        for obj in self:
            if obj.packaging_ids:
                um=obj.packaging_ids[0].qty*obj.packaging_ids[0].rows*obj.packaging_ids[0].ul_qty
        if um==0:
            um=self.get_uc()
        return um


class product_product(models.Model):
    _name = "product.product"
    _inherit = "product.product"
     
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context and context.get('pricelist', False):
            date = context.get('date') or time.strftime('%Y-%m-%d')
            pricelist = self.pool.get('product.pricelist').browse(cr, uid, context.get('pricelist', False), context=context)
            version = False
            for v in pricelist.version_id:
                if ((v.date_start is False) or (v.date_start <= date)) and ((v.date_end is False) or (v.date_end >= date)):
                    version = v
                    break
            
            if version:
                cr.execute("SELECT distinct(product_id) FROM product_pricelist_item where price_version_id = %s" ,(version.id,))
                ids = [x[0] for x in cr.fetchall()]
                ids = None in ids and  [] or ids
                if ids:
                    args.append(('id', 'in', ids))
                    order = 'default_code'
            else:
                args.append(('id', 'in', []))
            
        return super(product_product, self).search(cr, uid, args, offset=offset, limit=limit, order=order, context=context, count=count)
 


class product_uom(models.Model):
    _inherit = 'product.uom'

    _order   = 'category_id,name'


        
