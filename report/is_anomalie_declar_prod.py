# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_anomalie_declar_prod(models.Model):
    _name='is.anomalie.declar.prod'
    _auto = False

    mp_id               = fields.Many2one('mrp.production', 'Ordre de fabrication')
    compose_id          = fields.Many2one('product.template', 'Article fabriqué')
    mp_state            = fields.Char('Etat')
    composant_id        = fields.Many2one('product.template', 'Composant')
    cat                 = fields.Char('Catégorie')

    mppl_is_bom_qty     = fields.Integer('Qt Lien nomenclature')
    mppl_product_qty    = fields.Integer('Qt Composant')
    qt_pf               = fields.Integer('Qt fabriquée')
    qt_rebuts           = fields.Integer('Qt Rebut')
    qt_composant        = fields.Integer('Qt Composant / Lien')


    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_anomalie_declar_prod')
        cr.execute("""
            CREATE OR REPLACE view is_anomalie_declar_prod AS (
                select
                    mp.id id,
                    mp.mp_id,
                    pt1.id                compose_id,
                    mp.mp_state,
                    pt2.id                composant_id,
                    ic.name               cat,
                    mp.mppl_is_bom_qty,
                    mp.mppl_product_qty,
                    mp.qt_pf,
                    mp.qt_rebuts,
                    mp.qt_composant
                from (
                    select
                        mppl.id            id,
                        mp.id              mp_id,
                        mp.product_id      mp_product_id,
                        mp.name            mp_name,
                        mp.state           mp_state,
                        mppl.product_id    mppl_product_id,
                        mppl.is_bom_qty    mppl_is_bom_qty,
                        round(mppl.product_qty)   mppl_product_qty,
                        round(
                            coalesce(
                                (
                                    select sum (sm1.product_qty)
                                    from stock_move sm1 inner join stock_location sl1 on sm1.location_dest_id=sl1.id
                                    where sm1.production_id=mp.id and sm1.state='done' and sl1.usage='internal'
                                ),0)
                            -
                            coalesce(
                                (
                                    select sum (sm1.product_qty)
                                    from stock_move sm1 inner join stock_location sl1 on sm1.location_id=sl1.id
                                    where sm1.production_id=mp.id and sm1.state='done' and sl1.usage='internal'
                                ),0)
                        ) qt_pf,
                        round(coalesce((
                            select sum (sm3.product_qty)
                            from stock_move sm3 inner join stock_location sl3 on sm3.location_dest_id=sl3.id
                            where sm3.production_id=mp.id and sm3.state='done' and sl3.scrap_location='t'
                        ),0)) qt_rebuts,
                        round(
                            (
                                coalesce(
                                    (
                                        select sum(sm2.product_qty)
                                        from stock_move sm2 inner join stock_location sl2 on sm2.location_id=sl2.id
                                                            inner join product_product pp3  on sm2.product_id=pp3.id 
                                                            inner join product_template pt3 on pp3.product_tmpl_id=pt3.id
                                        where 
                                            sm2.raw_material_production_id=mp.id and 
                                            sm2.product_id=mppl.product_id and
                                            sm2.state='done' and
                                            sl2.usage='internal'
                                    ),0)
                                    -
                                coalesce(
                                    (
                                        select sum(sm2.product_qty)
                                        from stock_move sm2 inner join stock_location sl2 on sm2.location_dest_id=sl2.id
                                                            inner join product_product pp3  on sm2.product_id=pp3.id 
                                                            inner join product_template pt3 on pp3.product_tmpl_id=pt3.id
                                        where 
                                            sm2.raw_material_production_id=mp.id and 
                                            sm2.product_id=mppl.product_id and
                                            sm2.state='done' and
                                            sl2.usage='internal'
                                    ),0)
                            )/mppl.is_bom_qty) qt_composant
                    from mrp_production mp inner join mrp_production_product_line mppl on mp.id=mppl.production_id
                    where mppl.is_bom_qty>0
                ) mp   inner join product_product pp1  on mp_product_id=pp1.id 
                       inner join product_template pt1 on pp1.product_tmpl_id=pt1.id
                       inner join product_product pp2  on mppl_product_id=pp2.id 
                       inner join product_template pt2 on pp2.product_tmpl_id=pt2.id
                       left outer join is_category ic  on pt2.is_category_id=ic.id
                where 
                    qt_pf<>qt_composant and 
                    (qt_pf+qt_rebuts)<>qt_composant
                order by pt1.is_code,mp.mp_id,pt2.is_code
            )
        """)

        #pt2.is_code not like '5%' and pt2.is_code not like '7%' 


