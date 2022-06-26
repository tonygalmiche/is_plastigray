# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _
import datetime
import pytz


_SELECT_STOCK_MOVE="""
    select 
            row_number() over(order by sm.id )  as id,
            sm.id                               as move_id,
            sm2.date                            as date,
            sm2.product_id                      as product_id, 
            ic.name                             as category,
            COALESCE(im.name,id.name)           as mold,
            COALESCE(spt.name,sm.src)           as type_mv,
            COALESCE(spt.name,sp.name,sm2.name) as name,
            sm2.picking_id                      as picking_id,
            sm2.purchase_line_id,
            sm2.raw_material_production_id,
            sm2.production_id,
            sm2.is_sale_line_id,
            sm.lot_id                          as lot_id,
            spl.is_lot_fournisseur             as lot_fournisseur,
            sm.qty                             as qty,
            pt.uom_id                          as product_uom,
            sm.dest                            as location_dest,
            sm2.is_employee_theia_id	   as is_employee_theia_id,
            rp.name                            as login
    from (

        select 
            sm.id,
            sq.lot_id           as lot_id,
            sum(sq.qty)         as qty,
            sl1.name            as src,
            sl2.name            as dest
        from stock_move sm inner join stock_location        sl1 on sm.location_id=sl1.id
                            inner join stock_location        sl2 on sm.location_dest_id=sl2.id
                            left outer join stock_quant_move_rel sqmr on sm.id=sqmr.move_id
                            left outer join stock_quant            sq on sqmr.quant_id=sq.id
        where sm.state='done' and sl2.usage='internal' 
        group by 
            sm.id,
            sq.lot_id,
            sl1.name,
            sl2.name

        union

        select 
            sm.id,
            sq.lot_id           as lot_id,
            -sum(sq.qty)        as qty,
            sl1.name            as dest,
            sl2.name            as src
        from stock_move sm inner join stock_location        sl1 on sm.location_dest_id=sl1.id
                            inner join stock_location        sl2 on sm.location_id=sl2.id
                            left outer join stock_quant_move_rel sqmr on sm.id=sqmr.move_id
                            left outer join stock_quant            sq on sqmr.quant_id=sq.id
        where sm.state='done' and sl2.usage='internal' 
        group by 
            sm.id,
            sq.lot_id,
            sl1.name,
            sl2.name

    ) sm    inner join stock_move                sm2 on sm.id=sm2.id           
            inner join product_product            pp on sm2.product_id=pp.id
            inner join product_template           pt on pp.product_tmpl_id=pt.id
            inner join res_users                  ru on sm2.write_uid=ru.id
            inner join res_partner                rp on ru.partner_id=rp.id
            left outer join stock_picking_type   spt on sm2.picking_type_id=spt.id
            left outer join stock_picking         sp on sm2.picking_id=sp.id
            left outer join is_category           ic on pt.is_category_id=ic.id
            left outer join is_mold               im on pt.is_mold_id=im.id
            left outer join is_dossierf           id on pt.is_dossierf_id=id.id
            left outer join stock_production_lot spl on sm.lot_id=spl.id
"""
#    order by sm2.date desc, sm2.id




class pg_stock_move(models.Model):
    _name='pg.stock.move'
    _order='date desc'

    move_id            = fields.Many2one('stock.move', 'Mouvement'   , select=True)
    date               = fields.Datetime('Date'                      , select=True)
    product_id         = fields.Many2one('product.product', 'Article', select=True)
    category           = fields.Char('Cat'                           , select=True)
    mold               = fields.Char('Moule / DossierF'              , select=True)
    type_mv            = fields.Char('Type'                          , select=True)
    name               = fields.Char('Description')
    picking_id         = fields.Many2one('stock.picking', 'Rcp/Liv')
    lot_id             = fields.Many2one('stock.production.lot', 'Lot')
    lot_fournisseur    = fields.Char('Lot fournisseur')
    qty                = fields.Float('Quantité')
    product_uom        = fields.Many2one('product.uom', 'Unité')
    location_dest      = fields.Char("Lieu"                          , select=True)
    login              = fields.Char('Utilisateur')
    is_employee_theia_id       = fields.Many2one('hr.employee', 'Employé Theia')
    purchase_line_id           = fields.Many2one('purchase.order.line', 'Ligne commande achat')
    raw_material_production_id = fields.Many2one('mrp.production'     , 'Composant ordre de fabrication')
    production_id              = fields.Many2one('mrp.production'     , 'Ordre de fabrication')
    is_sale_line_id            = fields.Many2one('sale.order.line'    , 'Ligne commande vente')


class is_stock_move(models.Model):
    _name='is.stock.move'
    _order='date desc'
    _auto = False

    move_id            = fields.Many2one('stock.move', 'Mouvement')
    date               = fields.Datetime('Date')
    product_id         = fields.Many2one('product.product', 'Article')
    category           = fields.Char('Cat')
    mold               = fields.Char('Moule / DossierF')
    type_mv            = fields.Char('Type')
    name               = fields.Char('Description')
    picking_id         = fields.Many2one('stock.picking', 'Rcp/Liv')
    lot_id             = fields.Many2one('stock.production.lot', 'Lot')
    lot_fournisseur    = fields.Char('Lot fournisseur')
    qty                = fields.Float('Quantité')
    product_uom        = fields.Many2one('product.uom', 'Unité')
    location_dest      = fields.Char("Lieu")
    login              = fields.Char('Utilisateur')
    is_employee_theia_id  = fields.Many2one('hr.employee', 'Employé Theia')

    purchase_line_id           = fields.Many2one('purchase.order.line', 'Ligne commande achat')
    raw_material_production_id = fields.Many2one('mrp.production'     , 'Composant ordre de fabrication')
    production_id              = fields.Many2one('mrp.production'     , 'Ordre de fabrication')
    is_sale_line_id            = fields.Many2one('sale.order.line'    , 'Ligne commande vente')


    @api.multi
    def refresh_stock_move_action(self):
        cr = self._cr
        cr.execute("REFRESH MATERIALIZED VIEW is_stock_move;")

        now = datetime.datetime.now(pytz.timezone('Europe/Paris')).strftime('%H:%M:%S')
        return {
            'name': u'Mouvements de stocks actualisés à '+str(now),
            'view_mode': 'tree,form',
            'view_type': 'form',
            'res_model': 'is.stock.move',
            'type': 'ir.actions.act_window',
        }


    def init(self, cr):
        cr.execute("""
            DROP MATERIALIZED VIEW IF EXISTS is_stock_move;
            CREATE MATERIALIZED view is_stock_move AS ("""+_SELECT_STOCK_MOVE+"""
            );
        """)



