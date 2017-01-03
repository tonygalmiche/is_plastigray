# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_stock_quant(models.Model):
    _name='is.stock.quant'
    _order='product_id,location_id,lot'
    _auto = False

    product_id         = fields.Many2one('product.template', 'Article')
    gestionnaire_id    = fields.Many2one('is.gestionnaire' , 'Gestionnaire')
    category_id        = fields.Many2one('is.category'     , 'Catégorie')
    moule              = fields.Char('Moule')
    dossierf           = fields.Char('Dossier F')
    client_id          = fields.Many2one('res.partner', 'Client')
    ref_client         = fields.Char('Référence Client')
    ref_fournisseur    = fields.Char('Référence Fournisseur')
    location_id        = fields.Many2one('stock.location'     , 'Emplacement')
    lot                = fields.Char('Lot')
    lot_fournisseur    = fields.Char('Lot fournisseur')
    quantite           = fields.Float('Quantité')
    uom_id             = fields.Many2one('product.uom', 'Unité')
    date_entree        = fields.Datetime("Date d'entrée")


    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_stock_quant')
        cr.execute("""
            CREATE OR REPLACE view is_stock_quant AS (
                select 
                    sq.id                  id,
                    pt.id                  product_id, 
                    pt.is_gestionnaire_id  gestionnaire_id,
                    pt.is_category_id      category_id,
                    im.name                moule,
                    id.name                dossierf,
                    pt.is_ref_client       ref_client,
                    pt.is_ref_fournisseur  ref_fournisseur,
                    sq.location_id         location_id,
                    spl.name               lot,
                    spl.is_lot_fournisseur lot_fournisseur,
                    sq.qty                quantite, 
                    pt.uom_id             uom_id,
                    in_date               date_entree,
                    (   select client_id 
                        from is_product_client ipc
                        where ipc.product_id=pt.id and ipc.client_defaut='t' limit 1) client_id
                from stock_quant sq inner join product_product            pp on sq.product_id=pp.id
                                    inner join product_template           pt on pp.product_tmpl_id=pt.id
                                    left outer join stock_production_lot spl on sq.lot_id=spl.id
                                    left outer join is_mold               im on pt.is_mold_id=im.id
                                    left outer join is_dossierf           id on pt.is_dossierf_id=id.id
            )
        """)



