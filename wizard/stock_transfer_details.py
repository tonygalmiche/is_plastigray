# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import Warning
import openerp.addons.decimal_precision as dp
import datetime


def _date_reception():
    return datetime.date.today().strftime('%Y-%m-%d')


class stock_transfer_details(models.TransientModel):
    _inherit = 'stock.transfer_details'
    _description = 'Picking wizard'


    is_purchase_order_id = fields.Many2one('purchase.order', 'Commande Fournisseur')
    is_num_bl            = fields.Char("N° BL fournisseur")
    is_date_reception    = fields.Date('Date de réception')


    _defaults = {
        'is_date_reception': lambda *a: _date_reception(),
    }


    @api.one
    def do_detailed_transfer(self):
        res = super(stock_transfer_details, self).do_detailed_transfer()
        for obj in self:
            obj.picking_id.is_num_bl         = obj.is_num_bl
            obj.picking_id.is_date_reception = obj.is_date_reception
            if obj.picking_id.is_purchase_order_id:
                for row in obj.item_ids:
                    if row.lot_id:
                        row.lot_id.is_lot_fournisseur=row.is_lot_fournisseur
        return res


    def default_get(self, cr, uid, fields, context=None):
        if context is None: context = {}
        picking_ids = context.get('active_ids', [])
        picking_id, = picking_ids
        picking = self.pool.get('stock.picking').browse(cr, uid, picking_id, context=context)
        stock_product_lot_obj = self.pool.get('stock.production.lot')
        res = super(stock_transfer_details, self).default_get(cr, uid, fields, context=context)


        #** Permet de gérer les réceptions avec le même article ****************
        picking_ids = context.get('active_ids', [])
        active_model = context.get('active_model')

        if not picking_ids or len(picking_ids) != 1:
            return res
        assert active_model in ('stock.picking'), 'Bad context propagation'
        picking_id, = picking_ids
        picking = self.pool.get('stock.picking').browse(cr, uid, picking_id, context=context)
        items = []
        packs = []
        if not picking.pack_operation_ids:
            picking.do_prepare_partial()
        for op in picking.pack_operation_ids:
            item = {
                'packop_id': op.id,
                'product_id': op.product_id.id,
                'product_uom_id': op.product_uom_id.id,
                'quantity': op.product_qty,
                'package_id': op.package_id.id,
                'lot_id': op.lot_id.id,
                'is_lot_fournisseur':op.lot_id.is_lot_fournisseur,
                'sourceloc_id': op.location_id.id,
                'destinationloc_id': op.location_dest_id.id,
                'result_package_id': op.result_package_id.id,
                'date': op.date, 
                'owner_id': op.owner_id.id,
                'name':op.move_id.name
            }
            if op.product_id:
                items.append(item)
            elif op.package_id:
                packs.append(item)
        res.update(item_ids=items)
        res.update(packop_ids=packs)
        #***********************************************************************


#        #** Permet de créer un lot avec le même numéro que la réception ********
#        if picking.is_purchase_order_id:
#            res.update({'is_purchase_order_id': picking.is_purchase_order_id.id})
#            item_data = res.get('item_ids',[])
#            for item in item_data:
#                if item.get('lot_id', False) == False:
#                    lot_id = stock_product_lot_obj.search(cr, uid, [('name','=', picking.name),('product_id','=', item.get('product_id'))], context=context)
#                    if lot_id: lot_id = lot_id[0]
#                    else:
#                        lot_id = stock_product_lot_obj.create(cr, uid, {
#                                'name': picking.name,
#                                'product_id': item.get('product_id'),
#                        }, context=context)
#                    if lot_id:
#                        item['lot_id']=lot_id
#        #***********************************************************************



        #** Créer lot avec le même numéro que la réception et la date devant ***
        if picking.is_purchase_order_id:
            res.update({'is_purchase_order_id': picking.is_purchase_order_id.id})
            item_data = res.get('item_ids',[])
            for item in item_data:
                if item.get('lot_id', False) == False:
                    numlot=datetime.date.today().strftime('%y%m%d')+picking.name
                    lot_id = stock_product_lot_obj.search(cr, uid, [
                            ('name','=', numlot),
                            ('product_id','=', item.get('product_id'))
                        ], context=context)
                    if lot_id: lot_id = lot_id[0]
                    else:
                        lot_id = stock_product_lot_obj.create(cr, uid, {
                                'name': numlot,
                                'product_id': item.get('product_id'),
                        }, context=context)
                    if lot_id:
                        item['lot_id']=lot_id
        #***********************************************************************

        return res
        



class stock_transfer_details_items(models.TransientModel):
    _inherit = 'stock.transfer_details_items'

    name                  = fields.Char('Description')
    is_lot_fournisseur    = fields.Char("Lot fournisseur / Date péremption")
    is_produit_perissable = fields.Boolean("Produit périssable", related="product_id.is_produit_perissable", readonly=True)
    is_ctrl_rcp           = fields.Selection([('bloque','Produit bloqué')], "Contrôle réception", related='product_id.is_ctrl_rcp', readonly=True)


    @api.multi
    def produit_perissable_action(self):
        print self

