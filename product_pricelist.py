# -*- coding: utf-8 -*-

from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp

import datetime
from dateutil.relativedelta import relativedelta



class product_uom(osv.osv):
    _inherit = "product.uom"
    
    _columns = {
        'min_quantity': fields.float('Quantité minimum'),
        'amount': fields.float('Montant', digits_compute= dp.get_precision('Product Price')),
    }



class product_pricelist_version(osv.osv):
    _inherit = "product.pricelist.version"



    def action_liste_items(self, cr, uid, ids, context=None):
        print ids
        for obj in self.browse(cr, uid, ids, dict(context, active_test=False)):
            return {
                'name': obj.name,
                'view_mode': 'tree',
                'view_type': 'form',
                'res_model': 'product.pricelist.item',
                'type': 'ir.actions.act_window',
                'domain': [('price_version_id','=',obj.id)],
                'context': {'default_price_version_id': obj.id }
            }




    def action_dupliquer(self, cr, uid, ids, context=None):
        print ids
        for obj in self.browse(cr, uid, ids, dict(context, active_test=False)):




            date_end=datetime.datetime.strptime(obj.date_end, '%Y-%m-%d')
            print date_end, type(date_end)

            date_start = date_end   + datetime.timedelta(days=1)
            date_end = date_start + relativedelta(years=1)
            date_end = date_end   + datetime.timedelta(days=-1)

            print date_start , date_end

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
                print item

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







class product_pricelist_item(osv.osv):
    _inherit = "product.pricelist.item"
    _order="price_version_id,product_id,sequence"
    
    _columns = {
        'date_start': fields.date('Date de début de validité'),
        'date_end': fields.date('Date de fin de validité'),
        'product_po_uom_id': fields.related('product_id','uom_po_id', type='many2one', relation='product.uom' , string="Unité d'achat", readonly=True),
        'min_quantity': fields.float('Quantité minimum', required=True,
            help="For the rule to apply, bought/sold quantity must be greater "
              "than or equal to the minimum quantity specified in this field.\n"
              "Expressed in the default UoM of the product."
            ),
    }
    
    def on_change_product_id(self, cr, uid, ids, product_id):
        res = {}
        res.setdefault('value',{})
        if product_id:
            product_brw = self.pool.get('product.product').browse(cr, uid, product_id)[0]
            if product_brw.uom_po_id:
                res['value']['product_po_uom_id'] = product_brw.uom_po_id.id
                res['value']['min_quantity']      = product_brw.lot_mini
                res['value']['price_surcharge']   = product_brw.uom_po_id.amount
        return res


