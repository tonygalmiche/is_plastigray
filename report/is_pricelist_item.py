# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_pricelist_item(models.Model):
    _name='is.pricelist.item'
    _order='pricelist_name,price_version_id,sequence,product_id'
    _auto = False

    pricelist_name     = fields.Char('Liste de prix')
    pricelist_type     = fields.Char('Type')
    price_version_id   = fields.Many2one('product.pricelist.version', 'Version')
    version_date_start = fields.Date('Date début version')
    version_date_end   = fields.Date('Date fin version')
    product_id         = fields.Many2one('product.product', 'Article')
    sequence           = fields.Integer('Sequence')
    product_po_uom_id  = fields.Many2one('product.uom', "Unité d'achat")
    min_quantity       = fields.Float('Quantité min.')
    price_surcharge    = fields.Float('Prix')
    item_date_start    = fields.Date('Date début ligne')
    item_date_end      = fields.Date('Date fin ligne')

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_pricelist_item')
        cr.execute("""
            CREATE OR REPLACE view is_pricelist_item AS (
                SELECT 
                    ppi.id                as id,
                    pl.name               as pricelist_name,
                    pl.type               as pricelist_type,
                    ppi.price_version_id  as price_version_id,
                    ppv.date_start        as version_date_start,
                    ppv.date_end          as version_date_end,
                    ppi.product_id        as product_id,
                    ppi.sequence          as sequence,
                    pt.uom_po_id          as product_po_uom_id,
                    ppi.min_quantity      as min_quantity,
                    ppi.price_surcharge   as price_surcharge,
                    ppi.date_start        as item_date_start,
                    ppi.date_end          as item_date_end
                FROM product_pricelist_item ppi inner join product_product   pp on ppi.product_id=pp.id
                                                inner join product_template pt on pp.product_tmpl_id=pt.id
                                                inner join product_pricelist_version ppv on ppi.price_version_id=ppv.id
                                                inner join product_pricelist pl on ppv.pricelist_id = pl.id
                WHERE ppi.id>0 
            )
        """)



    def action_liste_items(self, cr, uid, ids, context=None):
        print ids
        for obj in self.browse(cr, uid, ids, dict(context, active_test=False)):
            return {
                'name': str(obj.pricelist_name)+" ("+str(obj.price_version_id.name)+")",
                'view_mode': 'tree',
                'view_type': 'form',
                'res_model': 'product.pricelist.item',
                'type': 'ir.actions.act_window',
                'domain': [('price_version_id','=',obj.price_version_id.id)],
                'context': {'default_price_version_id': obj.price_version_id.id }
            }





