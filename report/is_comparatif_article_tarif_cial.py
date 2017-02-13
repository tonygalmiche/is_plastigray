# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_comparatif_article_tarif_cial(models.Model):
    _name='is.comparatif.article.tarif.cial'
    _order='product_id'
    _auto = False

    product_id         = fields.Many2one('product.template'  , 'Article')
    segment_id         = fields.Many2one('is.product.segment', 'Segment')
    is_category_id     = fields.Many2one('is.category'       , 'Catégorie')
    is_gestionnaire_id = fields.Many2one('is.gestionnaire'   , 'Gestionnaire')
    client_id          = fields.Many2one('res.partner'       , 'Client')
    tarif_cial_id      = fields.Many2one('is.tarif.cial'     , 'Tarif commercial')

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_comparatif_article_tarif_cial')
        cr.execute("""
            CREATE OR REPLACE view is_comparatif_article_tarif_cial AS (
                select 
                    ipc.id,
                    pt.id product_id,
                    pt.segment_id,
                    pt.is_category_id,
                    pt.is_gestionnaire_id,
                    ipc.client_id,
                    (
                        select itc.id
                        from is_tarif_cial itc inner join res_partner rp2 on itc.partner_id=rp2.id
                        where rp2.is_code=rp1.is_code and itc.product_id=pt.id and indice_prix=999
                        limit 1
                    ) tarif_cial_id
                from product_template pt  inner join is_product_client ipc on pt.id=ipc.product_id
                                          inner join res_partner       rp1 on ipc.client_id=rp1.id
                where pt.sale_ok='t' and pt.active='t'
            )
        """)

