# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_article_sans_nomenclature(models.Model):
    _name='is.article.sans.nomenclature'
    _order='is_code'
    _auto = False

    is_code     = fields.Char('Code PG')
    designation = fields.Char('Désignation')
    nb          = fields.Char('Nb nomenclatures')

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_article_sans_nomenclature')
        cr.execute("""
            CREATE OR REPLACE view is_article_sans_nomenclature AS (
                SELECT 
                    pt.id          as id,
                    pt.is_code     as is_code,
                    pt.name        as designation,
                    (select count(id) from mrp_bom mb where pt.id=mb.product_tmpl_id) as nb 
                FROM product_template pt inner join stock_route_product srp on pt.id=srp.product_id
                WHERE pt.id>0 and srp.route_id=6
            )
        """)

#select * from stock_route_product;
#product_id | route_id 
#plastigray=# select id,name from stock_location_route;                                                                                                                                                    
# id |            name                                                                                                                                                                                     
#----+-----------------------------                                                                                                                                                                        
#  5 | Buy
#  6 | Manufacture


