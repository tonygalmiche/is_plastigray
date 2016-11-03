# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_article_sans_fournisseur(models.Model):
    _name='is.article.sans.fournisseur'
    _order='is_code'
    _auto = False

    product_id         = fields.Many2one('product.template', 'Article')
    is_code            = fields.Char('Code Article')
    is_category_id     = fields.Many2one('is.category', 'Catégorie')
    is_gestionnaire_id = fields.Many2one('is.gestionnaire', 'Gestionnaire')
    designation        = fields.Char('Désignation')
    nb                 = fields.Integer('Nb fournisseurs')

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_article_sans_fournisseur')
        cr.execute("""
            CREATE OR REPLACE view is_article_sans_fournisseur AS (
                SELECT 
                    pt.id                 as id,
                    pt.id                 as product_id,
                    pt.is_code            as is_code,
                    pt.is_category_id     as is_category_id,
                    pt.is_gestionnaire_id as is_gestionnaire_id,
                    pt.name           as designation,
                    (select count(id) from product_supplierinfo ps where pt.id=ps.product_tmpl_id) as nb 
                FROM product_template pt inner join stock_route_product srp on pt.id=srp.product_id
                                         inner join is_category         ic  on pt.is_category_id=ic.id
                                         inner join is_gestionnaire     ig  on pt.is_gestionnaire_id=ig.id
                WHERE pt.id>0 
                      and srp.route_id=5 
                      and pt.active='t'
                      and pt.is_category_id is not null 
                      and ic.name<'80'
                      and ig.actif='t'
            )
        """)

