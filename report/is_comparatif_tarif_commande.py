# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_comparatif_tarif_commande(models.Model):
    _name='is.comparatif.tarif.commande'
    _order='product_id'
    _auto = False

    sale_id         = fields.Many2one('sale.order', 'Commande')
    partner_id      = fields.Many2one('res.partner', 'Client')
    product_id      = fields.Many2one('product.template', 'Article')
    is_category_id  = fields.Many2one('is.category', 'Catégorie')
    prix_commande   = fields.Float('Prix Commande')
    prix_liste_prix = fields.Float('Prix Liste de prix')
    delta           = fields.Float('Delta')

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_comparatif_tarif_commande')
        cr.execute("""

CREATE OR REPLACE FUNCTION is_prix_vente(pricelistid integer, productid integer, qt float, date date) RETURNS float AS $$
BEGIN
    RETURN (
        select price_surcharge 
        from product_pricelist ppl inner join product_pricelist_version ppv on ppv.pricelist_id=ppl.id 
                                   inner join product_pricelist_item    ppi on ppi.price_version_id=ppv.id
        where ppi.product_id=productid
            and ppl.id=pricelistid
            and min_quantity>=qt
            and ppl.type='sale' and ppl.active='t'
            and (ppv.date_end   is null or ppv.date_end   >= date) 
            and (ppv.date_start is null or ppv.date_start <= date) 

            and (ppi.date_end   is null or ppi.date_end   >= date) 
            and (ppi.date_start is null or ppi.date_start <= date) 
        order by ppi.sequence limit 1
    );
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE view is_comparatif_tarif_commande AS (
    SELECT 
        sol.id               as id,
        so.id                as sale_id,
        pt.id                as product_id,
        so.partner_id        as partner_id,
        pt.is_category_id    as is_category_id,
        sol.price_unit       as prix_commande,
        is_prix_vente(so.pricelist_id,pp.id,sol.product_uom_qty,sol.is_date_livraison) as prix_liste_prix,
        round(cast(abs(is_prix_vente(so.pricelist_id,pp.id,sol.product_uom_qty,sol.is_date_livraison)-sol.price_unit) as numeric),4) as delta


    FROM sale_order_line sol inner join sale_order       so on sol.order_id=so.id
                             inner join product_product  pp on sol.product_id=pp.id
                             inner join product_template pt on pp.product_tmpl_id=pt.id
                             inner join is_category      ic on pt.is_category_id=ic.id
    WHERE so.state='draft' and sol.state='draft' 
          and sol.price_unit!=is_prix_vente(so.pricelist_id,pp.id,sol.product_uom_qty,sol.is_date_livraison)
         
)

        """)


