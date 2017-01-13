# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_comparatif_cde_draft_done(models.Model):
    _name='is.comparatif.cde.draft.done'
    _order='product_id'
    _auto = False

    product_id           = fields.Many2one('product.template', 'Article')
    date_livraison       = fields.Date('Date livraison commande')
    order_id             = fields.Many2one('sale.order', 'Commande en cours (brouillon)')
    qt_commande          = fields.Float('Qt commande en cours')
    qt_livree            = fields.Float('Qt commande terminée (liste à servir)')


    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_comparatif_cde_draft_done')
        cr.execute("""
            CREATE OR REPLACE view is_comparatif_cde_draft_done AS (
                select
                    sol2.id,
                    pt.id                  product_id,
                    sol2.is_date_livraison date_livraison,
                    so.id                  order_id,
                    sol2.qty_done          qt_commande, 
                    sol2.qty_draft         qt_livree
                from (
                    select
                        sol.id,
                        sol.product_id,
                        sol.is_date_livraison,
                        sol.order_id, 
                        sol.product_uom_qty qty_done, 
                        (
                            select sol2.product_uom_qty
                            from sale_order_line sol2
                            where 
                                sol2.is_type_commande='ferme' and 
                                sol2.state='draft' and
                                sol2.product_id=sol.product_id and
                                sol2.is_date_livraison=sol.is_date_livraison
                            limit 1
                        ) qty_draft
                    from sale_order_line sol
                    where is_type_commande='ferme' and state='done'
                    order by product_id
                ) sol2 inner join product_product  pp on sol2.product_id=pp.id
                       inner join product_template pt on pp.product_tmpl_id=pt.id 
                       inner join sale_order       so on sol2.order_id=so.id
                where sol2.qty_draft>0
                order by pt.is_code, sol2.is_date_livraison
            )
        """)



