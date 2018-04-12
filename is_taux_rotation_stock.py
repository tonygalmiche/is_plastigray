# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api


class is_taux_rotation_stock_new(models.Model):
    _name='is.taux.rotation.stock.new'
    _order='product_id'

    product_id      = fields.Many2one('product.template', 'Article')
    code_pg         = fields.Char('Code PG')
    designation     = fields.Char('Désignation')
    cat             = fields.Char('Cat')
    gest            = fields.Char('Gest')
    cout_act        = fields.Float('Coût actualisé'      , digits=(14,2))
    stock           = fields.Float('Stock'               , digits=(14,0))
    pic_12mois      = fields.Float('PIC 12 Mois'         , digits=(14,0))
    pic_3mois_ferme = fields.Float('PIC 3 mois ferme'    , digits=(14,0))
    pic_3mois_prev  = fields.Float('PIC 3 mois prev'     , digits=(14,0))
    fm_3mois        = fields.Float('FM 3 mois'           , digits=(14,0))
    ft_3mois        = fields.Float('FT 3 mois'           , digits=(14,0))
    besoin_total    = fields.Float('Besoins Total 3 mois', digits=(14,0))
    nb_sem          = fields.Float('Nb Sem'              , digits=(14,0))
    stock_valorise  = fields.Float('Stock valorisé'      , digits=(14,0))

    def run_is_taux_rotation_stock_new_scheduler_action(self, cr, uid, use_new_cursor=False, company_id = False, context=None):
        self.run_is_taux_rotation_stock_new(cr, uid, context)

    @api.multi
    def run_is_taux_rotation_stock_new(self):
        cr = self._cr
        print '#### Début : run_is_taux_rotation_stock_new ####'
        sql="""
            delete from is_taux_rotation_stock_new;

            INSERT INTO is_taux_rotation_stock_new (id,product_id,code_pg,designation,cat,gest,cout_act,stock,pic_12mois,pic_3mois_ferme,pic_3mois_prev,fm_3mois,ft_3mois,besoin_total,nb_sem,stock_valorise)
            SELECT id,product_id,code_pg,designation,cat,gest,cout_act,stock,pic_12mois,pic_3mois_ferme,pic_3mois_prev,fm_3mois,ft_3mois,besoin_total,nb_sem,stock_valorise
            FROM is_taux_rotation_stock_view;
        """
        cr.execute(sql)
        print '#### Fin : run_is_taux_rotation_stock_new ####'


