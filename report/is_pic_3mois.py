# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_pic_3mois(models.Model):
    _name='is.pic.3mois'
    _order='partner_id, product_id, is_date_expedition'
    _auto = False

    partner_id         = fields.Many2one('res.partner', 'Client')
    is_mold_id         = fields.Many2one('is.mold', 'Moule')
    project            = fields.Many2one('is.mold.project', 'Projet')
    product_id         = fields.Many2one('product.product', 'Article')
    is_category_id     = fields.Many2one('is.category', 'Catégorie')
    description        = fields.Char("Description")
    is_ref_client      = fields.Char("Référence client")
    product_uom_qty    = fields.Float('Quantité')
    is_date_expedition = fields.Date("Date d'expédition")
    is_type_commande   = fields.Selection([('ferme', 'Ferme'),('previsionnel', 'Prév.')], "Type")
    route_id           = fields.Many2one('stock.location.route', 'Achat/Fabriqué')



#        'route_ids': fields.many2many('stock.location.route', 'stock_route_product', 'product_id', 'route_id', 'Routes', domain="[('product_selectable', '=', True)]",
#                                    help="Depending on the modules installed, this will allow you to define the route of the product: whether it will be bought, manufactured, MTO/MTS,..."),

#plastigray=# select * from stock_route_product limit 1;
# product_id | route_id 
#------------+----------
#          3 |        5




    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_pic_3mois')

        cr.execute("""
                CREATE OR REPLACE view is_pic_3mois AS (
                SELECT 
                    sol.id,
                    so.partner_id,
                    sol.product_id,
                    pt.is_category_id,
                    concat (pt.is_code, ' ', pt.name, ' (', im.name, ')') description,
                    pt.is_ref_client,
                    pt.is_mold_id,
                    sol.product_uom_qty,
                    sol.is_date_expedition,
                    sol.is_type_commande,
                    im.project,
                    (select route_id from stock_route_product srp where srp.product_id=pt.id  limit 1) route_id
                FROM sale_order so inner join sale_order_line sol on so.id=sol.order_id 
                                   inner join product_product pp on pp.id = sol.product_id
                                   inner join product_template pt on pt.id = pp.product_tmpl_id
                                   left outer join is_mold im on pt.is_mold_id = im.id


               )
        """)



