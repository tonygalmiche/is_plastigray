# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from datetime import datetime

class stock_transfer_details(models.TransientModel):
    _inherit = 'stock.transfer_details'
    _description = 'Picking wizard'

    def default_get(self, cr, uid, fields, context=None):        
        if context is None: context = {}
        picking_ids = context.get('active_ids', [])
        picking_id, = picking_ids
        picking = self.pool.get('stock.picking').browse(cr, uid, picking_id, context=context)
        stock_product_lot_obj = self.pool.get('stock.production.lot')
        res = super(stock_transfer_details, self).default_get(cr, uid, fields, context=context)
        item_data = res.get('item_ids',[])
        for item in item_data:
            if item.get('lot_id', False) == False:
                lot_id = stock_product_lot_obj.search(cr, uid, [('name','=', picking.name),('product_id','=', item.get('product_id'))], context=context)
                if lot_id: lot_id = lot_id[0]
                else:
                    lot_id = stock_product_lot_obj.create(cr, uid, {
                            'name': picking.name,
                            'product_id': item.get('product_id'),
                    }, context=context)
                if lot_id:
                    item['lot_id']=lot_id
        return res
        

