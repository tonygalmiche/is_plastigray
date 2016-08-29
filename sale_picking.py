#-*- coding:utf-8 -*-

from openerp import models, fields, api, _
from openerp.tools import frozendict

 
class stock_move(models.Model):
    _inherit = 'stock.move'
     
    is_sale_line_id = fields.Many2one('sale.order.line', 'Ligne de commande')

    
class procurement_order(models.Model):
    _inherit = "procurement.order"
    
    @api.v7
    def _run_move_create(self, cr, uid, procurement, context=None):
        data = super(procurement_order,self)._run_move_create(cr, uid, procurement, context=context)
        
        data.update({'is_sale_line_id':procurement.sale_line_id and procurement.sale_line_id.id})
        data.update({'location_id':procurement.sale_line_id and procurement.sale_line_id.order_id.is_source_location_id.id})
        return data
        
        
class sale_order(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _get_default_location(self):
        
        company_id = self.env.user.company_id.id
        warehouse_obj = self.env['stock.warehouse']
        warehouse_id = warehouse_obj.search([('company_id','=',company_id)])
        location = warehouse_id.out_type_id and  warehouse_id.out_type_id.default_location_src_id
        return location and location or False
        
    is_source_location_id = fields.Many2one('stock.location', 'Source Location', default=_get_default_location) 
    
     
class stock_picking(models.Model):
    _inherit = "stock.picking"
    
    location_id = fields.Many2one(realted='move_lines.location_id', relation='stock.location', string='Location', readonly=False)
    
    @api.onchange('location_id')
    def onchange_location(self):
        for move in self.move_lines:
            move.location_id = self.location_id

