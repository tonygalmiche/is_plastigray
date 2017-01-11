# -*- coding: utf-8 -*-

import time
import datetime

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import netsvc
from operator import itemgetter
import openerp.addons.decimal_precision as dp

class is_stock_mise_rebut(osv.osv):
    _name = 'is.stock.mise.rebut'
    _description = "Mise au rebut"
    
    _columns = {
        'product_id': fields.many2one('product.product', 'Article', readonly=True),
        'is_uc_qt': fields.integer('Qt/UC', related='product_id.is_uc_qt', readonly=True),
        'product_qty': fields.float('Quantité', required=True),
        'location_rebut_id': fields.many2one('stock.location', 'Emplacement de destination'),
        'location_revert_id': fields.many2one('stock.location', 'Emplacement de destination'),
        'restrict_lot_id': fields.many2one('stock.production.lot', 'Lot', readonly=True),
        'location_src_id': fields.many2one('stock.location', 'Emplacement source', readonly=True),
        'operation': fields.selection([
                                ('bloque', u'Bloqué'),
                                ('debloque', u'Débloqué'),
                                ('change_location', 'Changement emplacement'),
                                ('rebut', 'Mise au rebut')], 'Operation', readonly=True),     

    }
    
    def default_get(self, cr, uid, fields, context=None):
        """ Get default values
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param fields: List of fields for default value
        @param context: A standard dictionary
        @return: default values of fields
        """
        if context is None:
            context = {}
            
        res = super(is_stock_mise_rebut, self).default_get(cr, uid, fields, context=context)
        line_ids = context.get('active_ids', [])        
        active_model = context.get('active_model')

        if not line_ids or len(line_ids) != 1:
            return res
        
        bloque_id, = line_ids
        line = self.pool.get(active_model).browse(cr, uid, bloque_id, context=context)

        if 'product_id' in fields:
            res.update({'product_id': line.product_id.id})
        if 'product_qty' in fields:
            res.update({'product_qty': line.qty})
        if 'restrict_lot_id' in fields:
            res.update(restrict_lot_id=line.lot_id.id)
        if 'location_src_id' in fields:
            res.update(location_src_id=line.location_id.id)
        if 'operation' in fields:
            res.update(operation=line.operation)
        return res
    
    # Créer un mouvement
    def create_stock_move(self, cr, uid, ids, data, context=None):
        move_obj = self.pool.get('stock.move')
        
        location_dest_id = False
        if data.operation == 'rebut':
            location_dest_id = data.location_revert_id.id
        else:
            location_dest_id = data.location_src_id.id
        res = move_obj.onchange_product_id(cr, uid, ids, data.product_id.id, data.location_src_id.id, location_dest_id, False)
        uos_id = data.product_id.uos_id and data.product_id.uos_id.id or False
        type_interne = self.pool.get('stock.picking.type').search(cr, uid, [('code','=','internal')], context=context)                    
            
        vals = {
            'product_id': data.product_id.id,
            'product_uom_qty': data.product_qty,
            'name': res['value']['name'],
            'product_uom': res['value']['product_uom'],
            'product_uos': res['value']['product_uos'],
            'product_uom_qty': data.product_qty,
            'product_uos_qty': self.pool.get('stock.move').onchange_quantity(cr, uid, ids, data.product_id.id, data.product_qty, data.product_id.uom_id.id, uos_id)['value']['product_uos_qty'],               
            'location_id': data.location_src_id.id,
            'location_dest_id': location_dest_id,
            'date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'planned_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'picking_type_id': type_interne and type_interne[0],
            'restrict_lot_id': data.restrict_lot_id.id,
        }
        new_id = move_obj.create(cr, uid, vals, context=context)
        return new_id 
    
    def validate_scrap(self, cr, uid, ids, context=None):
        move_obj = self.pool.get('stock.move')
        if context is None:
            context = {}
        data = self.browse(cr, uid, ids[0])
        action_model = False
        data_pool = self.pool.get('ir.model.data')
        action = {}

        if data:
            move_id = self.create_stock_move(cr, uid, ids, data, context=context)
            if data.operation in ('bloque', 'debloque', 'change_location'):
                """ Mise au rebut des lots en stock """
                move_obj.action_scrap(cr, uid, [move_id],
                                      data.product_qty, data.location_rebut_id.id, data.restrict_lot_id.id, context=context)
                # supprimer le mouvement brouillon créé
                move_obj.unlink(cr, uid, [move_id], context=context)
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
            elif data.operation == 'rebut':
                """ Remettre au stock les lots au rebut """
                move_obj.action_done(cr, uid, [move_id], context=context)       
                action_model,action_id = data_pool.get_object_reference(cr, uid, 'is_plastigray', "action_stock_lot_rebut_report")
                action_pool = self.pool.get(action_model)
                action = action_pool.read(cr, uid, action_id, context=context)
                return action

is_stock_mise_rebut()
    
    
    