class product_pricelist(osv.osv):
    _inherit = "product.pricelist"
    
    def _price_rule_get_multi(self, cr, uid, pricelist, products_by_qty_by_partner, context=None):
        context = context or {}
        date = context.get('date') or time.strftime('%Y-%m-%d')
        date = date[0:10]

        products = map(lambda x: x[0], products_by_qty_by_partner)
        currency_obj = self.pool.get('res.currency')
        product_obj = self.pool.get('product.template')
        product_uom_obj = self.pool.get('product.uom')
        price_type_obj = self.pool.get('product.price.type')

        if not products:
            return {}

        version = False
        for v in pricelist.version_id:
            if ((v.date_start is False) or (v.date_start <= date)) and ((v.date_end is False) or (v.date_end >= date)):
                version = v
                break
        if not version:
            raise osv.except_osv(_('Warning!'), _("At least one pricelist has no active version !\nPlease create or activate one."))
        categ_ids = {}
        for p in products:
            categ = p.categ_id
            while categ:
                categ_ids[categ.id] = True
                categ = categ.parent_id
        categ_ids = categ_ids.keys()

        is_product_template = products[0]._name == "product.template"
        if is_product_template:
            prod_tmpl_ids = [tmpl.id for tmpl in products]
            # all variants of all products
            prod_ids = [p.id for p in
                        list(chain.from_iterable([t.product_variant_ids for t in products]))]
        else:
            prod_ids = [product.id for product in products]
            prod_tmpl_ids = [product.product_tmpl_id.id for product in products]

        #Added date filter
        cr.execute(
            'SELECT i.id '
            'FROM product_pricelist_item AS i '
            'WHERE (product_tmpl_id IS NULL OR product_tmpl_id = any(%s)) '
                'AND (product_id IS NULL OR (product_id = any(%s))) '
                'AND ((categ_id IS NULL) OR (categ_id = any(%s))) '
                'AND (price_version_id = %s) '
                'AND (date_start IS NULL OR date_start <= %s) '
                'AND (date_end IS NULL OR date_end >= %s) '
            'ORDER BY sequence, min_quantity desc',
            (prod_tmpl_ids, prod_ids, categ_ids, version.id, date, date))
        item_ids = [x[0] for x in cr.fetchall()]
        #print "::item_ids:::",item_ids
        
        
        
        items = self.pool.get('product.pricelist.item').browse(cr, uid, item_ids, context=context)

        price_types = {}

        results = {}
        for product, qty, partner in products_by_qty_by_partner:
            results[product.id] = 0.0
            rule_id = False
            price = False

            # Final unit price is computed according to `qty` in the `qty_uom_id` UoM.
            # An intermediary unit price may be computed according to a different UoM, in
            # which case the price_uom_id contains that UoM.
            # The final price will be converted to match `qty_uom_id`.
            qty_uom_id = context.get('uom') or product.uom_po_id.id
            price_uom_id = product.uom_po_id.id
            qty_in_product_uom = qty
            product_qty = qty
            if qty_uom_id != product.uom_po_id.id:
                try:
                    qty_in_product_uom = product_uom_obj._compute_qty(
                        cr, uid, context['uom'], qty, product.uom_po_id.id or product.uos_id.id)
                except except_orm:
                    # Ignored - incompatible UoM in context, use default product UoM
                    pass
            #print "::items:::",items
            for rule in items:
                #print ": 145::::rule.min_quantity::::",rule.id
                if rule.min_quantity and qty_in_product_uom < rule.min_quantity:
                    continue
                if is_product_template:
                    if rule.product_tmpl_id and product.id != rule.product_tmpl_id.id:
                        continue
                    if rule.product_id and \
                            (product.product_variant_count > 1 or product.product_variant_ids[0].id != rule.product_id.id):
                        # product rule acceptable on template if has only one variant
                        continue
                else:
                    if rule.product_tmpl_id and product.product_tmpl_id.id != rule.product_tmpl_id.id:
                        continue
                    if rule.product_id and product.id != rule.product_id.id:
                        continue

                if rule.categ_id:
                    cat = product.categ_id
                    while cat:
                        if cat.id == rule.categ_id.id:
                            break
                        cat = cat.parent_id
                    if not cat:
                        continue

                if rule.base == -1:
                    if rule.base_pricelist_id:
                        price_tmp = self._price_get_multi(cr, uid,
                                rule.base_pricelist_id, [(product,
                                qty, partner)], context=context)[product.id]
                        ptype_src = rule.base_pricelist_id.currency_id.id
                        price_uom_id = qty_uom_id
                        price = currency_obj.compute(cr, uid,
                                ptype_src, pricelist.currency_id.id,
                                price_tmp, round=False,
                                context=context)
                elif rule.base == -2:
                    seller = False
                    for seller_id in product.seller_ids:
                        if (not partner) or (seller_id.name.id != partner):
                            continue
                        seller = seller_id
                    if not seller and product.seller_ids:
                        seller = product.seller_ids[0]
                    if seller:
                        qty_in_seller_uom = qty
                        seller_uom = seller.product_uom.id
                        if qty_uom_id != seller_uom:
                            qty_in_seller_uom = product_uom_obj._compute_qty(cr, uid, qty_uom_id, qty, to_uom_id=seller_uom)
                        price_uom_id = seller_uom
                        for line in seller.pricelist_ids:
                            if line.min_quantity <= qty_in_seller_uom:
                                price = line.price

                else:
                    if rule.base not in price_types:
                        price_types[rule.base] = price_type_obj.browse(cr, uid, int(rule.base))
                    price_type = price_types[rule.base]

                    # price_get returns the price in the context UoM, i.e. qty_uom_id
                    price_uom_id = qty_uom_id
                    price = currency_obj.compute(
                            cr, uid,
                            price_type.currency_id.id, pricelist.currency_id.id,
                            product_obj._price_get(cr, uid, [product], price_type.field, context=context)[product.id],
                            round=False, context=context)

                if price is not False:
                    price_limit = price
                    price = price * (1.0+(rule.price_discount or 0.0))
                    if rule.price_round:
                        price = tools.float_round(price, precision_rounding=rule.price_round)

                    convert_to_price_uom = (lambda price: product_uom_obj._compute_price(
                                                cr, uid, product.uom_po_id.id,#cr, uid, product.uom_po_id.id, #Niravcr, uid, product.uom_id.id,
                                                price, price_uom_id))
                    #print "\n:::rule.min_quantity:::",rule.min_quantity,":::product_qty:::",product_qty
                    if rule.price_surcharge and rule.min_quantity <= product_qty:
                        price_surcharge = convert_to_price_uom(rule.price_surcharge)
                        price += price_surcharge

                    if rule.price_min_margin:
                        price_min_margin = convert_to_price_uom(rule.price_min_margin)
                        price = max(price, price_limit + price_min_margin)

                    if rule.price_max_margin:
                        price_max_margin = convert_to_price_uom(rule.price_max_margin)
                        price = min(price, price_limit + price_max_margin)

                    rule_id = rule.id
                    #print ":::::::::::::::::::::::rule_id::::::",rule_id,":::price:::",price
                break

            # Final price conversion to target UoM
            price = product_uom_obj._compute_price(cr, uid, price_uom_id, price, qty_uom_id)

            results[product.id] = (price, rule_id)
        return results