class is_taux_rotation_stock_view(models.Model):
    _name='is.taux.rotation.stock.view'
    _order='product_id'
    _auto = False

    product_id      = fields.Many2one('product.template', 'Article')
    code_pg         = fields.Char('Code PG')
    designation     = fields.Char('Désignation')
    cat             = fields.Char('Cat')
    gest            = fields.Char('Gest')
    cout_act        = fields.Float('Coût actualisé'      , digits=(14,2))
    stock           = fields.Float('Stock'               , digits=(14,0))
    pic_12mois      = fields.Float('PIC 12 Mois'         , digits=(14,0))
    pic_3mois_ferme = fields.Float('PIC 3 mois ferme'    , digits=(14,0))
    pic_3mois_prev  = fields.Float('PIC 3 mois prev'     , digits=(14,0))
    fm_3mois        = fields.Float('FM 3 mois'           , digits=(14,0))
    ft_3mois        = fields.Float('FT 3 mois'           , digits=(14,0))
    besoin_total    = fields.Float('Besoins Total 3 mois', digits=(14,0))
    nb_sem          = fields.Float('Nb Sem'              , digits=(14,0))
    stock_valorise  = fields.Float('Stock valorisé'      , digits=(14,0))




    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_taux_rotation_stock_view')
        cr.execute("""

CREATE OR REPLACE FUNCTION get_cout_act_total(pp_id  integer) RETURNS float AS $$
BEGIN
    RETURN (
        COALESCE(
            (
                select ic.cout_act_total 
                from is_cout ic
                where ic.name=pp_id limit 1
            )
        ,0)
    );
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_pic_12mois(pp_id  integer) RETURNS float AS $$
BEGIN
    RETURN (
        COALESCE(
            (
                select sum(quantite) 
                from is_pic_3ans
                where product_id=pp_id and type_donnee='pic' and annee=CAST(date_part('year', CURRENT_DATE) AS text)
            )
        ,0)
    );
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_pic_3mois(pp_id  integer, type_cde char) RETURNS float AS $$
BEGIN
    RETURN (
        COALESCE(
            (
                select sum(sol.product_uom_qty) 
                from sale_order so inner join sale_order_line sol on sol.order_id=so.id
                where 
                    sol.product_id=pp_id and 
                    sol.is_type_commande=type_cde and
                    sol.is_date_expedition<=(CURRENT_DATE + interval '84' day) and 
                    so.state='draft' 
            )
        ,0)
    );
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_fm_3mois(pp_id  integer) RETURNS float AS $$
BEGIN
    RETURN (
        COALESCE(
            (
                select sum(sm.product_uom_qty) 
                from stock_move sm inner join mrp_production mp on sm.raw_material_production_id=mp.id
                where
                    sm.product_id=pp_id and
                    sm.state not in ('done','cancel') and
                    mp.date_planned<=(CURRENT_DATE + interval '84' day)
            )
        ,0)
    );
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_ft_3mois(pp_id  integer) RETURNS float AS $$
BEGIN
    RETURN (
        COALESCE(
            (
                select sum(quantity) 
                from mrp_prevision mp
                where
                    mp.product_id=pp_id and
                    mp.type='ft' and
                    mp.start_date<=(CURRENT_DATE + interval '84' day)
            )
        ,0)
    );
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_nb_semaines_rotation(stock  float, besoin float) RETURNS float AS $$
BEGIN
    IF besoin = 0 THEN
        RETURN 9999;
    ELSE
        RETURN stock/(besoin/12);
    END IF;
END;
$$ LANGUAGE plpgsql;


-- DROP MATERIALIZED VIEW IF EXISTS is_taux_rotation_stock;
-- CREATE MATERIALIZED VIEW is_taux_rotation_stock AS (

CREATE OR REPLACE VIEW is_taux_rotation_stock_view AS (
    select 
        pt.id                               id,
        pt.id                               product_id,
        pt.is_code                          code_pg,
        pt.name                             designation,
        ic.name                             cat,
        ig.name                             gest,
        get_cout_act_total(pp.id)           cout_act,
        is_stock(pp.id)                     stock,
        get_pic_12mois(pp.id)               pic_12mois,
        get_pic_3mois(pp.id,'ferme')        pic_3mois_ferme,
        get_pic_3mois(pp.id,'previsionnel') pic_3mois_prev,
        get_fm_3mois(pp.id)                 fm_3mois,
        get_ft_3mois(pp.id)                 ft_3mois,
        (get_pic_3mois(pp.id,'ferme')+get_pic_3mois(pp.id,'previsionnel')+get_fm_3mois(pp.id)+get_ft_3mois(pp.id)) besoin_total,
        get_nb_semaines_rotation(is_stock(pp.id) ,(get_pic_3mois(pp.id,'ferme')+get_pic_3mois(pp.id,'previsionnel')+get_fm_3mois(pp.id)+get_ft_3mois(pp.id)))    nb_sem,
        is_stock(pp.id)*get_cout_act_total(pp.id) stock_valorise
    from product_product pp inner join product_template      pt on pp.product_tmpl_id=pt.id
                            left outer join is_category      ic on pt.is_category_id=ic.id
                            left outer join is_gestionnaire  ig on pt.is_gestionnaire_id=ig.id

    where ic.name not in('70','72','73','74','80') and is_stock(pp.id)<>0


)

        """)






