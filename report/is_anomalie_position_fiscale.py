# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_anomalie_position_fiscale(models.Model):
    _name='is.anomalie.position.fiscale'
    _order='partner_id,order_id'
    _auto = False

    order_id                = fields.Many2one('purchase.order', 'Commande')
    partner_id              = fields.Many2one('res.partner', 'Fournisseur')
    product_id              = fields.Many2one('product.template', 'Article')
    product_uom             = fields.Many2one('product.uom', 'Unité Cde')
    product_qty_uom_po      = fields.Float('Qt Cde (UA)'  , digits=(14,3))
    qt_rcp                  = fields.Float('Qt Rcp (UA)'  , digits=(14,3))
    qt_reste                = fields.Float('Qt Reste (UA)', digits=(14,3))
    position_id             = fields.Many2one('account.fiscal.position', 'Position fiscale Fournisseur')
    fiscal_position         = fields.Many2one('account.fiscal.position', 'Position fiscale Commande')

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_anomalie_position_fiscale')
        cr.execute("""
            CREATE OR REPLACE FUNCTION get_account_position_id(rp_id integer) RETURNS integer AS $$
            BEGIN
                RETURN (
                    select substring(value_reference, 25)::int account_position_id
                    from ir_property ip 
                    where ip.name='property_account_position' and res_id=concat('res.partner,',rp_id)
                    limit 1

                );
            END;
            $$ LANGUAGE plpgsql;

            CREATE OR REPLACE view is_anomalie_position_fiscale AS (
                select 
                    ipol.id, 
                    ipol.order_id,
                    ipol.partner_id, 
                    ipol.product_id, 
                    ipol.product_uom,
                    ipol.product_qty_uom_po, 
                    ipol.qt_rcp , 
                    ipol.qt_reste, 
                    get_account_position_id(rp.id) position_id,
                    po.fiscal_position
                from is_purchase_order_line ipol inner join res_partner    rp on ipol.partner_id=rp.id
                                                 inner join purchase_order po on ipol.order_id=po.id
                where 
                    ipol.qt_reste>0 and 
                    coalesce(po.fiscal_position,0)!=coalesce(get_account_position_id(rp.id),0)
            );
        """)

