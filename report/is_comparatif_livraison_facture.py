# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_comparatif_livraison_facture(models.Model):
    _name='is.comparatif.livraison.facture'
    _order='invoice_id,product_id'
    _auto = False

    invoice_id         = fields.Many2one('account.invoice', 'Facture')
    internal_number    = fields.Char('N°Facture')
    state              = fields.Char('Etat Facture')
    picking_id         = fields.Many2one('stock.picking', 'Livraison')
    partner_id         = fields.Many2one('res.partner', 'Client')
    product_id         = fields.Many2one('product.product', 'Article')
    product_uom             = fields.Many2one('product.uom', 'Unité Livraison')
    uos_id             = fields.Many2one('product.uom', 'Unité Facture')
    product_uom_qty           = fields.Float('Quantité Livraison')
    quantity           = fields.Float('Quantité Facture')

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_comparatif_livraison_facture')
        cr.execute("""

CREATE OR REPLACE view is_comparatif_livraison_facture AS (
    select 
        ail.id,
        ail.invoice_id,
        ai.internal_number,
        ai.state,
        sm.picking_id,
        ai.partner_id,
        ail.product_id,
        sm.product_uom,
        ail.uos_id,
        sm.product_uom_qty,
        ail.quantity
    from account_invoice_line ail inner join account_invoice ai on ail.invoice_id=ai.id
                                  inner join stock_move      sm on ail.is_move_id=sm.id
    where ai.type='out_invoice' and (ail.uos_id!=sm.product_uom or ail.quantity!=sm.product_uom_qty)
)
        """)


