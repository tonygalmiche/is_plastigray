# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_ligne_reception(models.Model):
    _name='is.ligne.reception'
    _order='date_mouvement desc'
    _auto = False

    picking_id         = fields.Many2one('stock.picking', 'Réception')
    num_bl             = fields.Char('N°BL fournisseur')
    order_id           = fields.Many2one('purchase.order', 'Commande')
    partner_id         = fields.Many2one('res.partner', 'Fournisseur')

    is_demandeur_id      = fields.Many2one('res.users', 'Demandeur')
    is_date_confirmation = fields.Date('Date de confirmation')
    is_commentaire       = fields.Text('Commentaire')

    product_id         = fields.Many2one('product.template', 'Article')
    ref_fournisseur    = fields.Char('Référence fournisseur')
    commande_ouverte   = fields.Char('Commande ouverte')
    product_uom        = fields.Many2one('product.uom', 'Unité')
    qt_receptionnee    = fields.Float('Quantité réceptionnée', digits=(14,4))
    qt_facturee        = fields.Float('Quantité facturée'    , digits=(14,4))
    reste_a_facturer   = fields.Float('Reste à facturer'     , digits=(14,4))
    date_planned       = fields.Date('Date prévue')
    date_reception     = fields.Date('Date réception')
    date_mouvement     = fields.Datetime('Date mouvement')
    lot_fournisseur    = fields.Char('Lot fournisseur')
    user_id            = fields.Many2one('res.users', 'Utilisateur')
    move_id            = fields.Many2one('stock.move', 'Mouvement de stock')
    picking_state      = fields.Selection([
        ('draft'               , u'Brouillon'),
        ('cancel'              , u'Annulé'),
        ('waiting'             , u'En attente'),
        ('confirmed'           , u'En attente'),
        ('assigned'            , u'Prêt à transférer'),
        ('partially_availlable', u'Partiellement disponible'),
        ('done'                , u'Transféré'),
    ], u"État réception", readonly=True, select=True)
    state              = fields.Selection([
        ('draft'    , u'Nouveau'),
        ('cancel'   , u'Annulé'),
        ('waiting'  , u'En attente'),
        ('confirmed', u'Confirmé'),
        ('assigned' , u'Disponible'),
        ('done'     , u'Terminé')
    ], u"État Mouvement", readonly=True, select=True)

    invoice_state = fields.Selection([
        ('2binvoiced', u'à Facturer'),
        ('none'      , u'Annulé'),
        ('invoiced'  , u'Facturé'),
    ], u"État facturation", readonly=True, select=True)


    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_ligne_reception')
        cr.execute("""
            CREATE OR REPLACE view is_ligne_reception AS (
                select  sm.id,
                        pol.date_planned,
                        sp.id                 as picking_id, 
                        sp.is_num_bl          as num_bl,
                        sp.is_date_reception  as date_reception,
                        sm.date               as date_mouvement,
                        po.id                 as order_id,  
                        sp.partner_id         as partner_id, 
                        po.is_demandeur_id       as is_demandeur_id,
                        po.is_date_confirmation  as is_date_confirmation,
                        po.is_commentaire        as is_commentaire,
                        pt.id                 as product_id, 
                        pt.is_ref_fournisseur as ref_fournisseur,
                        sm.product_uom        as product_uom,
                        sm.product_uom_qty    as qt_receptionnee,
                        coalesce((select sum(quantity) from account_invoice_line ail where ail.is_move_id=sm.id ),0) as qt_facturee,
                        round(sm.product_uom_qty-coalesce((select sum(quantity) from account_invoice_line ail where ail.is_move_id=sm.id ),0),4) as reste_a_facturer,
                        sm.state              as state,
                        sp.state              as picking_state,
                        sp.invoice_state      as invoice_state,
                        sm.write_uid          as user_id,
                        sm.id                 as move_id,
                        (select icof.name from is_cde_ouverte_fournisseur icof where sp.partner_id=icof.partner_id limit 1) as commande_ouverte,
                        (select is_lot_fournisseur from stock_production_lot spl where spl.name=sp.name and spl.product_id=pp.id limit 1) as lot_fournisseur
                from stock_picking sp inner join stock_move                sm on sm.picking_id=sp.id 
                                      inner join product_product           pp on sm.product_id=pp.id
                                      inner join product_template          pt on pp.product_tmpl_id=pt.id
                                      left outer join purchase_order       po on sp.is_purchase_order_id=po.id
                                      left outer join purchase_order_line pol on sm.purchase_line_id=pol.id
                where sp.picking_type_id=1
            )
        """)



