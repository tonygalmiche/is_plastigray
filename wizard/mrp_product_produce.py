# -*- coding: utf-8 -*-

from openerp.osv import fields, osv

class mrp_product_produce(osv.osv_memory):
    _inherit = 'mrp.product.produce'

    def default_get(self, cr, uid, fields, context=None):        
        if context is None: context = {}
        res = super(mrp_product_produce, self).default_get(cr, uid, fields, context=context)
        prod_obj = self.pool.get("mrp.production")
        if context.get('active_id', False) and res.get('product_id',False):
            production = prod_obj.browse(cr, uid, context['active_id'], context=context)
            stock_product_lot_obj = self.pool.get('stock.production.lot')
            lot_id = stock_product_lot_obj.search(cr, uid, [('name','=', production.name),('product_id','=', res.get('product_id'))], context=context)
            if lot_id: lot_id = lot_id[0]
            else:
                lot_id = stock_product_lot_obj.create(cr, uid, {
                                'name': production.name,
                                'product_id': res.get('product_id'),
                        }, context=context)
            if lot_id:
                res['lot_id']=lot_id
        return res
