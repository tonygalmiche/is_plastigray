# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_comparatif_cout_pk_tarif(models.Model):
    _name='is.comparatif.cout.pk.tarif'
    _order='product_id'
    _auto = False

    product_id           = fields.Many2one('product.template', 'Article')
    gest                 = fields.Char('Gest')
    lot_mini             = fields.Char("Lot d'appro")
    partner_id           = fields.Many2one('res.partner', 'Fournisseur')
    cout_id              = fields.Many2one('is.cout', 'Coût')
    cout_ma              = fields.Float(u'Coût machine', digits=(14,4))
    cout_mo              = fields.Float(u'Coût MO'     , digits=(14,4))
    cout_total           = fields.Float(u'Coût Total'  , digits=(14,4))
    prix_achat           = fields.Float(u'Tarif achat' , digits=(14,4))

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_comparatif_cout_pk_tarif')
        cr.execute("""
            CREATE OR REPLACE view is_comparatif_cout_pk_tarif AS (
                select
                    ic.id,
                    pt.id          product_id,
                    ig.name        gest,
                    pt.lot_mini    lot_mini,
                    rp.id          partner_id,
                    get_product_pricelist_purchase(rp.id) product_pricelist_purchase,
                    ic.id          cout_id,
                    (   select sum(ma.cout_total)
                        from is_cout_gamme_ma_pk ma
                        where ma.cout_id=ic.id
                    ) cout_ma,
                    (   select sum(mo.cout_total)
                        from is_cout_gamme_mo_pk mo
                        where mo.cout_id=ic.id
                    ) cout_mo,
                    (
                        (   select sum(ma.cout_total)
                            from is_cout_gamme_ma_pk ma
                            where ma.cout_id=ic.id
                        ) + 
                        (   select sum(mo.cout_total)
                            from is_cout_gamme_mo_pk mo
                            where mo.cout_id=ic.id
                        )
                    ) cout_total,
                    is_prix_achat(get_product_pricelist_purchase(rp.id),pp.id, pt.lot_mini/is_unit_coef(pt.uom_id, pt.uom_po_id),CURRENT_DATE)/is_unit_coef(pt.uom_id, pt.uom_po_id) prix_achat
                from is_cout ic inner join product_product  pp on ic.name=pp.id
                                inner join product_template pt on pp.product_tmpl_id=pt.id
                                inner join res_partner      rp on pt.is_fournisseur_id=rp.id
                                inner join is_gestionnaire  ig on pt.is_gestionnaire_id=ig.id
                where 
                    rp.is_code='7504' and 
                    pt.active='t' and
                    round(abs(
                        (   select sum(ma.cout_total)
                            from is_cout_gamme_ma_pk ma
                            where ma.cout_id=ic.id
                        ) + 
                        (   select sum(mo.cout_total)
                            from is_cout_gamme_mo_pk mo
                            where mo.cout_id=ic.id
                        ) -
                        (
                            COALESCE(
                                is_prix_achat(get_product_pricelist_purchase(rp.id),pp.id, pt.lot_mini/is_unit_coef(pt.uom_id, pt.uom_po_id),CURRENT_DATE)/is_unit_coef(pt.uom_id, pt.uom_po_id),
                                0
                            )
                        )
                    )::numeric,4)>0
            )
        """)

