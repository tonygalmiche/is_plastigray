# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_comparatif_tarif_cial_vente(models.Model):
    _name='is.comparatif.tarif.cial.vente'
    _order='pricelist_id, version_id, sequence, product_id'
    _auto = False

    pricelist_id       = fields.Many2one('product.pricelist', 'Liste de prix')
    partner_id         = fields.Many2one('res.partner', 'Client')
    version_id         = fields.Many2one('product.pricelist.version', 'Version')
    version_date_start = fields.Date('Date début version')
    version_date_end   = fields.Date('Date fin version')
    product_id         = fields.Many2one('product.template', 'Article')
    is_category_id     = fields.Many2one('is.category', 'Catégorie')
    item_date_start    = fields.Date('Date début ligne')
    item_date_end      = fields.Date('Date fin ligne')
    sequence           = fields.Integer('Séquence')
    min_quantity       = fields.Float('Quantité min.', digits=(12, 4))
    prix_vente         = fields.Float('Prix de vente', digits=(12, 4))
    tarif_cial         = fields.Float('Tarif cial'   , digits=(12, 4))


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
                    ppi.id,
                    ppl.id            pricelist_id,
                    rp.id             partner_id,
                    ppv.id            version_id,
                    ppv.date_start    version_date_start,
                    ppv.date_end      version_date_end,
                    pt.id             product_id,
                    pt.is_category_id is_category_id,
                    ppi.date_start    item_date_start,
                    ppi.date_end      item_date_end,
                    ppi.sequence,
                    ppi.min_quantity  min_quantity,
                    ppi.price_surcharge prix_vente,
                    get_tarif_cial(pt.id, rp.is_code) tarif_cial
                from product_pricelist ppl inner join product_pricelist_version ppv on ppl.id=ppv.pricelist_id
                                           inner join product_pricelist_item    ppi on ppv.id=ppi.price_version_id 
                                           inner join res_partner                rp on ppl.partner_id=rp.id 
                                           inner join product_product            pp on ppi.product_id=pp.id
                                           inner join product_template           pt on pp.product_tmpl_id=pt.id
                                           inner join is_category                ic on pt.is_category_id=ic.id
                where 
                    ppl.type='sale' and
                    ppl.active='t' and
                    ppv.active='t' and
                    (ppv.date_start<=CURRENT_DATE or ppv.date_start is null) and 
                    (ppv.date_end>=CURRENT_DATE or ppv.date_end is null) and
                    (ppi.date_start<=CURRENT_DATE or ppi.date_start is null) and 
                    (ppi.date_end>=CURRENT_DATE or ppi.date_end is null) and
                    ic.name<'40' and
                    get_tarif_cial(pt.id, rp.is_code)!=ppi.price_surcharge

                order by ic.name,ppl.name, ppv.name, pt.is_code
            )
        """)








#    select
#        pt.id                as id,
#        pt.id                as product_id,
#        pt.is_code           as is_code,
#        pt.name              as designation,
#        pt.is_category_id    as is_category_id,
#        pt.is_client_id      as partner_id,
#        get_product_pricelist(pt.is_client_id)    as pricelist_id,

#        get_lot_livraison(pt.id, pt.is_client_id) as lot_livraison,
#        coalesce(get_tarif_cial(pt.id,rp.is_code),0) as tarif_cial,
#        coalesce(is_prix_vente(get_product_pricelist(pt.is_client_id), pp.id, get_lot_livraison(pt.id, pt.is_client_id), CURRENT_DATE),0) as tarif_vente

#    from product_template pt inner join product_product pp on pp.product_tmpl_id=pt.id
#                             inner join res_partner     rp on pt.is_client_id=rp.id
#    where 
#        pt.active='t' and 

#        coalesce(get_tarif_cial(pt.id,rp.is_code),0)<>coalesce(is_prix_vente(get_product_pricelist(pt.is_client_id), pp.id, get_lot_livraison(pt.id, pt.is_client_id), CURRENT_DATE),0)
#    order by pt.is_code


