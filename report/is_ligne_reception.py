# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_ligne_reception(models.Model):
    _name='is.ligne.reception'
    _order='date_mouvement desc'
    _auto = False

    picking_id           = fields.Many2one('stock.picking', 'Réception')
    num_bl               = fields.Char('N°BL fournisseur')
    order_id             = fields.Many2one('purchase.order', 'Commande')
    is_cfc_id            = fields.Many2one('is.cde.ferme.cadencee', 'Cde ferme cadencée')
    order_line_id        = fields.Many2one('purchase.order.line', 'Ligne de Commande')
    partner_id           = fields.Many2one('res.partner', 'Fournisseur')
    is_demandeur_id      = fields.Many2one('res.users', 'Demandeur')
    is_date_confirmation = fields.Date('Date de confirmation')
    is_commentaire       = fields.Text('Commentaire')
    product_id           = fields.Many2one('product.template', 'Article')
    description          = fields.Char('Description')
    segment_id           = fields.Many2one('is.product.segment', 'Segment', readonly=True)
    is_ctrl_rcp          = fields.Selection([('bloque','Produit bloqué'),('aqp','AQP')], "Contrôle réception")
    is_facturable        = fields.Boolean('Article facturable')
    ref_fournisseur      = fields.Char('Référence fournisseur')
    commande_ouverte     = fields.Char('Commande ouverte')
    product_uom          = fields.Many2one('product.uom', 'Unité')
    price_unit           = fields.Float('Prix commande'             , digits=(14,4))
    qt_receptionnee      = fields.Float('Quantité réceptionnée'     , digits=(14,4))
    qt_facturee          = fields.Float('Quantité facturée'         , digits=(14,4))
    reste_a_facturer     = fields.Float('Reste à facturer'          , digits=(14,4))
    montant_reception    = fields.Float('Montant réception'         , digits=(14,2))
    montant_reste        = fields.Float('Montant reste à facturer'  , digits=(14,2))
    date_planned         = fields.Date('Date prévue')
    date_reception       = fields.Date('Date réception')
    date_mouvement       = fields.Datetime('Date mouvement')
    lot_fournisseur      = fields.Char('Lot fournisseur')
    is_dosmat_ctrl_qual  = fields.Char('Contrôle qualité Dynacase')
    is_dosmat_conditions_stockage = fields.Char(u'Conditions de stockage')
    user_id              = fields.Many2one('res.users', 'Utilisateur')
    move_id              = fields.Many2one('stock.move', 'Mouvement de stock')
    picking_state        = fields.Selection([
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

    is_piece_jointe = fields.Boolean(u"Pièce jointe", store=False, readonly=True, compute='_compute_is_piece_jointe')


    @api.multi
    def pj_action(self):
        for obj in self:
            print obj

    def _compute_is_piece_jointe(self):
        for obj in self:
            attachments = self.env['ir.attachment'].search([('res_model','=','stock.picking'),('res_id','=',obj.picking_id.id)])
            pj=False
            if attachments:
                pj=True
            obj.is_piece_jointe=pj


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
                        po.is_cfc_id          as is_cfc_id,
                        pol.id                as order_line_id,
                        pol.price_unit        as price_unit,
                        pol.price_unit*sm.product_uom_qty as montant_reception,
                        sp.partner_id            as partner_id, 
                        po.is_demandeur_id       as is_demandeur_id,
                        po.is_date_confirmation  as is_date_confirmation,
                        po.is_commentaire        as is_commentaire,
                        pt.id                    as product_id,
                        sm.name                  as description,
                        pt.segment_id            as segment_id,
                        pt.is_ctrl_rcp           as is_ctrl_rcp,
                        pt.is_facturable         as is_facturable,
                        pt.is_ref_fournisseur    as ref_fournisseur,
                        sm.product_uom           as product_uom,
                        sm.product_uom_qty       as qt_receptionnee,
                        coalesce((select sum(quantity) from account_invoice_line ail where ail.is_move_id=sm.id ),0) as qt_facturee,
                        round(sm.product_uom_qty-coalesce((select sum(quantity) from account_invoice_line ail where ail.is_move_id=sm.id ),0),4) as reste_a_facturer,
                        round(sm.product_uom_qty-coalesce((select sum(quantity) from account_invoice_line ail where ail.is_move_id=sm.id ),0),4)*pol.price_unit as montant_reste,
                        sm.state              as state,
                        sp.state              as picking_state,
                        sm.invoice_state      as invoice_state,
                        sm.write_uid          as user_id,
                        sm.id                 as move_id,
                        sm.is_dosmat_ctrl_qual as is_dosmat_ctrl_qual,
                        sm.is_dosmat_conditions_stockage as is_dosmat_conditions_stockage,
                        (select icof.name from is_cde_ouverte_fournisseur icof where sp.partner_id=icof.partner_id limit 1) as commande_ouverte,
                        (
                            select spl.is_lot_fournisseur 
                            from stock_quant_move_rel sqmr inner join stock_quant           sq on sqmr.quant_id=sq.id
                                                           inner join stock_production_lot spl on sq.lot_id = spl.id
                            where sqmr.move_id=sm.id limit 1
                        )  as lot_fournisseur
                from stock_picking sp inner join stock_move                sm on sm.picking_id=sp.id 
                                      inner join product_product           pp on sm.product_id=pp.id
                                      inner join product_template          pt on pp.product_tmpl_id=pt.id
                                      left outer join purchase_order       po on sp.is_purchase_order_id=po.id
                                      left outer join purchase_order_line pol on sm.purchase_line_id=pol.id
                where sp.picking_type_id=1
            )
        """)

