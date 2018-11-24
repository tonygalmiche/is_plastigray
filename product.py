# -*- coding: utf-8 -*-

import time
import datetime
from openerp import pooler
from openerp import models,fields,api
from openerp.tools.translate import _



class product_template(models.Model):
    _inherit = "product.template"


    @api.depends('weight','weight_net')
    def _compute_weight_delta(self):
        for obj in self:
            delta=obj.weight-obj.weight_net
            obj.is_weight_delta=delta


    is_weight_delta = fields.Float("Ecart entre poids brut et poids net", compute='_compute_weight_delta', readonly=True, store=True,digits=(12,4))


    @api.multi
    def copy(self,vals):
        for obj in self:
            vals.update({
                'is_code'                 : obj.is_code + ' (copie)',
                'property_account_income' : obj.property_account_income,
                'property_account_expense': obj.property_account_expense,
            })
            res=super(product_template, self).copy(vals)
            model = self.env['product.supplierinfo']
            for item in obj.seller_ids:
                vals = {
                    'product_tmpl_id': res.id,
                    'name'           : item.name.id,
                    'product_name'   : item.product_name,
                    'sequence'       : item.sequence,
                    'product_code'   : item.product_code,
                    'min_qty'        : item.min_qty,
                    'delay'          : item.delay,
                }
                id = model.create(vals)
            model = self.env['product.packaging']
            for item in obj.packaging_ids:
                vals = {
                    'product_tmpl_id': res.id,
                    'ean'            : item.ean,
                    'qty'            : item.qty,
                    'ul'             : item.ul.id,
                    'ul_qty'         : item.ul_qty,
                    'rows'           : item.rows,
                    'ul_container'   : item.ul_container.id,
                    'weight'         : item.weight,
                }
                id = model.create(vals)
            model = self.env['is.product.client']
            for item in obj.is_client_ids:
                vals = {
                    'product_id'         : res.id,
                    'client_id'          : item.client_id.id,
                    'client_defaut'      : item.client_defaut,
                    'lot_livraison'      : item.lot_livraison,
                    'multiple_livraison' : item.multiple_livraison,
                }
                id = model.create(vals)
        return res


    def get_uc(self):
        uc=0
        for obj in self:
            if obj.packaging_ids:
                uc=obj.packaging_ids[0].qty
        if uc==0:
            uc=1
        return uc

    def get_um(self):
        um=0
        for obj in self:
            if obj.packaging_ids:
                um=obj.packaging_ids[0].qty*obj.packaging_ids[0].rows*obj.packaging_ids[0].ul_qty
        if um==0:
            um=self.get_uc()
        return um


    @api.multi
    def corriger_stock_negatif_action(self):
        for obj in self:
            products=self.env['product.product'].search([('product_tmpl_id','=',obj.id)])
            for product in products:
                quants=self.env['stock.quant'].search([('product_id','=',product.id)])
                locations=[]
                for quant in quants:
                    if quant.location_id.usage=='internal' and quant.qty<0:
                        location=quant.location_id
                        if location not in locations:
                            locations.append(location)
                for location in locations:
                    vals={
                        'name': product.is_code+u' (Correction stock négatif)',
                        'location_id': location.id,
                        'filter':'product',
                        'product_id': product.id,
                    }
                    inventory=self.env['stock.inventory'].create(vals)
                    inventory.prepare_inventory()
                    create_date=False
                    qty=0
                    for line in inventory.line_ids:
                        if line.product_qty<0:
                            qty=qty-line.product_qty
                            line.product_qty=0
                    for line in inventory.line_ids:
                        if line.product_qty>0:
                            if line.product_qty>=qty:
                                line.product_qty=line.product_qty-qty
                                qty=0
                            else:
                                qty=qty-line.product_qty
                                line.product_qty=0
                            if qty<=0:
                                break
                    inventory.action_done()


class product_product(models.Model):
    _name = "product.product"
    _inherit = "product.product"
     
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context and context.get('pricelist', False):
            date = context.get('date') or time.strftime('%Y-%m-%d')
            pricelist = self.pool.get('product.pricelist').browse(cr, uid, context.get('pricelist', False), context=context)
            version = False
            for v in pricelist.version_id:
                if ((v.date_start is False) or (v.date_start <= date)) and ((v.date_end is False) or (v.date_end >= date)):
                    version = v
                    break
            
            if version:
                cr.execute("SELECT distinct(product_id) FROM product_pricelist_item where price_version_id = %s" ,(version.id,))
                ids = [x[0] for x in cr.fetchall()]
                ids = None in ids and  [] or ids
                if ids:
                    args.append(('id', 'in', ids))
                    order = 'default_code'
            else:
                args.append(('id', 'in', []))
            
        return super(product_product, self).search(cr, uid, args, offset=offset, limit=limit, order=order, context=context, count=count)
 

    def get_stock(self, product_id, control_quality=False, location=False):
        cr=self._cr
        SQL="""
            select sum(sq.qty) 
            from stock_quant sq inner join stock_location sl on sq.location_id=sl.id
            where sq.product_id="""+str(product_id)+""" 
                  and sl.usage='internal' and sl.active='t' """
        if control_quality:
            SQL=SQL+" and sl.control_quality='"+str(control_quality)+"' "
        if location:
            SQL=SQL+" and sl.name='"+str(location)+"' "
        cr.execute(SQL)
        result = cr.fetchall()
        stock=0
        for row in result:
            stock=row[0]
        return stock

    




class product_uom(models.Model):
    _inherit = 'product.uom'

    _order   = 'category_id,name'


        
