# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_ligne_reception(models.Model):
    _name='is.ligne.reception'
    _order='picking_id desc'
    _auto = False

    picking_id         = fields.Many2one('stock.picking', 'Réception')
    order_id           = fields.Many2one('purchase.order', 'Commande')
    partner_id         = fields.Many2one('res.partner', 'Fournisseur')
    product_id         = fields.Many2one('product.template', 'Article')
    ref_fournisseur    = fields.Char('Référence fournisseur')
    commande_ouverte   = fields.Char('Commande ouverte')
    product_uom_qty    = fields.Float('Quantité')
    product_uom        = fields.Many2one('product.uom', 'Unité')
    date_planned       = fields.Date('Date prévue')
    state              = fields.Selection([
        ('draft'    , u'Nouveau'),
        ('cancel'   , u'Annulé'),
        ('waiting'  , u'En attente'),
        ('confirmed', u'Confirmé'),
        ('assigned' , u'Disponible'),
        ('done'     , u'Terminé')], u"État", readonly=True, select=True)

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_ligne_reception')
        cr.execute("""
            CREATE OR REPLACE view is_ligne_reception AS (
                select  sm.id,
                        sp.id                 as picking_id, 
                        po.id                 as order_id,  
                        sp.partner_id         as partner_id, 
                        pt.id                 as product_id, 
                        pt.is_ref_fournisseur as ref_fournisseur,
                        sm.product_uom_qty,
                        sm.product_uom,
                        pol.date_planned,
                        sm.state,
                        (select icof.name from is_cde_ouverte_fournisseur icof where sp.partner_id=icof.partner_id limit 1) as commande_ouverte 
                from stock_picking sp inner join stock_move                sm on sm.picking_id=sp.id 
                                      inner join product_product           pp on sm.product_id=pp.id
                                      inner join product_template          pt on pp.product_tmpl_id=pt.id
                                      left outer join purchase_order       po on sp.is_purchase_order_id=po.id
                                      left outer join purchase_order_line pol on sm.purchase_line_id=pol.id

                where sp.picking_type_id=1
            )
        """)
