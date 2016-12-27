# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_purchase_order_line(models.Model):
    _name='is.purchase.order.line'
    _order='id desc'
    _auto = False

    order_id             = fields.Many2one('purchase.order', 'Commande')
    partner_id           = fields.Many2one('res.partner', 'Fournisseur')
    date_order           = fields.Date('Date de commande')
    minimum_planned_date = fields.Date('Date prévue entête')
    is_date_confirmation = fields.Date('Date de confirmation')
    product_id           = fields.Many2one('product.template', 'Article')
    is_ref_fournisseur   = fields.Char('Référence fournisseur')
    date_planned         = fields.Date('Date prévue ligne')
    product_qty          = fields.Float('Quantité', digits=(14,4))
    product_uom          = fields.Many2one('product.uom', 'Unité')
    price_unit           = fields.Float('Prix unitaire')
    is_justification     = fields.Char('Justifcation')


    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_purchase_order_line')
        cr.execute("""
            CREATE OR REPLACE view is_purchase_order_line AS (
                select  pol.id,
                        po.id                   as order_id,
                        po.partner_id           as partner_id, 
                        po.date_order,
                        po.minimum_planned_date,
                        po.is_date_confirmation,
                        pt.id                   as product_id, 
                        pt.is_ref_fournisseur   as is_ref_fournisseur,
                        pol.date_planned,
                        pol.product_qty,
                        pol.product_uom,
                        pol.price_unit,
                        pol.is_justification
                from purchase_order po inner join purchase_order_line pol on po.id=pol.order_id
                                       inner join product_product      pp on pol.product_id=pp.id
                                       inner join product_template     pt on pp.product_tmpl_id=pt.id
                where po.state!='draft' 
            )
        """)

