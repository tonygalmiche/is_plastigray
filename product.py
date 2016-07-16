# -*- coding: utf-8 -*-

import time
import datetime
from openerp import pooler
from openerp import models,fields,api
from openerp.tools.translate import _

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


        
