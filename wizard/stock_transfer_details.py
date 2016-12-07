# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import Warning
import openerp.addons.decimal_precision as dp
import datetime


class stock_transfer_details(models.TransientModel):
    _inherit = 'stock.transfer_details'
    _description = 'Picking wizard'


    is_purchase_order_id = fields.Many2one('purchase.order', 'Commande Fournisseur')
    is_num_bl            = fields.Char("N° BL fournisseur")
    is_date_reception    = fields.Date('Date de réception')

    def _date():
        return datetime.date.today().strftime('%Y-%m-%d')

    _defaults = {
        'is_date_reception':  _date(),
    }


    @api.one
    def do_detailed_transfer(self):
        res = super(stock_transfer_details, self).do_detailed_transfer()
        for obj in self:
            obj.picking_id.is_num_bl         = obj.is_num_bl
            obj.picking_id.is_date_reception = obj.is_date_reception
            for row in obj.item_ids:
                if row.lot_id:
                    row.lot_id.is_lot_fournisseur=row.is_lot_fournisseur
        #raise Warning('test')
        return res


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
        if picking.is_purchase_order_id:
            res.update({'is_purchase_order_id': picking.is_purchase_order_id.id})
        return res
        



class stock_transfer_details_items(models.TransientModel):
    _inherit = 'stock.transfer_details_items'

    is_lot_fournisseur = fields.Char("Lot fournisseur")






