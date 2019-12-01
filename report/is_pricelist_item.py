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
    base               = fields.Integer('Base')
    price_version_id   = fields.Many2one('product.pricelist.version', 'Version')
    version_date_start = fields.Date('Date début version')
    version_date_end   = fields.Date('Date fin version')
    product_id         = fields.Many2one('product.product', 'Article')
    gestionnaire_id    = fields.Many2one('is.gestionnaire', 'Gestionnaire')
    ref_client         = fields.Char('Référence client')
    ref_fournisseur    = fields.Char('Référence fournisseur')
    moule              = fields.Char('Moule ou Dossier F')
    sequence           = fields.Integer('Sequence')
    product_uom_id     = fields.Many2one('product.uom', "Unité")
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
                    ppi.base              as base,
                    ppi.price_version_id  as price_version_id,
                    ppv.date_start        as version_date_start,
                    ppv.date_end          as version_date_end,
                    ppi.product_id        as product_id,
                    pt.is_gestionnaire_id as gestionnaire_id,
                    pt.is_ref_client      as ref_client,
                    pt.is_ref_fournisseur as ref_fournisseur,
                    pt.is_mold_dossierf   as moule,
                    ppi.sequence          as sequence,
                    pt.uom_id             as product_uom_id,
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


    @api.multi
    def action_liste_items(self):
        for obj in self:
            print obj.price_version_id.pricelist_id

            if obj.price_version_id.pricelist_id.type=='sale':
                view_id=self.env.ref('is_plastigray.is_product_pricelist_item_sale_tree_view').id
                pricelist_type='sale'
            else:
                view_id=self.env.ref('is_plastigray.is_product_pricelist_item_purchase_tree_view').id
                pricelist_type='purchase'

            return {
                'name': str(obj.pricelist_name)+" ("+str(obj.price_version_id.name)+")",
                'view_mode': 'tree',
                'view_type': 'form',
                'res_model': 'product.pricelist.item',
                'type': 'ir.actions.act_window',
                #'view_id': view_id.id,
                'view_id'  : False,
                'views'    : [(view_id, 'tree')],
                'domain': [('price_version_id','=',obj.price_version_id.id)],
                'context': {
                    'default_price_version_id': obj.price_version_id.id,
                    'type': pricelist_type,
                }
            }


#        return {
#            'name': u'Lignes des factures client actualisées à '+str(now),
#            'view_mode': 'tree,form,graph',
#            'view_type': 'form',
#            'view_id'  : False,
#            'views'    : [(view_id, 'tree'),(False, 'form'),(False, 'graph')],
#            'res_model': 'is.account.invoice.line',
#            'domain'   : [('type','=', 'out_invoice')],
#            'type': 'ir.actions.act_window',
#        }





    @api.multi
    def corriger_anomalie_pricelist(self):
        for obj in self:
            base=False
            if obj.pricelist_type=='purchase' and obj.base!=2:
                base=2
            if obj.pricelist_type=='sale' and obj.base!=1:
                base=1

            if base:
                items=self.env['product.pricelist.item'].browse(obj.id)
                for item in items:
                    item.base=base




