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
        data.update({'is_sale_line_id'    : procurement.sale_line_id and procurement.sale_line_id.id})
        data.update({'location_id'        : procurement.sale_line_id and procurement.sale_line_id.order_id.is_source_location_id.id})
        return data

