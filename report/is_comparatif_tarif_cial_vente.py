# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_comparatif_tarif_cial_vente(models.Model):
    _name='is.comparatif.tarif.cial.vente'
    _order='is_code'
    _auto = False

    product_id     = fields.Many2one('product.template', 'Article')
    is_code        = fields.Char('Code Article')
    designation    = fields.Char('Désignation')
    is_category_id = fields.Many2one('is.category', 'Catégorie')
    partner_id     = fields.Many2one('res.partner', 'Client')
    pricelist_id   = fields.Many2one('product.pricelist', 'Liste de prix')
    lot_livraison  = fields.Integer('Lot de livraison')
    tarif_cial     = fields.Float('Prix de vente tarif commercial', digits=(12, 4))
    tarif_vente    = fields.Float('Prix de vente liste de prix'   , digits=(12, 4))

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_comparatif_tarif_cial_vente')
        cr.execute("""

CREATE OR REPLACE FUNCTION get_tarif_cial(productid integer, partnercode char) RETURNS float AS $$
BEGIN
    RETURN (
        select itc.prix_vente 
        from is_tarif_cial itc inner join res_partner rp on itc.partner_id=rp.id
        where itc.product_id=productid and rp.is_code=partnercode and itc.indice_prix=999 limit 1
    );
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE view is_comparatif_tarif_cial_vente AS (
    select
        pt.id                as id,
        pt.id                as product_id,
        pt.is_code           as is_code,
        pt.name              as designation,
        pt.is_category_id    as is_category_id,
        pt.is_client_id      as partner_id,
        get_product_pricelist(pt.is_client_id)    as pricelist_id,
        get_lot_livraison(pt.id, pt.is_client_id) as lot_livraison,
        coalesce(get_tarif_cial(pt.id,rp.is_code),0) as tarif_cial,
        coalesce(is_prix_vente(get_product_pricelist(pt.is_client_id), pp.id, get_lot_livraison(pt.id, pt.is_client_id), CURRENT_DATE),0) as tarif_vente
    from product_template pt inner join product_product pp on pp.product_tmpl_id=pt.id
                             inner join res_partner     rp on pt.is_client_id=rp.id
    where 
        pt.active='t' and 
        coalesce(get_tarif_cial(pt.id,rp.is_code),0)<>coalesce(is_prix_vente(get_product_pricelist(pt.is_client_id), pp.id, get_lot_livraison(pt.id, pt.is_client_id), CURRENT_DATE),0)
    order by pt.is_code
)

        """)

