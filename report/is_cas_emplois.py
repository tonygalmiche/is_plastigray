# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_cas_emplois(models.Model):
    _name='is.cas.emplois'
    _order='bom_id,sequence'
    _auto = False

    bom_id             = fields.Many2one('mrp.bom', 'Nomenclature mère')
    is_mold_id         = fields.Many2one('is.mold', 'Moule', related='bom_id.product_tmpl_id.is_mold_id', readonly=True)
    is_sous_traitance  = fields.Boolean('Nomenclature de sous-traitance')
    is_negoce          = fields.Boolean('Nomenclature de négoce')
    is_inactive        = fields.Boolean('Nomenclature inactive')
    sequence           = fields.Integer('Sequence')
    product_id         = fields.Many2one('product.product', 'Article')
    type               = fields.Selection([('normal', 'Normal'), ('phantom', 'Fantôme')], 'Type de composant')
    is_article_fourni  = fields.Selection([('oui', 'Oui'), ('non', 'Non')], 'Article fourni')
    product_qty        = fields.Float('Quantité')
    product_uom        = fields.Many2one('product.uom', 'Article')
    date_start         = fields.Date('Valide du')
    date_stop         = fields.Date("Valide jusqu'au")

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_cas_emplois')
        cr.execute("""
            CREATE OR REPLACE view is_cas_emplois AS (
                SELECT 
                    mbl.id                  as id,
                    mbl.bom_id              as bom_id,
                    mb.is_sous_traitance    as is_sous_traitance,
                    mb.is_negoce            as is_negoce,
                    mb.is_inactive          as is_inactive,
                    mbl.sequence            as sequence,
                    mbl.product_id          as product_id,
                    mbl.type                as type,
                    mbl.is_article_fourni   as is_article_fourni,
                    mbl.product_qty         as product_qty,
                    mbl.product_uom         as product_uom,
                    mbl.date_start          as date_start,
                    mbl.date_stop           as date_stop
                FROM mrp_bom_line mbl inner join mrp_bom mb on mbl.bom_id=mb.id
                WHERE mbl.id>0 
            )
        """)





