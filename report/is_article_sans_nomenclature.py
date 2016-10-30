# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_article_sans_nomenclature(models.Model):
    _name='is.article.sans.nomenclature'
    _order='is_code'
    _auto = False

    product_id     = fields.Many2one('product.template', 'Article')
    is_code        = fields.Char('Code Article')
    designation    = fields.Char('Désignation')
    is_category_id = fields.Many2one('is.category', 'Catégorie')

    nb          = fields.Integer('Nb nomenclatures')

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_article_sans_nomenclature')
        cr.execute("""
            CREATE OR REPLACE view is_article_sans_nomenclature AS (
                SELECT 
                    pt.id             as id,
                    pt.id             as product_id,
                    pt.is_code        as is_code,
                    pt.name           as designation,
                    pt.is_category_id as is_category_id,
                    (select count(id) from mrp_bom mb where pt.id=mb.product_tmpl_id) as nb 
                FROM product_template pt inner join stock_route_product srp on pt.id=srp.product_id
                                         inner join is_category ic          on pt.is_category_id=ic.id
                WHERE pt.id>0 and srp.route_id=6 and pt.active='t'
            )
        """)


