# -*- coding: utf-8 -*-

from openerp.exceptions import except_orm
from openerp import models, fields, api, _

class mrp_product_produce(models.TransientModel):
    _inherit = "mrp.product.produce"


    @api.v7
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


    @api.model
    def _get_default_package(self):
        cr, uid, context = self.env.args
        prod = self.env['mrp.production'].browse(context.get('active_id',False))
        res=False
        if prod:
            res = prod.product_package
        return res


    @api.model
    def _get_default_package_qty(self):
        cr, uid, context = self.env.args
        prod = self.env['mrp.production'].browse(context.get('active_id',False))
        res=False
        if prod:
            res=prod.package_qty
        return res
        

    @api.model
    def _get_default_product_package_qty(self):
        return 0
        

    @api.model
    def _get_default_finished_pro_location(self):
        cr, uid, context = self.env.args
        prod = self.env['mrp.production'].browse(context.get('active_id',False))
        res=False
        if prod:
            res=prod.location_dest_id
        return res

    
    finished_products_location_id = fields.Many2one('stock.location', string="Emplacement des produits finis", domain="[('usage','=','internal')]", default=_get_default_finished_pro_location)
    product_package = fields.Many2one('product.ul', default=_get_default_package, string="Conditionnement (UC)")
    package_qty = fields.Float(string='Quantité par UC', default=_get_default_package_qty)
    product_package_qty = fields.Float(string="Nombre d'UC à déclarer", default=_get_default_product_package_qty)

    
    @api.v7
    def on_change_qty(self, cr, uid, ids, product_qty, consume_lines, context=None):

        return

        context = dict(context or {})
        prod_obj = self.pool.get("mrp.production")
        production = prod_obj.browse(cr, uid, context['active_id'], context=context)
        
#         if product_qty > production.product_qty and context.get('is_product_package_qty',False) == False:
#             raise except_orm('Warning','Please enter valid product quantity.')
        ret_val = super(mrp_product_produce, self).on_change_qty(cr, uid, ids, product_qty, consume_lines, context=context)
        new_consume_lines = []
        if product_qty > 0:
            context.update({'is_custom_compute':True,'qty_to_compute':product_qty})
            lines = prod_obj._prepare_lines(cr, uid, production, properties=None, context=context)[0]
            for line in lines:
                new_consume_lines.append([0, False, {'lot_id': False, 
                                                     'product_id': line.get('product_id',False),
                                                     'product_qty': line.get('product_qty',0.0)
                                                     }
                                          ])
            ret_val['value'].update({'consume_lines': new_consume_lines})
        if production.package_qty > 0:
            product_package_qty = product_qty / production.package_qty
            ret_val['value'].update({'product_package_qty': product_package_qty})
        return ret_val
    


    @api.onchange('product_package_qty')
    def on_change_product_package_qty(self):
        if self.package_qty > 0:
            self.product_qty = self.product_package_qty * self.package_qty


    @api.one
    def do_produce(self):
        cr, uid, context = self.env.args
        production_id = context.get('active_id', False)
        assert production_id, "Production Id should be specified in context as a Active ID."
        mrp_product_obj = self.env['mrp.production']
        stock_move_obj = self.env["stock.move"]
        production_brw = mrp_product_obj.browse(production_id)
        location_dest_id=production_brw.location_dest_id.id
        if self.finished_products_location_id:
            

            production_brw.location_dest_id = self.finished_products_location_id
            move_ids = stock_move_obj.search([('production_id','=', production_id),('state','!=', 'done')])
            for move in move_ids:
                move.location_dest_id = self.finished_products_location_id
        mrp_product_obj.action_produce(production_id,self.product_qty, self.mode, self)
        production_brw.location_dest_id = location_dest_id
        return {}


