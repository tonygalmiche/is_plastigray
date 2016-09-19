# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_article_sans_fournisseur(models.Model):
    _name='is.article.sans.fournisseur'
    _order='is_code'
    _auto = False

    is_code     = fields.Char('Code PG')
    designation = fields.Char('Désignation')
    nb          = fields.Char('Nb fournisseurs')

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_article_sans_fournisseur')
        cr.execute("""
            CREATE OR REPLACE view is_article_sans_fournisseur AS (
                SELECT 
                    pt.id          as id,
                    pt.is_code     as is_code,
                    pt.name        as designation,
                    (select count(id) from product_supplierinfo ps where pt.id=ps.product_tmpl_id) as nb 
                FROM product_template pt inner join stock_route_product srp on pt.id=srp.product_id
                WHERE pt.id>0 and srp.route_id=5
            )
        """)

# id  | create_uid | product_code |        create_date         | name | sequence | product_name | company_id | write_uid | delay |         
#write_date         | min_qty |  qty   | product_tmpl_id 
#plastigray=# select * from product_supplierinfo;

