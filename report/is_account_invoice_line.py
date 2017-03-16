# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_account_invoice_line(models.Model):
    _name='is.account.invoice.line'
    _order='id desc'
    _auto = False

    partner_id              = fields.Many2one('res.partner', 'Client/Fournisseur')
    invoice_id              = fields.Many2one('account.invoice', 'Facture')
    date_invoice            = fields.Date("Date facture")
    internal_number         = fields.Char('N°Facture')
    date_due                = fields.Date("Date d'échéance")
    origin                  = fields.Char('Origine/BL')
    supplier_invoice_number = fields.Char('Numéro de facture fournisseur')
    state                   = fields.Char('Etat facture')
    type                    = fields.Char('Type')
    product_id              = fields.Many2one('product.product', 'Article')
    is_ref_client           = fields.Char('Référence client')
    description             = fields.Char('Description')
    quantity                = fields.Float('Quantité', digits=(14,2))
    uos_id                  = fields.Many2one('product.uom', 'Unité')
    price_unit              = fields.Float('Prix unitaire', digits=(14,4))
    total                   = fields.Float('Montant Total', digits=(14,2))
    move_id                 = fields.Many2one('stock.move', 'Mouvement de stock')
    picking_id              = fields.Many2one('stock.picking', 'Livraison')
    purchase_order_id       = fields.Many2one('purchase.order', 'Commande fournisseur')

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_account_invoice_line')
        cr.execute("""
            CREATE OR REPLACE view is_account_invoice_line AS (
                select 
                    ail.id,
                    ai.partner_id,
                    ai.id invoice_id,
                    ai.date_invoice,
                    ai.internal_number,
                    ai.date_due,
                    ai.origin,
                    ai.supplier_invoice_number,
                    ai.state,
                    ai.type,
                    ail.product_id,
                    pt.is_ref_client,
                    ail.name                  description,
                    ail.quantity,
                    ail.uos_id,
                    ail.price_unit,
                    (ail.quantity*ail.price_unit) total,
                    ail.is_move_id            move_id,
                    sm.picking_id             picking_id,
                    sp.is_purchase_order_id   purchase_order_id
                from account_invoice ai inner join account_invoice_line ail on ai.id=ail.invoice_id
                                        inner join product_product       pp on ail.product_id=pp.id
                                        inner join product_template      pt on pp.product_tmpl_id=pt.id
                                        left outer join stock_move       sm on ail.is_move_id=sm.id
                                        left outer join stock_picking    sp on sm.picking_id=sp.id

                where ai.id>0
                order by ail.id desc
            )
        """)






