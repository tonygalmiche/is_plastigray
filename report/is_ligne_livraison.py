# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _
import datetime
import pytz


class is_ligne_livraison(models.Model):
    _name='is.ligne.livraison'
    _order='date_mouvement desc'
    _auto = False

    client_order_ref    = fields.Char('Commande Client')
    partner_id          = fields.Many2one('res.partner', 'Client')
    product_id          = fields.Many2one('product.template', 'Article')
    segment_id          = fields.Many2one('is.product.segment', 'Segment')
    is_category_id      = fields.Many2one('is.category', 'Catégorie')
    is_gestionnaire_id  = fields.Many2one('is.gestionnaire', 'Gestionnaire')
    family_id           = fields.Char('Famille')
    ref_client          = fields.Char('Référence client')
    is_mold_dossierf    = fields.Char('Moule ou Dossier F')
    product_uom_qty     = fields.Float('Quantité livrée', digits=(14,2))
    qt_par_uc           = fields.Float('UC', digits=(14,0))
    nb_uc               = fields.Float('Quantité livrée (UC)', digits=(14,1))
    product_uom         = fields.Many2one('product.uom', 'Unité')
    date_expedition     = fields.Date("Date d'expédition")
    date_livraison      = fields.Date("Date d'arrivée chez le client")
    nb_uc               = fields.Float('Quantité livrée (UC)', digits=(14,1))
    date_mouvement      = fields.Datetime('Date mouvement')
    price_unit          = fields.Float('Prix unitaire', digits=(14,4))
    price_subtotal      = fields.Float('Montant total', digits=(14,2))

    amortissement_moule = fields.Float('Amt client négocié', digits=(14,4))
    amt_interne         = fields.Float('Amt interne'       , digits=(14,4))
    cagnotage           = fields.Float('Cagnotage'         , digits=(14,4))

    montant_amt_moule   = fields.Float('Montant amt client négocié', digits=(14,2))
    montant_amt_interne = fields.Float('Montant amt interne'       , digits=(14,2))
    montant_cagnotage   = fields.Float('Montant cagnotage'         , digits=(14,2))

    montant_matiere     = fields.Float('Montant matière livrée', digits=(14,2))
    order_id            = fields.Many2one('sale.order', 'Commande')
    order_line_id       = fields.Many2one('sale.order.line', 'Ligne de commande')
    picking_id          = fields.Many2one('stock.picking', 'Livraison')
    move_id             = fields.Many2one('stock.move', 'Mouvement de stock')
    user_id             = fields.Many2one('res.users', 'Utilisateur')
    state               = fields.Selection([
        ('draft'    , u'Nouveau'),
        ('cancel'   , u'Annulé'),
        ('waiting'  , u'En attente'),
        ('confirmed', u'Confirmé'),
        ('assigned' , u'Disponible'),
        ('done'     , u'Terminé')], u"État", readonly=True, select=True)


    @api.multi
    def refresh_materialized_view_action(self):
        cr = self._cr
        cr.execute("REFRESH MATERIALIZED VIEW is_ligne_livraison;")
        view_id=self.env.ref('is_plastigray.is_ligne_livraison_tree_view').id
        now = datetime.datetime.now(pytz.timezone('Europe/Paris')).strftime('%H:%M:%S')
        return {
            'name'     : u'Lignes des livraisons actualisées à '+str(now),
            'view_mode': 'tree,form,graph',
            'view_type': 'form',
            'res_model': 'is.ligne.livraison',
            'views'    : [(view_id, 'tree'),(False, 'form'),(False, 'graph')],
            'type'     : 'ir.actions.act_window',
        }


    def init(self, cr):
        #tools.drop_view_if_exists(cr, 'is_ligne_livraison')




        
        cr.execute("""

            DROP MATERIALIZED VIEW IF EXISTS is_ligne_livraison;
            CREATE MATERIALIZED view is_ligne_livraison AS (
                select  sm.id,
                        sp.is_date_expedition   as date_expedition,
                        sp.is_date_livraison    as date_livraison,
                        sm.date                 as date_mouvement,
                        sol.is_client_order_ref as client_order_ref,
                        sp.partner_id           as partner_id, 
                        pt.id                   as product_id, 
                        ipf.name                as family_id,
                        pt.segment_id           as segment_id,
                        pt.is_category_id       as is_category_id,
                        pt.is_gestionnaire_id   as is_gestionnaire_id,
                        pt.is_mold_dossierf     as is_mold_dossierf,
                        pt.is_ref_client        as ref_client,
                        sm.product_uom_qty,
                        COALESCE(is_qt_par_uc(pt.id),1) as qt_par_uc,
                        sm.product_uom_qty/COALESCE(is_qt_par_uc(pt.id),1) as nb_uc,
                        sm.product_uom          as product_uom,
                        sol.price_unit          as price_unit,
                        (sol.price_unit*sol.product_uom_qty) as price_subtotal,

                        sm.is_amortissement_moule as amortissement_moule,
                        sm.is_amt_interne         as amt_interne,
                        sm.is_cagnotage           as cagnotage,
                        sm.is_montant_amt_moule   as montant_amt_moule,
                        sm.is_montant_amt_interne as montant_amt_interne,
                        sm.is_montant_cagnotage   as montant_cagnotage,
                        sm.is_montant_matiere     as montant_matiere,

                        so.id                   as order_id,
                        sol.id                  as order_line_id,
                        sp.id                   as picking_id, 
                        sm.id                   as move_id,
                        sm.write_uid            as user_id,
                        sm.state                as state
                from stock_picking sp inner join stock_move                sm on sm.picking_id=sp.id 
                                      inner join product_product           pp on sm.product_id=pp.id
                                      inner join product_template          pt on pp.product_tmpl_id=pt.id
                                      inner join res_partner               rp on sp.partner_id=rp.id
                                      left outer join is_product_famille   ipf on pt.family_id=ipf.id
                                      left outer join sale_order           so on sp.is_sale_order_id=so.id
                                      left outer join sale_order_line     sol on sm.is_sale_line_id=sol.id


                where sp.picking_type_id=2 and sm.state='done' and so.id is not null
            )
        """)





        # cr.execute("""

        #     DROP MATERIALIZED VIEW IF EXISTS is_ligne_livraison;
        #     CREATE MATERIALIZED view is_ligne_livraison AS (
        #         select  sm.id,
        #                 sp.is_date_expedition   as date_expedition,
        #                 sp.is_date_livraison    as date_livraison,
        #                 sm.date                 as date_mouvement,
        #                 sol.is_client_order_ref as client_order_ref,
        #                 sp.partner_id           as partner_id, 
        #                 pt.id                   as product_id, 
        #                 ipf.name                as family_id,
        #                 pt.segment_id           as segment_id,
        #                 pt.is_category_id       as is_category_id,
        #                 pt.is_gestionnaire_id   as is_gestionnaire_id,
        #                 pt.is_mold_dossierf     as is_mold_dossierf,
        #                 pt.is_ref_client        as ref_client,
        #                 sm.product_uom_qty,
        #                 COALESCE(is_qt_par_uc(pt.id),1) as qt_par_uc,
        #                 sm.product_uom_qty/COALESCE(is_qt_par_uc(pt.id),1) as nb_uc,
        #                 sm.product_uom          as product_uom,
        #                 sol.price_unit          as price_unit,
        #                 (sol.price_unit*sol.product_uom_qty) as price_subtotal,

        #                 get_amortissement_moule_a_date(rp.is_code, pt.id, sp.is_date_expedition) as amortissement_moule,
        #                 get_amt_interne_a_date(rp.is_code, pt.id, sp.is_date_expedition) as amt_interne,
        #                 get_cagnotage_a_date(rp.is_code, pt.id, sp.is_date_expedition) as cagnotage,

        #                 get_amortissement_moule_a_date(rp.is_code, pt.id, sp.is_date_expedition)*sol.product_uom_qty as montant_amt_moule,
        #                 get_amt_interne_a_date(rp.is_code, pt.id, sp.is_date_expedition)*sol.product_uom_qty as montant_amt_interne,
        #                 get_cagnotage_a_date(rp.is_code, pt.id, sp.is_date_expedition)*sol.product_uom_qty as montant_cagnotage,

        #                 get_cout_act_matiere_st(pp.id)*sol.product_uom_qty as montant_matiere,
        #                 so.id                   as order_id,
        #                 sol.id                  as order_line_id,
        #                 sp.id                   as picking_id, 
        #                 sm.id                   as move_id,
        #                 sm.write_uid            as user_id,
        #                 sm.state                as state
        #         from stock_picking sp inner join stock_move                sm on sm.picking_id=sp.id 
        #                               inner join product_product           pp on sm.product_id=pp.id
        #                               inner join product_template          pt on pp.product_tmpl_id=pt.id
        #                               inner join res_partner               rp on sp.partner_id=rp.id
        #                               left outer join is_product_famille   ipf on pt.family_id=ipf.id
        #                               left outer join sale_order           so on sp.is_sale_order_id=so.id
        #                               left outer join sale_order_line     sol on sm.is_sale_line_id=sol.id


        #         where sp.picking_type_id=2 and sm.state='done' and so.id is not null
        #     )
        # """)

