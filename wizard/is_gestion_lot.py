# -*- coding: utf-8 -*-

import time
import datetime

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import netsvc
from operator import itemgetter

class is_gestion_lot(osv.osv):
    _name = 'is.gestion.lot'
    _description = u"gestion contrôle qualité"               
    
    _columns = {
        'product_id': fields.many2one('product.product', 'Article', readonly=True),
        'is_uc_qt': fields.integer('Qt/UC', related='product_id.is_uc_qt', readonly=True),
        'prod_lot_id': fields.many2one('stock.production.lot', 'Lot', readonly=True),
        'planned_date': fields.datetime(u'Date prévue'),
        'location_src_id': fields.many2one('stock.location', 'Emplacement source',readonly=True),
        'location_dest_bloq_id': fields.many2one('stock.location', 'Emplacement de destination'),
        'location_dest_debloq_id': fields.many2one('stock.location', 'Emplacement de destination'),
        'location_dest_change_id': fields.many2one('stock.location', 'Emplacement de destination'),
        'product_qty': fields.float(u'Quantité', required=True),
        'description': fields.many2one('is.commentaire.mouvement.stock', 'Description'),
        'operation': fields.selection([
                                ('bloque', u'Bloqué'),
                                ('debloque', u'Débloqué'),
                                ('change_location', 'Changement emplacement'),
                                ('rebut', 'Mise au rebut')], 'Operation', readonly=True),     
    }
    
    _defaults = {
        'planned_date': time.strftime('%Y-%m-%d %H:%M:%S'),
    }
    
    # Retourne la quantité en stock d'un lot de produit dans un emplacement donnée
    def get_product_qty_lot_location(self, cr, uid, product_id, lot_id, location_src_id, context=None):
        quant_obj = self.pool.get('stock.quant')
        qty = 0
        if product_id and lot_id and location_src_id:
            quant_ids = quant_obj.search(cr, uid, [('product_id','=',product_id), ('lot_id','=',lot_id), ('location_id','=',location_src_id)], context=context)
            if quant_ids:
                for quant in quant_obj.read(cr, uid, quant_ids, ['qty'], context=context):
                    qty += quant['qty']
        return qty
    
    def _check_product_qty(self, cr, uid, ids, context=None):
        obj = self.browse(cr, uid, ids[0], context=context)
        if obj.product_id and obj.prod_lot_id and obj.location_src_id:
            qty = self.get_product_qty_lot_location(cr, uid, obj.product_id.id, obj.prod_lot_id.id, obj.location_src_id.id, context)
            if obj.product_qty > qty:
                return False
        return True

    
    _constraints = [
        (_check_product_qty, u'La quantité que vous avez entrée est supérieure à celle existante en stock', ['product_qty']),
    ]
    
    def default_get(self, cr, uid, fields, context=None):
        if context is None: context = {}
        res = super(is_gestion_lot, self).default_get(cr, uid, fields, context=context)
        line_ids = context.get('active_ids', [])        
        active_model = context.get('active_model')

        if not line_ids or len(line_ids) != 1:
            return res
        
        bloque_id, = line_ids
        line = self.pool.get(active_model).browse(cr, uid, bloque_id, context=context)
        if 'operation' in fields:
            res.update(operation=line.operation)
        if 'product_id' in fields:
            res.update(product_id=line.product_id.id)
        if 'prod_lot_id' in fields:
            res.update(prod_lot_id=line.lot_id.id)
        if 'product_qty' in fields:
            res.update(product_qty=line.qty)
        if 'location_src_id' in fields:
            res.update(location_src_id=line.location_id.id)
        return res
    
    # Créer un mouvement
    def create_stock_move(self, cr, uid, ids, data, context=None):
        move_obj = self.pool.get('stock.move')
        
        location_dest_id = False
        if data.operation == 'bloque':
            location_dest_id = data.location_dest_bloq_id.id
        if data.operation == 'debloque':
            location_dest_id = data.location_dest_debloq_id.id
        if data.operation == 'change_location':
            location_dest_id = data.location_dest_change_id.id
        
        res = move_obj.onchange_product_id(cr, uid, ids, data.product_id.id, data.location_src_id.id, location_dest_id, False)
        uos_id = data.product_id.uos_id and data.product_id.uos_id.id or False
        type_interne = self.pool.get('stock.picking.type').search(cr, uid, [('code','=','internal')], context=context)                    
            
        vals = {
            'product_id': data.product_id.id,
            'product_uom_qty': data.product_qty,
            'name': data.description and data.description.name or res['value']['name'],
            'product_uom': res['value']['product_uom'],
            'product_uos': res['value']['product_uos'],
            'product_uom_qty': data.product_qty,
            'product_uos_qty': self.pool.get('stock.move').onchange_quantity(cr, uid, ids, data.product_id.id, data.product_qty, data.product_id.uom_id.id, uos_id)['value']['product_uos_qty'],               
            'location_id': data.location_src_id.id,
            'location_dest_id': location_dest_id,
            'date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'planned_date': data.planned_date,
            'picking_type_id': type_interne and type_interne[0],
            'restrict_lot_id': data.prod_lot_id.id,
        }
        new_id = move_obj.create(cr, uid, vals, context=context)
        return new_id               
                
    
    # la validation de bouton de l'assistant
    def validate_lot(self, cr, uid, ids, context=None):
        move_obj = self.pool.get('stock.move')
        if context is None:
            context = {}
        data = self.browse(cr, uid, ids[0])

        if data:
            move_id = self.create_stock_move(cr, uid, ids, data, context=context)
            # Valider le mouvement
            move_obj.action_done(cr, uid, [move_id], context=context)       
            action_model = False
            data_pool = self.pool.get('ir.model.data')
            action = {}
            if data.operation == 'bloque':
                action_model,action_id = data_pool.get_object_reference(cr, uid, 'is_plastigray', "action_stock_lot_bloque_report")
                action_pool = self.pool.get(action_model)
                action = action_pool.read(cr, uid, action_id, context=context)
                return action             
            elif data.operation == 'debloque':
                action_model,action_id = data_pool.get_object_reference(cr, uid, 'is_plastigray', "action_stock_lot_debloque_report")
                action_pool = self.pool.get(action_model)
                action = action_pool.read(cr, uid, action_id, context=context)
                return action
            elif data.operation == 'change_location':
                action_model,action_id = data_pool.get_object_reference(cr, uid, 'is_plastigray', "action_stock_lot_change_location_report")
                action_pool = self.pool.get(action_model)
                action = action_pool.read(cr, uid, action_id, context=context)
                return action
            else:
                return {}
    
is_gestion_lot()
