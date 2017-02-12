# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_res_partner(models.Model):
    _name='is.res.partner'
    _order='partner_id'
    _auto = False

    partner_id            = fields.Many2one('res.partner'     , 'Fournisseur')
    segment_id            = fields.Many2one('is.segment.achat', 'Segment')
    cde_ouverte_id        = fields.Many2one('is.cde.ouverte.fournisseur', 'Commande prévisionnelle')
    cde_ferme_cadencee_id = fields.Many2one('is.cde.ferme.cadencee', 'Commande ferme cadencée')
    supplier              = fields.Boolean('Est un fournisseur')
    customer              = fields.Boolean('Est un client')

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_res_partner')
        cr.execute("""
            CREATE OR REPLACE view is_res_partner AS (
                select
                    rp.id,
                    rp.id               partner_id,
                    rp.is_segment_achat segment_id,
                    rp.supplier,
                    rp.customer,
                    isa.name,
                    (
                        select icof.id
                        from is_cde_ouverte_fournisseur icof
                        where icof.partner_id=rp.id
                        limit 1
                    ) cde_ouverte_id,

                    (
                        select icfc.id
                        from is_cde_ferme_cadencee icfc
                        where icfc.partner_id=rp.id
                        limit 1
                    ) cde_ferme_cadencee_id
                from res_partner rp  left outer join is_segment_achat isa on rp.is_segment_achat=isa.id
                where is_company='t' and active='t' and isa.name not in ('frais généraux','mouliste','Transport')
            )
        """)




