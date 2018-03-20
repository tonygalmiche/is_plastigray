# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_stock_quant(models.Model):
    _name='is.stock.quant'
    _order='product_id,location_id,lot'
    _auto = False

    product_id         = fields.Many2one('product.template', 'Article')
    code_pg            = fields.Char('Code PG')
    designation        = fields.Char('Désignation')
    gestionnaire_id    = fields.Many2one('is.gestionnaire' , 'Gestionnaire')
    category_id        = fields.Many2one('is.category'     , 'Catégorie')
    moule              = fields.Char('Moule')
    client_id          = fields.Many2one('res.partner', 'Client')
    ref_client         = fields.Char('Référence Client')
    ref_fournisseur    = fields.Char('Référence Fournisseur')
    location_id        = fields.Many2one('stock.location'     , 'Emplacement')
    emplacement        = fields.Char('Emplacement')
    lot                = fields.Char('Lot')
    lot_fournisseur    = fields.Char('Lot fournisseur')
    quantite           = fields.Float('Quantité', digits=(16,6))
    uom_id             = fields.Many2one('product.uom', 'Unité')
    date_entree        = fields.Datetime("Date d'entrée")


    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_stock_quant')
        cr.execute("""
            CREATE OR REPLACE view is_stock_quant AS (

                select
                    max(isq.id) as id,
                    isq.product_id, 
                    isq.code_pg,
                    isq.designation,
                    isq.gestionnaire_id,
                    isq.category_id,
                    isq.moule,
                    isq.ref_client,
                    isq.ref_fournisseur,
                    isq.location_id,
                    isq.emplacement,
                    isq.lot,
                    isq.lot_fournisseur,
                    sum(isq.quantite) as quantite, 
                    isq.uom_id,
                    max(isq.date_entree) as date_entree,
                    isq.client_id
                from (

                    select 
                        sq.id                  id,
                        pt.id                  product_id, 
                        pt.is_code             code_pg,
                        pt.name                designation,
                        pt.is_gestionnaire_id  gestionnaire_id,
                        pt.is_category_id      category_id,
                        pt.is_mold_dossierf    moule,
                        pt.is_ref_client       ref_client,
                        pt.is_ref_fournisseur  ref_fournisseur,
                        sq.location_id         location_id,
                        sl.name                emplacement,
                        spl.name               lot,
                        spl.is_lot_fournisseur lot_fournisseur,
                        sq.qty                 quantite, 
                        pt.uom_id              uom_id,
                        in_date                date_entree,
                        pt.is_client_id        client_id
                    from stock_quant sq inner join product_product            pp on sq.product_id=pp.id
                                        inner join product_template           pt on pp.product_tmpl_id=pt.id
                                        inner join stock_location             sl on sq.location_id=sl.id
                                        left outer join stock_production_lot spl on sq.lot_id=spl.id
                    where sl.usage='internal'
                ) isq
                group by
                    isq.product_id, 
                    isq.code_pg,
                    isq.designation,
                    isq.gestionnaire_id,
                    isq.category_id,
                    isq.moule,
                    isq.ref_client,
                    isq.ref_fournisseur,
                    isq.location_id,
                    isq.emplacement,
                    isq.lot,
                    isq.lot_fournisseur,
                    isq.uom_id,
                    isq.client_id
            )
        """)



