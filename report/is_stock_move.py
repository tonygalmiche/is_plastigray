# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_stock_move(models.Model):
    _name='is.stock.move'
    _order='date desc'
    _auto = False

    move_id            = fields.Many2one('stock.move', 'Mouvement')
    date               = fields.Datetime('Date')
    product_id         = fields.Many2one('product.product', 'Article')
    category           = fields.Char('Cat')
    mold               = fields.Char('Moule')
    type_mv            = fields.Char('Type')
    name               = fields.Char('Description')
    picking_id         = fields.Many2one('stock.picking', 'Rcp/Liv')
    qty                = fields.Float('Quantité')
    product_uom        = fields.Many2one('product.uom', 'Unité')
    location_dest      = fields.Char("Lieu")
    login              = fields.Char('Login')


    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_stock_move')
        cr.execute("""
            CREATE OR REPLACE view is_stock_move AS (

                select 
                        row_number() over(order by sm.id ) as id,
                        sm.id                              as move_id,
                        sm.write_date                      as date,
                        sm.product_id                      as product_id, 
                        ic.name                            as category,
                        im.name                            as mold,
                        COALESCE(spt.name,sm.src)          as type_mv,
                        COALESCE(spt.name,sp.name,sm.name) as name,
                        sm.picking_id                      as picking_id,
                        sm.product_uom_qty                 as qty,
                        sm.product_uom                     as product_uom,
                        sm.dest                            as location_dest,
                        ru.login                           as login 
                from (

                    select 
                        sm.id,
                        sm.date,
                        sm.product_id, 
                        sm.picking_type_id,
                        sm.picking_id,
                        sm.name,
                        sm.origin,
                        sm.product_uom_qty,
                        sm.product_uom,
                        sl1.name            as src,
                        sl2.name            as dest,
                        sm.write_date,
                        sm.write_uid 
                    from stock_move sm inner join stock_location sl1 on sm.location_id=sl1.id
                                       inner join stock_location sl2 on sm.location_dest_id=sl2.id
                    where sm.state='done' and sl2.usage='internal' 

                    union

                    select 
                        sm.id,
                        sm.date,
                        sm.product_id, 
                        sm.picking_type_id,
                        sm.picking_id,
                        sm.name,
                        sm.origin,
                        -sm.product_uom_qty,
                        sm.product_uom,
                        sl1.name            as dest,
                        sl2.name            as src,
                        sm.write_date,
                        sm.write_uid 
                    from stock_move sm inner join stock_location sl1 on sm.location_dest_id=sl1.id
                                       inner join stock_location sl2 on sm.location_id=sl2.id
                    where sm.state='done' and sl2.usage='internal' 
                ) as sm inner join product_product           pp on sm.product_id=pp.id
                        inner join product_template          pt on pp.product_tmpl_id=pt.id
                        inner join res_users                 ru on sm.write_uid=ru.id
                        left outer join stock_picking_type  spt on sm.picking_type_id=spt.id
                        left outer join stock_picking        sp on sm.picking_id=sp.id
                        left outer join is_category          ic on pt.is_category_id=ic.id
                        left outer join is_mold              im on pt.is_mold_id=im.id
                order by sm.date desc, sm.id
            )
        """)



