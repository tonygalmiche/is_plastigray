# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_comparatif_tarif_cial_vente(models.Model):
    _name='is.comparatif.tarif.cial.vente'
    _order='is_code'
    _auto = False

    tarif_cial_id  = fields.Many2one('is.tarif.cial', 'Tarif commercial')
    partner_id     = fields.Many2one('res.partner', 'Client')
    product_id     = fields.Many2one('product.template', 'Article')
    is_code        = fields.Char('Code Article')
    is_category_id = fields.Many2one('is.category', 'Catégorie')
    designation    = fields.Char('Désignation')
    tarif_cial     = fields.Float('Prix de vente tarif commercial', digits=(12, 4))
    tarif_vente    = fields.Float('Prix de vente liste de prix'   , digits=(12, 4))
    delta          = fields.Float('Delta'                         , digits=(12, 4))



#CREATE OR REPLACE FUNCTION is_prix_vente(pp_id integer) RETURNS float AS $$
#BEGIN
#    RETURN (
#        select price_surcharge 
#        from product_pricelist ppl inner join product_pricelist_version ppv on ppv.pricelist_id=ppl.id 
#                                   inner join product_pricelist_item    ppi on ppi.price_version_id=ppv.id
#        where ppi.product_id=pp_id
#            and ppl.type='sale' and ppl.active='t'
#            and (ppv.date_end   is null or ppv.date_end   >= CURRENT_DATE) 
#            and (ppv.date_start is null or ppv.date_start <= CURRENT_DATE) 

#            and (ppi.date_end   is null or ppi.date_end   >= CURRENT_DATE) 
#            and (ppi.date_start is null or ppi.date_start <= CURRENT_DATE) 
#        order by ppi.sequence limit 1
#    );
#END;
#$$ LANGUAGE plpgsql;


    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_comparatif_tarif_cial_vente')
        cr.execute("""

CREATE OR REPLACE view is_comparatif_tarif_cial_vente AS (
    SELECT 
        itc.id               as id,
        itc.id               as tarif_cial_id,
        itc.product_id       as product_id,
        itc.partner_id       as partner_id,
        pt.is_code           as is_code,
        pt.is_category_id    as is_category_id,
        pt.name              as designation,
        itc.prix_vente       as tarif_cial,
        coalesce(is_prix_vente(pp.id),0) as tarif_vente,
        round(cast(abs(coalesce(is_prix_vente(pp.id),0)-itc.prix_vente) as numeric),4) as delta
    FROM is_tarif_cial itc   inner join product_template   pt on itc.product_id=pt.id
                             inner join is_category        ic on pt.is_category_id=ic.id
                             inner join product_product    pp on pp.product_tmpl_id=pt.id 
                             inner join is_product_client ipc on pt.id=ipc.product_id and itc.partner_id=ipc.client_id
    WHERE pt.active='t' and itc.indice_prix=999 and
          cast(abs(coalesce(is_prix_vente(pp.id),0)-itc.prix_vente) as numeric)>0
)

        """)






#            CREATE OR REPLACE view is_comparatif_tarif_cial_vente AS (
#                SELECT 
#                    itc.id            as id,
#                    itc.id            as tarif_cial_id,
#                    itc.product_id    as product_id,
#                    itc.partner_id    as partner_id,
#                    pt.is_code        as is_code,
#                    pt.is_category_id as is_category_id,
#                    pt.name           as designation,
#                    itc.prix_vente    as tarif_cial,
#                    (   select count(ppv.id) 
#                        from product_pricelist ppl inner join product_pricelist_version ppv on ppv.pricelist_id=ppl.id
#                        where ppl.id>0 and ppl.type='sale' and ppl.active='t'
#                    ) as tarif_vente 
#                FROM is_tarif_cial itc   inner join product_template pt on itc.product_id=pt.id
#                                         inner join is_category ic          on pt.is_category_id=ic.id
#                WHERE pt.active='t' and itc.indice_prix=999
#            )


