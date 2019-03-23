# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _
import datetime
import pytz



class is_purchase_order_line(models.Model):
    _name='is.purchase.order.line'
    _order='id desc'
    _auto = False

    order_line_id        = fields.Many2one('purchase.order.line', 'Ligne de commande')
    order_id             = fields.Many2one('purchase.order', 'Commande')
    is_cfc_id            = fields.Many2one('is.cde.ferme.cadencee', 'Cde ferme cadencée')
    partner_id           = fields.Many2one('res.partner', 'Fournisseur')
    date_order           = fields.Date('Date de commande')
    minimum_planned_date = fields.Date('Date prévue entête')
    is_date_confirmation = fields.Date('Date de confirmation')
    is_commentaire       = fields.Text('Commentaire')
    product_id           = fields.Many2one('product.template', 'Article')
    is_ref_fournisseur   = fields.Char('Référence fournisseur')
    date_planned         = fields.Date('Date prévue ligne')
    product_qty          = fields.Float('Quantité Cde', digits=(14,4))
    product_uom          = fields.Many2one('product.uom', 'Unité Cde')
    price_unit           = fields.Float('Prix unitaire Cde')
    is_justification     = fields.Char('Justifcation')
    is_num_da            = fields.Char("N°Demande d'achat")
    is_document          = fields.Char("Document (N° de dossier)")
    is_num_chantier      = fields.Char("N° du chantier")
    is_demandeur_id      = fields.Many2one('res.users', 'Demandeur')

    uom_po_id            = fields.Many2one('product.uom', "Unité d'achat")
    price_unit_uom_po    = fields.Float('Prix unitaire (UA)')
    product_qty_uom_po   = fields.Float('Qt Cde (UA)'  , digits=(14,3))
    qt_rcp               = fields.Float('Qt Rcp (UA)'  , digits=(14,3))
    qt_reste             = fields.Float('Qt Reste (UA)', digits=(14,3))
    commande_ouverte     = fields.Char('Commande ouverte')


    @api.multi
    def refresh_purchase_order_line_action(self):
        cr = self._cr
        cr.execute("REFRESH MATERIALIZED VIEW is_purchase_order_line;")
        now = datetime.datetime.now(pytz.timezone('Europe/Paris')).strftime('%H:%M:%S')
        return {
            'name': u'Lignes des commandes actualisées à '+str(now),
            'view_mode': 'tree,form',
            'view_type': 'form',
            'views'    : [(False, 'tree'),(False, 'form')],
            'res_model': 'is.purchase.order.line',
            'type': 'ir.actions.act_window',
        }


#    def init(self, cr):
#        cr.execute("""
#            -- DROP VIEW  IF EXISTS is_anomalie_position_fiscale;
#            -- DROP MATERIALIZED VIEW IF EXISTS is_purchase_order_line;
#            CREATE MATERIALIZED VIEW is_purchase_order_line AS (
#                select  pol.id,
#                        pol.id                  as order_line_id,
#                        po.id                   as order_id,
#                        po.is_cfc_id            as is_cfc_id,
#                        po.partner_id           as partner_id, 
#                        po.date_order,
#                        po.minimum_planned_date,
#                        po.is_date_confirmation,
#                        po.is_commentaire,
#                        po.is_num_da            as is_num_da,
#                        po.is_document          as is_document,
#                        pol.is_num_chantier     as is_num_chantier,
#                        po.is_demandeur_id      as is_demandeur_id,
#                        pt.id                   as product_id, 
#                        pt.is_ref_fournisseur   as is_ref_fournisseur,
#                        pol.date_planned,
#                        pol.product_qty,
#                        pol.product_uom,
#                        pol.price_unit,
#                        pol.is_justification,

#                        pt.uom_po_id,
#                        is_unit_coef(pol.product_uom, pt.uom_po_id)*pol.price_unit  price_unit_uom_po,
#                        is_unit_coef(pt.uom_po_id, pol.product_uom)*pol.product_qty product_qty_uom_po,
#                        (
#                            select sum(sm1.product_uom_qty*is_unit_coef(pt1.uom_po_id, sm1.product_uom))
#                            from stock_picking sp1 inner join stock_move           sm1 on sp1.id=sm1.picking_id
#                                                   inner join product_product      pp1 on sm1.product_id=pp1.id
#                                                   inner join product_template     pt1 on pp1.product_tmpl_id=pt1.id
#                            where sp1.is_purchase_order_id=po.id and sm1.purchase_line_id=pol.id and sp1.state='done' and sm1.state='done'
#                        ) qt_rcp,

#                        (
#                            select sum(sm.product_uom_qty*is_unit_coef(pt.uom_po_id, sm.product_uom))
#                            from stock_picking sp inner join stock_move           sm on sp.id=sm.picking_id
#                                                  inner join product_product      pp on sm.product_id=pp.id
#                                                  inner join product_template     pt on pp.product_tmpl_id=pt.id
#                            where sp.is_purchase_order_id=po.id and sm.purchase_line_id=pol.id and sp.state not in ('done','cancel') 
#                        ) qt_reste,
#                        (select icof.name from is_cde_ouverte_fournisseur icof where po.partner_id=icof.partner_id limit 1) as commande_ouverte

#                from purchase_order po inner join purchase_order_line pol on po.id=pol.order_id
#                                       inner join product_product      pp on pol.product_id=pp.id
#                                       inner join product_template     pt on pp.product_tmpl_id=pt.id
#                where po.state!='draft' 
#            )
#        """)

