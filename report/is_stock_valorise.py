# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_stock_valorise(models.Model):
    _name='is.stock.valorise'
    _order='is_code'
    _auto = False

    product_id         = fields.Many2one('product.template', 'Article')
    is_code            = fields.Char('Code Article')
    designation        = fields.Char('Désignation')
    is_category_id     = fields.Many2one('is.category'       , 'Catégorie')
    is_gestionnaire_id = fields.Many2one('is.gestionnaire'   , 'Gestionnaire')
    segment_id         = fields.Many2one('is.product.segment', 'Segment')
    uom_id             = fields.Many2one('product.uom'       , 'Unité')
    stock_a            = fields.Float('Stock A')
    stock_q            = fields.Float('Stock Q')
    stock              = fields.Float('Stock Total')
    cout_act_matiere   = fields.Float("Coût act matière"       , digits=(12, 4))
    cout_act_machine   = fields.Float("Coût act machine"       , digits=(12, 4))
    cout_act_mo        = fields.Float("Coût act main d'oeuvre" , digits=(12, 4))
    cout_act_st        = fields.Float("Coût act sous-traitance", digits=(12, 4))
    cout_act_total     = fields.Float("Coût act Total"         , digits=(12, 4))
    stock_valorise     = fields.Float('Stock Valorisé'         , digits=(12, 4))

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_stock_valorise')
        cr.execute("""

            CREATE OR REPLACE FUNCTION is_stocka(pp_id integer) RETURNS float AS $$
            BEGIN
                RETURN (
                        select sum(qty) 
                        from stock_quant sq inner join stock_location sl on sq.location_id=sl.id 
                        where sl.usage='internal' 
                              and (sl.control_quality is null or sl.control_quality='f')
                              and sq.product_id=pp_id
                );
            END;
            $$ LANGUAGE plpgsql;

            CREATE OR REPLACE FUNCTION is_stockq(pp_id integer) RETURNS float AS $$
            BEGIN
                RETURN (
                        select sum(qty) 
                        from stock_quant sq inner join stock_location sl on sq.location_id=sl.id 
                        where sl.usage='internal' 
                              and sl.control_quality='t'
                              and sq.product_id=pp_id
                );
            END;
            $$ LANGUAGE plpgsql;

            CREATE OR REPLACE FUNCTION is_stock(pp_id integer) RETURNS float AS $$
            BEGIN
                RETURN (
                        select sum(qty) 
                        from stock_quant sq inner join stock_location sl on sq.location_id=sl.id 
                        where sl.usage='internal' 
                              and sq.product_id=pp_id
                );
            END;
            $$ LANGUAGE plpgsql;

            CREATE OR REPLACE view is_stock_valorise AS (
                SELECT 
                    pt.id                 as id,
                    pt.id                 as product_id,
                    pt.is_code            as is_code,
                    pt.name               as designation,
                    pt.is_category_id     as is_category_id,
                    pt.is_gestionnaire_id as is_gestionnaire_id,
                    pt.segment_id         as segment_id,
                    pt.uom_id             as uom_id,
                    is_stocka(pp.id)      as stock_a,
                    is_stockq(pp.id)      as stock_q,
                    is_stock(pp.id)       as stock,
                    cout_act_matiere,
                    cout_act_machine,
                    cout_act_mo,
                    cout_act_st,
                    cout_act_total,
                    is_stock(pp.id) * cout_act_total as stock_valorise
                FROM product_template pt inner join product_product          pp on pp.product_tmpl_id=pt.id
                                         left outer join is_category         ic on pt.is_category_id=ic.id
                                         left outer join is_gestionnaire     ig on pt.is_gestionnaire_id=ig.id
                                         left outer join is_product_segment ips on pt.segment_id=ips.id
                                         left outer join is_cout           cout on cout.name=pp.id
                WHERE pt.active='t'
                      and ic.name::int<70
            )
        """)

