# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_suivi_budget_analytique(models.Model):
    _name='is.suivi.budget.analytique'
    _order='id desc'
    _auto = False

    product_id              = fields.Many2one('product.product', 'Article')
    move_id                 = fields.Many2one('stock.move'     , 'Mouvement de stock')
    order_id                = fields.Many2one('purchase.order' , 'Commande')
    partner_id              = fields.Many2one('res.partner'    , 'Fournisseur')
    account                 = fields.Char('Compte')
    section                 = fields.Char('Section analytique')
    account_section         = fields.Char('Compte-Section')
    date_planned            = fields.Date("Date prévue")
    montant                 = fields.Float('Montant'           , digits=(14,2))
    product_uom_qty         = fields.Float('Quantité'          , digits=(14,4))
    price_unit              = fields.Float('Prix unitaire'     , digits=(14,4))
    pol_uom                 = fields.Many2one('product.uom', 'Unité commande')
    sm_uom                  = fields.Many2one('product.uom', 'Unité réception')
    coef                    = fields.Float('Coeficient'        , digits=(14,4))

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_suivi_budget_analytique')
        cr.execute("""
            CREATE OR REPLACE FUNCTION get_account_expense(pt_id integer) RETURNS integer AS $$
            BEGIN
                RETURN (
                    select aa.code
                    from (
                        select substring(value_reference, 17)::int account_id
                        from ir_property ip 
                        where ip.name='property_account_expense' and res_id=concat('product.template,',pt_id)
                        limit 1
                    ) property inner join account_account aa on account_id=aa.id
                );
            END;
            $$ LANGUAGE plpgsql;

            CREATE OR REPLACE view is_suivi_budget_analytique AS (
                select 
                    sm.id,
                    sm.product_id              product_id,
                    sm.id                      move_id,
                    po.id                      order_id,
                    po.partner_id              partner_id,
                    get_account_expense(pt.id) account,
                    isa.name                   section,
                    concat(get_account_expense(pt.id),'-',isa.name) account_section,
                    pol.date_planned           date_planned,
                    sm.product_uom_qty*pol.price_unit*is_unit_coef(pol.product_uom, sm.product_uom)  as montant,
                    sm.product_uom_qty*is_unit_coef(pol.product_uom, sm.product_uom) product_uom_qty,
                    pol.price_unit  price_unit,
                    pol.product_uom pol_uom,
                    sm.product_uom  sm_uom,
                    is_unit_coef(pol.product_uom, sm.product_uom) coef

                from stock_picking sp inner join stock_move                sm on sm.picking_id=sp.id 
                                      inner join product_product           pp on sm.product_id=pp.id
                                      inner join product_template          pt on pp.product_tmpl_id=pt.id
                                      inner join is_section_analytique    isa on pt.is_section_analytique_id=isa.id
                                      left outer join purchase_order       po on sp.is_purchase_order_id=po.id
                                      left outer join purchase_order_line pol on sm.purchase_line_id=pol.id
                where 
                    sp.picking_type_id=1 and 
                    sp.invoice_state='2binvoiced'
            )
        """)


