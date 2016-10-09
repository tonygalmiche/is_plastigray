# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _
import datetime
from dateutil.relativedelta import relativedelta

class product_pricelist_item(models.Model):
    _inherit = "product.pricelist.item"
    _order="price_version_id,product_id,sequence"

    date_start        = fields.Date('Date de début de validité')
    date_end          = fields.Date('Date de fin de validité')
    product_uom_id    = fields.Many2one('product.uom', 'Unité'        , related='product_id.uom_id'   , readonly=True)
    product_po_uom_id = fields.Many2one('product.uom', "Unité d'achat", related='product_id.uom_po_id', readonly=True)
    min_quantity      = fields.Float('Quantité minimum', required=True)

    @api.multi
    def on_change_product_id(self, product_id):
        context=self._context
        res = {}
        if product_id:
            if 'default_price_version_id' in context:
                res.setdefault('value',{})
                product = self.env['product.product'].browse(product_id)
                if product:
                    version = self.env['product.pricelist.version'].browse(context['default_price_version_id'])
                    if version.pricelist_id.type=='sale':
                        min_quantity=product.lot_livraison
                    else:
                        min_quantity=product.lot_mini
                        product_uom = self.env['product.uom'].browse(product.uom_po_id.id)
                        min_quantity = product_uom._compute_qty(product.uom_id.id, min_quantity, product.uom_po_id.id)
                    res['value']['product_uom_id']    = product.uom_id.id
                    res['value']['product_po_uom_id'] = product.uom_po_id.id
                    res['value']['min_quantity']      = min_quantity
                    res['value']['price_surcharge']   = product.uom_po_id.amount
        return res





class product_pricelist_version(models.Model):
    _inherit = "product.pricelist.version"


    @api.multi
    def action_liste_items(self):
        for obj in self:
            if obj.pricelist_id.type=='sale':
                view_id=self.env.ref('is_plastigray.is_product_pricelist_item_sale_tree_view')
            else:
                view_id=self.env.ref('is_plastigray.is_product_pricelist_item_purchase_tree_view')
            return {
                'name': obj.name,
                'view_mode': 'tree',
                'view_type': 'form',
                'res_model': 'product.pricelist.item',
                'type': 'ir.actions.act_window',
                'view_id': view_id.id,
                'domain': [('price_version_id','=',obj.id)],
                'context': {'default_price_version_id': obj.id }
            }


    def action_dupliquer(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids, dict(context, active_test=False)):
            date_end=datetime.datetime.strptime(obj.date_end, '%Y-%m-%d')
            date_start = date_end   + datetime.timedelta(days=1)
            date_end = date_start + relativedelta(years=1)
            date_end = date_end   + datetime.timedelta(days=-1)
            name=str(int(obj.name)+1)
            vals = {
                'pricelist_id' : obj.pricelist_id.id,
                'name': name,
                'active': obj.active,
                'date_start': date_start,
                'date_end': date_end ,
            }
            model = self.pool.get('product.pricelist.version')
            new_id = model.create(cr, uid, vals, context=context)


            model = self.pool.get('product.pricelist.item')
            for item in obj.items_id:
                start=item.date_start
                if start:
                    start=date_start
                end=item.date_end
                if end:
                    end=date_end
                vals = {
                    'price_version_id': new_id,
                    'name' : name,
                    'product_id': item.product_id.id,
                    'min_quantity': item.min_quantity,
                    'sequence': item.sequence,
                    'date_start': item.date_start,
                    'date_end': item.date_end,
                    'price_surcharge': item.price_surcharge,
                }
                id = model.create(cr, uid, vals, context=context)


        return {
            'name': "Liste de prix",
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'product.pricelist',
            'type': 'ir.actions.act_window',
            'res_id': obj.pricelist_id.id,
        }




