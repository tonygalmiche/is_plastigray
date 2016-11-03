# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_nomenclature_sans_gamme(models.Model):
    _name='is.nomenclature.sans.gamme'
    _order='bom_id, product_id'
    _auto = False

    bom_id                = fields.Many2one('mrp.bom', 'Nomenclature')
    product_id            = fields.Many2one('product.template', 'Article')
    is_category_id        = fields.Many2one('is.category', 'Catégorie')
    is_gestionnaire_id    = fields.Many2one('is.gestionnaire', 'Gestionnaire')
    is_sous_traitance     = fields.Boolean('Nomenclature de sous-traitance')
    is_negoce             = fields.Boolean('Nomenclature de négoce')
    is_inactive           = fields.Boolean('Nomenclature inactive')
    routing_id            = fields.Many2one('mrp.routing', 'Gamme')
    is_gamme_generique_id = fields.Many2one('mrp.routing', 'Gamme générique')


    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_nomenclature_sans_gamme')
        cr.execute("""
            CREATE OR REPLACE view is_nomenclature_sans_gamme AS (
                SELECT 
                    mb.id                    as id,
                    mb.id                    as bom_id,
                    mb.product_tmpl_id       as product_id,
                    pt.is_category_id        as is_category_id,
                    pt.is_gestionnaire_id    as is_gestionnaire_id,
                    mb.is_sous_traitance     as is_sous_traitance,
                    mb.is_negoce             as is_negoce,
                    mb.is_inactive           as is_inactive,
                    mb.routing_id            as routing_id,
                    mb.is_gamme_generique_id as is_gamme_generique_id
                FROM mrp_bom mb inner join product_template    pt  on mb.product_tmpl_id=pt.id
                                inner join stock_route_product srp on pt.id=srp.product_id
                                inner join is_category         ic  on pt.is_category_id=ic.id
                                inner join is_gestionnaire     ig  on pt.is_gestionnaire_id=ig.id
                WHERE pt.id>0 
                      and pt.active='t' 
                      and (mb.is_negoce is null         or mb.is_negoce='f')
                      and (mb.is_sous_traitance is null or mb.is_sous_traitance='f')
                      and (routing_id is null or is_gamme_generique_id is null)
                      and (ic.fantome is null or ic.fantome='f')
            )
        """)





