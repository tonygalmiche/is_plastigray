# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _
import datetime
import pytz
import psycopg2
import psycopg2.extras
from openerp.exceptions import Warning


class is_article_actualiser(models.TransientModel):
    _name = "is.article.actualiser"
    _description = u"Actualiser la liste des articles"


    @api.multi
    def actualiser_liste_articles(self):
        user    = self.env['res.users'].browse(self._uid)
        company = user.company_id
        try:
            cnx0 = psycopg2.connect("dbname='"+self._cr.dbname+"' user='"+company.is_postgres_user+"' host='"+company.is_postgres_host+"' password='"+company.is_postgres_pwd+"'")
        except Exception, e:
            raise Warning('Postgresql non disponible !')
        cur0 = cnx0.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        SQL="delete from is_article"
        cur0.execute(SQL)
        bases = self.env['is.database'].search([])
        for base in bases:
            cnx=False
            if base.database:
                try:
                    cnx  = psycopg2.connect("dbname='"+base.database  +"' user='"+company.is_postgres_user+"' host='"+company.is_postgres_host+"' password='"+company.is_postgres_pwd+"'")
                except Exception, e:
                    raise Warning('Postgresql non disponible !')
            if cnx:
                cur = cnx.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                SQL= """
                    SELECT 
                        pt.is_code            as name,
                        pt.name               as designation,
                        pt.is_mold_dossierf   as moule,
                        ipf.name              as famille,
                        ipsf.name             as sous_famille,
                        ic.name               as categorie,
                        ig.name               as gestionnaire,
                        pt.is_ref_fournisseur as ref_fournisseur,
                        pt.is_ref_plan        as ref_plan,
                        pt.is_couleur         as couleur,
                        rp.name               as fournisseur,
                        uom.name              as unite
                    FROM product_template pt left outer join is_product_famille       ipf on pt.family_id=ipf.id
                                             left outer join is_product_sous_famille ipsf on pt.sub_family_id=ipsf.id
                                             left outer join is_category               ic on pt.is_category_id=ic.id
                                             left outer join is_gestionnaire           ig on pt.is_gestionnaire_id=ig.id
                                             left outer join res_partner               rp on pt.is_fournisseur_id=rp.id
                                             left outer join product_uom              uom on pt.uom_id=uom.id
                    WHERE 
                        pt.id>0
                    ORDER BY pt.is_code
                """
                cur.execute(SQL)
                rows = cur.fetchall()
                for row in rows:
                    SQL="""
                        INSERT INTO is_article (
                            name,
                            designation,
                            moule,
                            famille,
                            sous_famille,
                            categorie,
                            gestionnaire,
                            ref_fournisseur,
                            ref_plan,
                            couleur,
                            fournisseur,
                            unite,
                            societe
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """
                    values=(
                        row['name'],
                        row['designation'],
                        row['moule'],
                        row['famille'],
                        row['sous_famille'],
                        row['categorie'],
                        row['gestionnaire'],
                        row['ref_fournisseur'],
                        row['ref_plan'],
                        row['couleur'],
                        row['fournisseur'],
                        row['unite'],
                        base.database
                    )
                    cur0.execute(SQL,values)
                cur.close()
        cnx0.commit()
        cur0.close()
        return {
            'name': u'Articles de tous les sites',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'res_model': 'is.article',
            'type': 'ir.actions.act_window',
            'limit': 100,
        }




class is_article(models.Model):
    _name='is.article'
    _order='name,societe'

    name              = fields.Char(u"Code PG", select=True)
    designation       = fields.Char(u"Désignation")
    moule             = fields.Char(u"Moule")
    famille           = fields.Char(u"Famille", select=True)
    sous_famille      = fields.Char(u"Sous-Famille", select=True)
    categorie         = fields.Char(u"Catégorie", select=True)
    gestionnaire      = fields.Char(u"Gestionnaire", select=True)
    ref_fournisseur   = fields.Char(u"Référence fournisseur")
    ref_plan          = fields.Char(u"Réf Plan")
    couleur           = fields.Char(u"Couleur/ Type matière")
    fournisseur       = fields.Char(u"Fournisseur par défaut")
    unite             = fields.Char(u"Unité")
    societe           = fields.Char(u"Société", select=True)
    cout_standard     = fields.Float(u"Coût standard")
    cout_actualise    = fields.Float(u"Coût actualisé")
    prevision_annee_n = fields.Float(u"Prévision Année N")

