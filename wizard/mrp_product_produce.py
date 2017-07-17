# -*- coding: utf-8 -*-

from openerp.exceptions import except_orm
from openerp import models, fields, api, _
from openerp.exceptions import Warning



class mrp_product_produce_line(models.TransientModel):
    _inherit="mrp.product.produce.line"

    is_sequence = fields.Integer('Sequence')


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

    
    finished_products_location_id = fields.Many2one(
        'stock.location', 
        string="Emplacement des produits finis", 
        domain="['|','&',('usage','=','internal'),('usage','!=','view'),('scrap_location','=',True)]", 
        default=_get_default_finished_pro_location
    )



    product_package = fields.Many2one('product.ul', default=_get_default_package, string="Conditionnement (UC)")
    package_qty = fields.Float(string='Quantité par UC', default=_get_default_package_qty)
    product_package_qty = fields.Float(string="Nombre d'UC à déclarer", default=_get_default_product_package_qty)

    
#    @api.v7
#    def on_change_qty(self, cr, uid, ids, product_qty, consume_lines, context=None):
#        context = dict(context or {})
#        prod_obj = self.pool.get("mrp.production")
#        production = prod_obj.browse(cr, uid, context['active_id'], context=context)
#        ret_val = super(mrp_product_produce, self).on_change_qty(cr, uid, ids, product_qty, consume_lines, context=context)
#        new_consume_lines = []
#        inverse=False
#        if product_qty<0:
#            product_qty=-product_qty
#            inverse=True

#        context.update({'is_custom_compute':True,'qty_to_compute':product_qty})
#        lines = prod_obj._prepare_lines(cr, uid, production, properties=None, context=context)[0]
#        sequence=0
#        for line in lines:
#            sequence=sequence+1
#            qty=line.get('product_qty',0.0)
#            if inverse:
#                qty=-qty
#            new_consume_lines.append([0, False, {
#                'is_sequence'   : sequence,
#                'lot_id'     : False, 
#                'product_id' : line.get('product_id',False),
#                'product_qty': qty
#            }])
#        ret_val['value'].update({'consume_lines': new_consume_lines})
#        if inverse:
#            product_qty=-product_qty
#        if production.package_qty > 0:
#            product_package_qty = product_qty / production.package_qty
#            ret_val['value'].update({'product_package_qty': product_package_qty})
#        return ret_val
    


    @api.multi
    def on_change_qty(self, product_qty, consume_lines):
        cr, uid, context = self.env.args
        prod_obj=self.env["mrp.production"]
        production = prod_obj.browse(context['active_id'])
        ret_val={}
        new_consume_lines = []
        sequence=0
        for line in production.product_lines:
            lot_id=False
            #** Recherche du lot utilisé dans le dernier mouvement *************
            if product_qty<0:
                SQL="""
                    select sq.lot_id
                    from stock_move sm inner join stock_quant_move_rel sqmr on sm.id=sqmr.move_id 
                                       inner join stock_quant            sq on sqmr.quant_id=sq.id
                    where 
                        sm.product_id="""+str(line.product_id.id)+""" and 
                        sm.raw_material_production_id="""+str(production.id)+""" and 
                        sm.state='done' and sq.lot_id is not null
                    order by sm.id desc limit 1
                """
                cr.execute(SQL)
                result = cr.fetchall()
                for row in result:
                    lot_id=row[0]
            #*******************************************************************

            sequence=sequence+1
            new_consume_lines.append([0, False, {
                'is_sequence'   : sequence,
                'lot_id'     : lot_id, 
                'product_id' : line.product_id.id,
                'product_qty': line.is_bom_qty*product_qty
            }])
        ret_val['value']={'consume_lines': new_consume_lines}
        return ret_val


    @api.onchange('product_package_qty')
    def on_change_product_package_qty(self):
        if self.package_qty > 0:
            self.product_qty = self.product_package_qty * self.package_qty


    @api.one
    def do_produce(self):
        cr, uid, context = self.env.args
        production_id = context.get('active_id', False)
        if self.product_qty==0:
            raise Warning(u'Quantité à 0 non autorisée !')
        mrp_product_obj = self.env['mrp.production']
        mrp_product_obj.action_produce(production_id,self.product_qty, self.mode, self)
        return {}




