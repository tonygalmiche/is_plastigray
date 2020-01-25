# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_comparatif_tps_article_gamme(models.Model):
    _name='is.comparatif.tps.article.gamme'
    _order='product_id'
    _auto = False

    product_id          = fields.Many2one('product.template', 'Article')
    is_category_id      = fields.Many2one('is.category', 'Catégorie')
    routing_id          = fields.Many2one('mrp.routing', 'Gamme Standard')
    sequence            = fields.Integer('Sequence')
    name                = fields.Char('Nom')
    workcenter_id       = fields.Many2one('mrp.workcenter', 'Poste de charge')
    nb_secondes_gamme   = fields.Float('Nb secondes Gamme')
    nb_secondes_article = fields.Float('Temps de realisation Article')
    delta_nb_secondes   = fields.Float('Delta Nb secondes')


#                    sum(mrw.is_nb_secondes*mr.is_nb_empreintes*mr.is_coef_theia) as nb_secondes_gamme,


    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_comparatif_tps_article_gamme')
        cr.execute("""

            CREATE OR REPLACE FUNCTION get_nb_secondes_gamme(nbsecondes float, nbempreintes integer, coeftheia float, name char) RETURNS float AS $$
                    BEGIN
                        IF name = 'ASSEMBLAGE' THEN
                            RETURN nbsecondes;
                        ELSE
                            RETURN nbsecondes*coeftheia;
                        END IF;
                    END;
            $$ LANGUAGE plpgsql;

            CREATE OR REPLACE view is_comparatif_tps_article_gamme AS (
                SELECT 
                    mb.id,
                    mb.product_tmpl_id   as product_id,
                    pt.is_category_id    as is_category_id,
                    mr.id                as routing_id,
                    min(mrw.sequence)         as sequence,
                    min(mrw.name)             as name,
                    min(mrw.workcenter_id)    as workcenter_id,
                    sum(get_nb_secondes_gamme(mrw.is_nb_secondes,mr.is_nb_empreintes,mr.is_coef_theia,mrw.name)) as nb_secondes_gamme,
                    min(pt.temps_realisation) as nb_secondes_article,
                    round(cast(sum(get_nb_secondes_gamme(mrw.is_nb_secondes,mr.is_nb_empreintes,mr.is_coef_theia,mrw.name))-min(pt.temps_realisation) as numeric),2) as delta_nb_secondes
                FROM mrp_bom mb inner join mrp_routing mr             on mb.routing_id=mr.id
                                inner join mrp_routing_workcenter mrw on mr.id=mrw.routing_id
                                inner join mrp_workcenter mw          on mrw.workcenter_id=mw.id
                                inner join resource_resource rr       on mw.resource_id=rr.id
                                inner join product_template pt        on mb.product_tmpl_id=pt.id
                                inner join is_category ic             on pt.is_category_id=ic.id
                WHERE 
                    rr.resource_type='material' and 
                    ic.name<'70'
                GROUP BY
                    mb.id,
                    mb.product_tmpl_id,
                    pt.is_category_id,
                    mr.id
                HAVING round(cast(sum(get_nb_secondes_gamme(mrw.is_nb_secondes,mr.is_nb_empreintes,mr.is_coef_theia,mrw.name))-min(pt.temps_realisation) as numeric),2)<>0
            )
        """)

