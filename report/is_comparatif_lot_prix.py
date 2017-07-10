# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_comparatif_lot_prix(models.Model):
    _name='is.comparatif.lot.prix'
    _order='product_id'
    _auto = False

    product_id           = fields.Many2one('product.template', 'Article')
    partner_id           = fields.Many2one('res.partner', 'Client')
    pricelist_id         = fields.Many2one('product.pricelist', 'Liste de prix')
    is_category_id       = fields.Many2one('is.category', 'Catégorie')
    mini_liste_prix      = fields.Float('Mini liste de prix')
    lot_livraison        = fields.Float('Lot de livraison')
    test_mini_liste_prix = fields.Float('Test Mini liste de prix')


    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_comparatif_lot_prix')
        cr.execute("""


CREATE OR REPLACE FUNCTION get_product_pricelist(partner_id integer) RETURNS integer AS $$
BEGIN
    RETURN (
        select substring(value_reference, 19)::int pricelist_id
        from ir_property ip 
        where ip.name='property_product_pricelist' and res_id=concat('res.partner,',partner_id)
        limit 1
    );
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION is_mini_liste_prix(productid integer, pricelistid integer) RETURNS float AS $$
BEGIN
    RETURN (
        select ppi.min_quantity
        from product_pricelist_version ppv inner join product_pricelist_item ppi on ppv.id=ppi.price_version_id
        where ppi.product_id=productid 
              and ppv.pricelist_id=pricelistid
              and (ppv.date_end   is null or ppv.date_end   >= CURRENT_DATE) 
              and (ppv.date_start is null or ppv.date_start <= CURRENT_DATE) 
              and (ppi.date_end   is null or ppi.date_end   >= CURRENT_DATE) 
              and (ppi.date_start is null or ppi.date_start <= CURRENT_DATE) 
        order by ppi.product_id, ppi.min_quantity limit 1
    );
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE view is_comparatif_lot_prix AS (
    select 
        ipc.id                    as id,
        pt.id                     as product_id, 
        rp.id                     as partner_id, 
        get_product_pricelist(rp.id) as pricelist_id,
        pt.is_category_id         as is_category_id, 
        is_mini_liste_prix(pp.id, get_product_pricelist(rp.id)) as mini_liste_prix,
        ipc.lot_livraison         as lot_livraison,
        round(cast(ipc.lot_livraison      / is_mini_liste_prix(pp.id, get_product_pricelist(rp.id)) as numeric),4)       as test_mini_liste_prix
    from is_product_client ipc inner join product_template pt on ipc.product_id=pt.id
                               inner join product_product  pp on pp.product_tmpl_id=pt.id
                               inner join res_partner rp      on ipc.client_id=rp.id
    where is_mini_liste_prix(pp.id, get_product_pricelist(rp.id))!=0
          and get_product_pricelist(rp.id) is not null
          and is_mini_liste_prix(pp.id, get_product_pricelist(rp.id)) is not null
          and (
            is_mini_liste_prix(pp.id, get_product_pricelist(rp.id))>ipc.lot_livraison 
            or
            round(cast(ipc.lot_livraison/is_mini_liste_prix(pp.id, get_product_pricelist(rp.id)) as numeric),0) != round(cast(ipc.lot_livraison/is_mini_liste_prix(pp.id, get_product_pricelist(rp.id)) as numeric),4) 
          )
)

        """)





