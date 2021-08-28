# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_sale_order_line(models.Model):
    _name='is.sale.order.line'
    _order='date_expedition desc'
    _auto = False

    client_order_ref    = fields.Char('Commande Client')
    partner_id          = fields.Many2one('res.partner', 'Client')
    product_id          = fields.Many2one('product.template', 'Article')
    segment_id          = fields.Many2one('is.product.segment', 'Segment')
    is_category_id      = fields.Many2one('is.category', 'Catégorie')
    is_gestionnaire_id  = fields.Many2one('is.gestionnaire', 'Gestionnaire')
    ref_client          = fields.Char('Référence client')
    mold_id             = fields.Many2one('is.mold', 'Moule')
    product_uom_qty     = fields.Float('Quantité livrée', digits=(14,2))
    product_uom         = fields.Many2one('product.uom', 'Unité')
    date_expedition     = fields.Date("Date d'expédition")
    date_livraison      = fields.Date("Date d'arrivée chez le client")
    price_unit          = fields.Float('Prix unitaire', digits=(14,4))
    price_subtotal      = fields.Float('Montant total', digits=(14,2))
    
    amortissement_moule = fields.Float('Amt client négocié', digits=(14,4))
    amt_interne         = fields.Float('Amt interne'       , digits=(14,4))
    cagnotage           = fields.Float('Cagnotage'         , digits=(14,4))

    montant_amt_moule   = fields.Float('Montant amt client négocié', digits=(14,2))
    montant_amt_interne = fields.Float('Montant amt interne'       , digits=(14,2))
    montant_cagnotage   = fields.Float('Montant cagnotage'         , digits=(14,2))

    montant_amt_moule   = fields.Float('Montant amortissement moule', digits=(14,2))
    montant_matiere     = fields.Float('Montant matière livrée', digits=(14,2))
    order_id            = fields.Many2one('sale.order', 'Commande')
    order_line_id       = fields.Many2one('sale.order.line', 'Ligne de commande')
    state               = fields.Char(u"État", readonly=True, select=True)

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_sale_order_line')
        cr.execute("""
            CREATE OR REPLACE view is_sale_order_line AS (
                select  sol.id,
                        sol.is_date_expedition  as date_expedition,
                        sol.is_date_livraison   as date_livraison,
                        sol.is_client_order_ref as client_order_ref,
                        so.partner_id           as partner_id, 
                        pt.id                   as product_id, 
                        pt.segment_id           as segment_id,
                        pt.is_category_id       as is_category_id,
                        pt.is_gestionnaire_id   as is_gestionnaire_id,
                        pt.is_mold_id           as mold_id,
                        pt.is_ref_client        as ref_client,
                        sol.product_uom_qty     as product_uom_qty,
                        sol.product_uom         as product_uom,
                        sol.price_unit          as price_unit,
                        (sol.price_unit*sol.product_uom_qty) as price_subtotal,

                        get_amortissement_moule_a_date(rp.is_code, pt.id, sol.is_date_expedition) as amortissement_moule,
                        get_amt_interne_a_date(rp.is_code, pt.id, sol.is_date_expedition)  as amt_interne,
                        get_cagnotage_a_date(rp.is_code, pt.id, sol.is_date_expedition)    as cagnotage,

                        get_amortissement_moule_a_date(rp.is_code, pt.id, sol.is_date_expedition)*sol.product_uom_qty as montant_amt_moule,
                        get_amt_interne_a_date(rp.is_code, pt.id, sol.is_date_expedition)*sol.product_uom_qty         as montant_amt_interne,
                        get_cagnotage_a_date(rp.is_code, pt.id, sol.is_date_expedition)*sol.product_uom_qty           as montant_cagnotage,

                        get_cout_act_matiere_st(pp.id)*sol.product_uom_qty as montant_matiere,
                        so.id                   as order_id,
                        sol.id                  as order_line_id,
                        so.state                as state
                from sale_order so    inner join sale_order_line     sol on so.id=sol.order_id
                                      inner join product_product      pp on sol.product_id=pp.id
                                      inner join product_template     pt on pp.product_tmpl_id=pt.id
                                      inner join res_partner          rp on so.partner_id=rp.id
            )
        """)

