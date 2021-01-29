# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_livraison_gefco(models.Model):
    _name='is.livraison.gefco'
    _order='is_date_expedition desc, name desc, product_id'
    _auto = False

    is_date_expedition  = fields.Date("Date d'expédition")
    partner_id          = fields.Many2one('res.partner', 'Client')
    picking_id          = fields.Many2one('stock.picking', 'Livraison')
    client_order_ref    = fields.Char('Commande Client')
    name                = fields.Char('BL')
    is_mold_dossierf    = fields.Char('Moule ou Dossier F')
    product_id          = fields.Many2one('product.template', 'Article')
    product_uom_qty     = fields.Float("Quantité")
    uc                  = fields.Char('UC')
    um                  = fields.Char('UM')
    nb_uc               = fields.Float("Nb UC")
    nb_um               = fields.Float("Nb UM")

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_livraison_gefco')
        cr.execute("""
            CREATE OR REPLACE view is_livraison_gefco AS (
                select 
                    sm.id,
                    sp.is_date_expedition,
                    sp.partner_id,
                    sp.id as picking_id,
                    sol.is_client_order_ref client_order_ref,
                    sp.name,
                    pt.is_mold_dossierf,
                    pt.id product_id,
                    sm.product_uom_qty,
                    sm.product_uom_qty/coalesce(
                        (
                            select qty from product_packaging pack where pack.product_tmpl_id=pt.id and qty>0 limit 1
                        )
                    ,1) nb_uc,
                    sm.product_uom_qty/coalesce(
                        (
                            select qty*rows*ul_qty from product_packaging pack where pack.product_tmpl_id=pt.id and qty>0 limit 1
                        )
                    ,1) nb_um,
                    (
                        select ul.name 
                        from product_packaging pack inner join product_ul ul on pack.ul=ul.id
                        where pack.product_tmpl_id=pt.id limit 1
                    ) uc,
                    (
                        select ul2.name 
                        from product_packaging pack2 inner join product_ul ul2 on pack2.ul_container=ul2.id
                        where pack2.product_tmpl_id=pt.id limit 1
                    ) um
                from stock_picking sp inner join stock_move            sm on sp.id=sm.picking_id
                                      inner join product_product       pp on sm.product_id=pp.id
                                      inner join product_template      pt on pp.product_tmpl_id=pt.id
                                      inner join res_partner           rp on sp.partner_id=rp.id
                                      left outer join sale_order_line  sol on sm.is_sale_line_id=sol.id
                where 
                    pt.is_livraison_gefbox='t' and
                    sm.state='done' and
                    sp.state='done' and
                    sp.picking_type_id=2 
            )
        """)
