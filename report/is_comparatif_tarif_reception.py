# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_comparatif_tarif_reception(models.Model):
    _name='is.comparatif.tarif.reception'
    _order='order_id,product_id'
    _auto = False

    order_id         = fields.Many2one('purchase.order', 'Commande')
    date_approve     = fields.Date("Date d'approbation")
    partner_id       = fields.Many2one('res.partner', 'Fournisseur')
    pricelist_id     = fields.Many2one('product.pricelist', 'Liste de prix')
    product_id       = fields.Many2one('product.product', 'Article')
    qty              = fields.Float('Quantité')
    date_planned     = fields.Date('Date prévue')
    justification    = fields.Char('Justification')
    pol_price        = fields.Float('Prix commande')
    pol_uom_id       = fields.Many2one('product.uom', 'Unité Commande')
    pricelist_price  = fields.Float('Prix liste de prix')
    pricelist_uom_id = fields.Many2one('product.uom', 'Unité Liste de prix')
    factor           = fields.Float('Coeficient')
    price_delta      = fields.Float('Ecart de prix')


    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_comparatif_tarif_reception')
        cr.execute("""
CREATE OR REPLACE FUNCTION is_prix_achat(pricelistid integer, productid integer, qt float, date date) RETURNS float AS $$
BEGIN
    RETURN (
        select price_surcharge 
        from product_pricelist ppl inner join product_pricelist_version ppv on ppv.pricelist_id=ppl.id 
                                   inner join product_pricelist_item    ppi on ppi.price_version_id=ppv.id
        where ppi.product_id=productid
            and ppl.id=pricelistid
            and round(min_quantity::numeric,5)<=round(qt::numeric,5)
            and ppl.type='purchase' and ppl.active='t'
            and (ppv.date_end   is null or ppv.date_end   >= date) 
            and (ppv.date_start is null or ppv.date_start <= date) 

            and (ppi.date_end   is null or ppi.date_end   >= date) 
            and (ppi.date_start is null or ppi.date_start <= date) 
        order by ppi.sequence limit 1
    );
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION is_unit_coef(uom1 integer, uom2 integer) RETURNS float AS $$
DECLARE
    factor1 float := 1;
    factor2 float := 1;
BEGIN

    factor1 := (
        select factor 
        from product_uom
        where id=uom1
    );
    factor2 := (
        select factor 
        from product_uom
        where id=uom2
    );
    RETURN factor1/factor2;
END;
$$ LANGUAGE plpgsql;




CREATE OR REPLACE view is_comparatif_tarif_reception AS (
    select 
        id,
        order_id,
        date_approve,
        partner_id,
        pricelist_id,
        product_id,
        qty,
        date_planned,
        justification,
        pol_price,
        pricelist_price,
        pol_uom_id,
        pricelist_uom_id,
        factor,
        abs(pol_price*factor-pricelist_price) price_delta
    from (
        select 
            sm.id                 id, 
            po.id                 order_id,
            po.date_approve       date_approve,
            po.partner_id         partner_id,
            po.pricelist_id       pricelist_id,
            sm.product_id         product_id, 
            pol.product_qty       qty, 
            pol.date_planned      date_planned, 
            pol.is_justification  justification,
            pol.price_unit        pol_price, 
            pol.product_uom       pol_uom_id,
            pt.uom_po_id          pricelist_uom_id,
            is_unit_coef(pol.product_uom, pt.uom_po_id) factor,
            COALESCE(is_prix_achat(po.pricelist_id,sm.product_id,pol.product_qty,pol.date_planned), 0) as pricelist_price
        from stock_move sm inner join purchase_order_line pol on sm.purchase_line_id=pol.id
                           inner join purchase_order       po on pol.order_id=po.id 
                           inner join product_product      pp on pol.product_id=pp.id
                           inner join product_template     pt on pp.product_tmpl_id=pt.id
                           inner join is_category          ic on pt.is_category_id=ic.id
        where 
            sm.state not in ('done','cancel') and 
            sm.purchase_line_id is not null and
            to_number(ic.name, '9999999')<70
    ) ipol
    where abs(pol_price*factor-pricelist_price)>0.00001
    order by ipol.id desc
)
        """)


