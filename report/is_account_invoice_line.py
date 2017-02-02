# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_account_invoice_line(models.Model):
    _name='is.account.invoice.line'
    _order='id desc'
    _auto = False

    partner_id              = fields.Many2one('res.partner', 'Partenaire')
    invoice_id              = fields.Many2one('account.invoice', 'Facture')
    date_invoice            = fields.Date("Date facture")
    internal_number         = fields.Char('N°Facture')
    date_due                = fields.Date("Date d'échéance")
    origin                  = fields.Char('Origine')
    supplier_invoice_number = fields.Char('Numéro de facture fournisseur')
    state                   = fields.Char('Etat facture')
    type                    = fields.Char('Type')
    product_id              = fields.Many2one('product.product', 'Article')
    description             = fields.Char('Description')
    quantity                = fields.Float('Quantité', digits=(14,2))
    uos_id                  = fields.Many2one('product.uom', 'Unité')
    price_unit              = fields.Float('Prix unitaire', digits=(14,4))
    total                   = fields.Float('Montant Total', digits=(14,2))

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
                    ail.name description,
                    ail.quantity,
                    ail.uos_id,
                    price_unit,
                    (ail.quantity*price_unit) total
                from account_invoice ai inner join account_invoice_line ail on ai.id=ail.invoice_id
                where ai.id>0
                order by ail.id desc
            )
        """)






