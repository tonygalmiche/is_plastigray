# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_comparatif_lot_appro_prix(models.Model):
    _name='is.comparatif.lot.appro.prix'
    _order='product_id'
    _auto = False

    product_id             = fields.Many2one('product.template', 'Article')
    is_category_id         = fields.Many2one('is.category', 'Catégorie')
    partner_id             = fields.Many2one('res.partner', 'Fournisseur')
    pricelist_id           = fields.Many2one('product.pricelist', 'Liste de prix')
    uom_id                 = fields.Many2one('product.uom', 'US')
    uom_po_id              = fields.Many2one('product.uom', 'UA')
    coef                   = fields.Float('US/UA')
    lot_mini_product       = fields.Float("Lot d'appro.")
    min_quantity_pricelist = fields.Float("Mini liste de prix")


    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_comparatif_lot_appro_prix')
        cr.execute("""
            CREATE OR REPLACE FUNCTION get_product_pricelist_purchase(partner_id integer) RETURNS integer AS $$
            BEGIN
                RETURN (
                    select substring(value_reference, 19)::int pricelist_id
                    from ir_property ip 
                    where ip.name='property_product_pricelist_purchase' and res_id=concat('res.partner,',partner_id)
                    limit 1
                );
            END;
            $$ LANGUAGE plpgsql;

            CREATE OR REPLACE view is_comparatif_lot_appro_prix AS (
                select
                    pt.id         id,
                    pt.id         product_id,
                    ic.id         is_category_id,
                    pt_tmp2.partner_id,
                    get_product_pricelist_purchase(pt_tmp2.partner_id) pricelist_id,
                    pt.uom_id,
                    pt.uom_po_id,
                    is_unit_coef(pt.uom_id, pt.uom_po_id) coef,
                    pt.lot_mini lot_mini_product,
                    (
                        select ppi.min_quantity
                        from product_pricelist_version ppv inner join product_pricelist_item ppi on ppv.id=ppi.price_version_id
                        where 
                            ppv.pricelist_id=get_product_pricelist_purchase(pt_tmp2.partner_id) and
                            ppi.product_id=pp.id and 
                            (ppv.date_end   is null or ppv.date_end   >= CURRENT_DATE) and 
                            (ppv.date_start is null or ppv.date_start <= CURRENT_DATE) and 
                            (ppi.date_end   is null or ppi.date_end   >= CURRENT_DATE) and 
                            (ppi.date_start is null or ppi.date_start <= CURRENT_DATE) and 
                            ppi.min_quantity*is_unit_coef(pt.uom_id, pt.uom_po_id)<=pt.lot_mini
                        order by ppi.product_id, ppi.min_quantity desc limit 1
                    )*is_unit_coef(pt.uom_id, pt.uom_po_id) min_quantity_pricelist
                from (
                    select
                        pt_tmp1.id,
                        (
                            select name from product_supplierinfo ps where ps.product_tmpl_id=pt_tmp1.id limit 1
                        ) partner_id
                    from product_template pt_tmp1
                ) pt_tmp2                   inner join product_template pt on pt_tmp2.id = pt.id
                                            inner join product_product  pp         on pp.product_tmpl_id=pt.id
                                            left outer join is_category         ic on pt.is_category_id=ic.id
                                            left outer join is_gestionnaire     ig on pt.is_gestionnaire_id=ig.id
                                            left outer join is_product_famille ipf on pt.family_id=ipf.id
                                            left outer join is_product_segment ips on pt.segment_id=ips.id
                where pt.purchase_ok='t' and ic.name::int<70 and pt.active='t'
            )

        """)



