# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_mouvement_stock(models.Model):
    _name='is.mouvement.stock'
    _order='date desc'
    _auto = False

    product_id         = fields.Many2one('product.product', 'Article')
    quant_qty          = fields.Float('Quantité')
    move_qty           = fields.Float('Quantité réservée')
    product_uom        = fields.Many2one('product.uom', 'Unité')
    location_id        = fields.Many2one('stock.location', "Source")
    location_dest_id   = fields.Many2one('stock.location', "Destination")
    date               = fields.Datetime('Date')
    origin             = fields.Char('Origine')
    description        = fields.Char('Description')
    lot_id             = fields.Many2one('stock.production.lot', "Lot")
    move_id            = fields.Many2one('stock.move', "Mouvement")
    quant_id           = fields.Many2one('stock.quant', "Quant")
    createur           = fields.Many2one('res.users', "Créé par")


    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_mouvement_stock')
        cr.execute("""
            CREATE OR REPLACE view is_mouvement_stock AS (
                select  row_number() over(order by sm.date desc, sm.id) as id,
                        sm.product_id, 
                        sq.qty as quant_qty, 
                        sm.product_uom_qty as move_qty, 
                        sm.product_uom, 
                        sm.location_id, 
                        sm.location_dest_id, 
                        sm.date, sm.name, 
                        sm.origin, 
                        sm.name as description, 
                        sq.lot_id, 
                        sm.id as move_id,
                        sqmr.quant_id,
                        sq.create_uid createur
                from stock_move  sm left outer join stock_quant_move_rel sqmr on sm.id=sqmr.move_id
                                    left outer join stock_quant            sq on sqmr.quant_id=sq.id
            )
        """)

#                from stock_quant_move_rel sqmr inner join stock_move  sm on sqmr.move_id=sm.id

#                                               inner join stock_quant sq on sqmr.quant_id=sq.id




