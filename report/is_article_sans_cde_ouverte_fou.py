# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_article_sans_cde_ouverte_fou(models.Model):
    _name='is.article.sans.cde.ouverte.fou'
    _order='product_id'
    _auto = False

    product_id              = fields.Many2one('product.template', 'Article')
    is_category_id          = fields.Many2one('is.category', 'Catégorie')
    is_gestionnaire_id      = fields.Many2one('is.gestionnaire', 'Gestionnaire')
    product_nb_fournisseurs = fields.Integer('Nb fournisseurs')
    product_partner_id      = fields.Many2one('res.partner', 'Fournisseur fiche article')
    nb_cde_ouverte          = fields.Integer('Nb commandes ouvertes')
    cde_ouverte_partner_id  = fields.Many2one('is.cde.ouverte.fournisseur', 'Commande ouverte fournisseur')


    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_article_sans_cde_ouverte_fou')
        cr.execute("""
            CREATE OR REPLACE FUNCTION get_product_fournisseur_id(pt_id integer) RETURNS integer AS $$
            BEGIN
                RETURN (
                    select ps.name 
                    from product_supplierinfo ps 
                    where ps.product_tmpl_id=pt_id
                    order by ps.sequence limit 1
                );
            END;
            $$ LANGUAGE plpgsql;

            CREATE OR REPLACE view is_article_sans_cde_ouverte_fou AS (
                select
                    pt2.id,
                    pt2.product_id,
                    pt2.is_category_id,
                    pt2.is_gestionnaire_id,
                    pt2.product_nb_fournisseurs,
                    pt2.product_partner_id,
                    pt2.nb_cde_ouverte,
                    pt2.cde_ouverte_partner_id
                from (
                    select 
                        pt.id,
                        pt.id product_id,
                        pt.is_category_id,
                        pt.is_gestionnaire_id,
                        (
                            select count(*) from product_supplierinfo ps where pt.id=ps.product_tmpl_id
                        ) product_nb_fournisseurs,
                        get_product_fournisseur_id(pt.id) product_partner_id,
                        (
                            select count(*)
                            from is_cde_ouverte_fournisseur cof inner join is_cde_ouverte_fournisseur_product cofp on cof.id=cofp.order_id
                            where cofp.product_id=pp.id 
                        ) nb_cde_ouverte,
                        (
                            select cof.id
                            from is_cde_ouverte_fournisseur cof inner join is_cde_ouverte_fournisseur_product cofp on cof.id=cofp.order_id
                            where cofp.product_id=pp.id and cof.partner_id=get_product_fournisseur_id(pt.id)
                            limit 1
                        ) cde_ouverte_partner_id
                    from product_template pt inner join product_product pp on pt.id=pp.product_tmpl_id
                    where pt.active='t' and pt.purchase_ok='t'
                ) pt2 inner join is_category ic on pt2.is_category_id=ic.id
                where ic.name::int<70
            )
        """)

