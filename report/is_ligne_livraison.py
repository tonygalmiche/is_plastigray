# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_ligne_livraison(models.Model):
    _name='is.ligne.livraison'
    _order='date_mouvement desc'
    _auto = False

    picking_id         = fields.Many2one('stock.picking', 'Livraison')
    order_id           = fields.Many2one('sale.order', 'Commande')
    client_order_ref   = fields.Char('Commande Client')
    partner_id         = fields.Many2one('res.partner', 'Client')
    product_id         = fields.Many2one('product.template', 'Article')
    ref_client         = fields.Char('Référence client')
    mold_id            = fields.Many2one('is.mold', 'Moule')
    product_uom_qty    = fields.Float('Quantité livrée', digits=(14,2))
    product_uom        = fields.Many2one('product.uom', 'Unité')
    date_expedition    = fields.Date("Date d'expédition")
    date_livraison     = fields.Date("Date d'arrivée chez le client")
    date_mouvement     = fields.Datetime('Date mouvement')
    user_id            = fields.Many2one('res.users', 'Utilisateur')
    move_id            = fields.Many2one('stock.move', 'Mouvement de stock')
    state              = fields.Selection([
        ('draft'    , u'Nouveau'),
        ('cancel'   , u'Annulé'),
        ('waiting'  , u'En attente'),
        ('confirmed', u'Confirmé'),
        ('assigned' , u'Disponible'),
        ('done'     , u'Terminé')], u"État", readonly=True, select=True)

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_ligne_livraison')
        cr.execute("""
            CREATE OR REPLACE view is_ligne_livraison AS (
                select  sm.id,
                        sp.id                   as picking_id, 
                        sp.is_date_expedition   as date_expedition,
                        sp.is_date_livraison    as date_livraison,
                        sm.date                 as date_mouvement,
                        sol.is_client_order_ref as client_order_ref,
                        so.id                   as order_id,  
                        sp.partner_id           as partner_id, 
                        pt.id                   as product_id, 
                        pt.is_mold_id           as mold_id,
                        pt.is_ref_client        as ref_client,
                        sm.product_uom_qty,
                        sm.product_uom,
                        sm.state,
                        sm.write_uid          as user_id,
                        sm.id                 as move_id
                from stock_picking sp inner join stock_move                sm on sm.picking_id=sp.id 
                                      inner join product_product           pp on sm.product_id=pp.id
                                      inner join product_template          pt on pp.product_tmpl_id=pt.id
                                      left outer join sale_order           so on sp.is_sale_order_id=so.id
                                      left outer join sale_order_line     sol on sm.is_sale_line_id=sol.id


                where sp.picking_type_id=2 and sm.state='done' and so.id is not null
            )
        """)

