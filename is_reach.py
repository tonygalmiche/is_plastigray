# -*- coding: utf-8 -*-
from openerp import models,fields,api,SUPERUSER_ID
from openerp.tools.translate import _
from openerp.exceptions import Warning
import datetime


class is_reach(models.Model):
    _name='is.reach'
    _order='name desc'


    name         = fields.Date("Date du calcul", required=True)
    date_debut   = fields.Date("Date de début" , required=True, help="Date de début des livraisons")
    date_fin     = fields.Date("Date de fin"   , required=True, help="Date de fin des livraisons")
    clients      = fields.Char("Clients", help="Codes des clients à 6 chiffres séparés par un espace")
    product_ids  = fields.One2many('is.reach.product', 'reach_id', u"Produits livrés")

    _defaults = {
        'name' : lambda *a: fields.datetime.now(),
    }


    @api.multi
    def calcul_action(self):
        cr, uid, context = self.env.args
        for obj in self:

            #** Liste des clients indiquée *************************************
            clients=[]
            if obj.clients:
                res=obj.clients.split(' ')
                for r in res:
                    if r not in clients and r:
                        clients.append("'"+r+"'")
            clients=','.join(clients)
            #*******************************************************************


            #** Livraisons sur la période et les clients indiqués **************
            SQL="""
                select
                    sp.partner_id           as partner_id,
                    pp.id                   as product_id,
                    pt.is_mold_dossierf     as is_mold_dossierf,
                    pt.is_ref_client        as ref_client,
                    pt.is_category_id       as is_category_id,
                    pt.is_gestionnaire_id   as is_gestionnaire_id,
                    pt.weight_net           as weight_net,
                    sum(sm.product_uom_qty)
                from stock_picking sp inner join stock_move                sm on sm.picking_id=sp.id 
                                      inner join product_product           pp on sm.product_id=pp.id
                                      inner join product_template          pt on pp.product_tmpl_id=pt.id
                                      inner join res_partner               rp on sp.partner_id=rp.id
                where 
                    sp.picking_type_id=2 and 
                    sm.state='done' and
                    sp.is_date_expedition>='"""+str(obj.date_debut)+"""' and
                    sp.is_date_expedition<='"""+str(obj.date_fin)+"""'
            """
            if clients:
                SQL=SQL+" and rp.is_code in ("+clients+") "
            SQL=SQL+"""
                group by
                    sp.partner_id, 
                    pp.id,
                    pt.id,
                    pt.is_code,
                    pt.is_category_id,
                    pt.is_gestionnaire_id,
                    pt.is_mold_dossierf,
                    pt.is_ref_client,
                    pt.weight_net
                order by pt.is_code
            """
            cr.execute(SQL)
            result = cr.fetchall()
            obj.product_ids.unlink()
            for row in result:
                vals={
                    'reach_id'       : obj.id,
                    'partner_id'     : row[0],
                    'name'           : row[1],
                    'moule'          : row[2],
                    'ref_client'     : row[3],
                    'category_id'    : row[4],
                    'gestionnaire_id': row[5],
                    'poids_produit'  : row[6]*row[7],
                    'qt_livree'      : row[7],
                    'interdit'       : 'Non',
                }
                line=self.env['is.reach.product'].create(vals)
                product_id=row[1]
                global ordre
                ordre=0
                product = self.env['product.product'].browse(product_id)

                #print product_id, product.is_code,row[7]

                self.cbb_multi_niveaux(line,product)
                poids_substances=0
                for cas in line.cas_ids:
                    poids_substances=poids_substances+cas.poids_substance
                pourcentage_substances=0
                if line.poids_produit!=0:
                    pourcentage_substances=100*poids_substances/line.poids_produit

                line.poids_substances=poids_substances
                line.pourcentage_substances=pourcentage_substances
            #*******************************************************************


    @api.multi
    def cbb_multi_niveaux(self, reach_product,product, quantite=1, niveau=1):
        global ordre

        #** Enregistrement des CAS de cet article ******************************
        for cas in product.is_code_cas_ids:
            poids_produit   = reach_product.poids_produit
            poids_substance = reach_product.qt_livree * quantite * cas.poids/100
            pourcentage_substance=0
            if poids_produit!=0:
                pourcentage_substance=100*poids_substance/poids_produit
            interdit=cas.code_cas_id.interdit
            if interdit=='Oui':
                reach_product.interdit='Oui'
            vals={
                'reach_product_id'     : reach_product.id,
                'reach_id'             : reach_product.reach_id.id,
                'partner_id'           : reach_product.partner_id.id,
                'product_id'           : reach_product.name.id,
                'moule'                : reach_product.moule,
                'ref_client'           : reach_product.ref_client,
                'category_id'          : reach_product.category_id.id,
                'gestionnaire_id'      : reach_product.gestionnaire_id.id,
                'qt_livree'            : reach_product.qt_livree,
                'poids_produit'        : poids_produit,
                'matiere_id'           : product.id,
                'name'                 : cas.code_cas_id.id,
                'interdit'             : interdit,
                'poids_substance'      : poids_substance,
                'pourcentage_substance': pourcentage_substance,
            }
            res=self.env['is.reach.product.cas'].create(vals)
        #***********************************************************************

        bom_obj = self.env['mrp.bom']
        bom_id = bom_obj._bom_find(product.product_tmpl_id.id, properties=None)
        bom = bom_obj.browse(bom_id)
        res= bom_obj._bom_explode(bom, product, 1)
        for line in res[0]:
            ordre=ordre+1
            line_product  = self.env['product.product'].browse(line['product_id'])
            line_quantite = quantite*line['product_qty']

            #if line_product.is_code=='501893':
            #    print product.is_code,line_product.is_code,line['product_qty'],quantite

            self.cbb_multi_niveaux(reach_product,line_product, line_quantite, niveau+1)


    @api.multi
    def produits_livres_action(self):
        for obj in self:
            return {
                'name': u'Analyse REACH par produit',
                'view_mode': 'tree,form',
                'view_type': 'form',
                'res_model': 'is.reach.product',
                'domain': [
                    ('reach_id'  ,'=', obj.id),
                ],
                'context': {
                    'default_reach_id'  : obj.id,
                },
                'type': 'ir.actions.act_window',
                'limit': 1000,
            }


    @api.multi
    def substances_livrees_action(self):
        for obj in self:
            return {
                'name': u'Analyse REACH par substance',
                'view_mode': 'tree,form',
                'view_type': 'form',
                'res_model': 'is.reach.product.cas',
                'domain': [
                    ('reach_id','=', obj.id),
                ],
                'context': {
                    'default_reach_id': obj.id,
                },
                'type': 'ir.actions.act_window',
                'limit': 1000,
            }


class is_reach_product(models.Model):
    _name='is.reach.product'
    _order='partner_id, name'

    reach_id         = fields.Many2one('is.reach', "Analyse REACH", required=True, ondelete='cascade')
    partner_id       = fields.Many2one('res.partner', 'Client livré')
    name             = fields.Many2one('product.product', 'Produit livré')
    moule            = fields.Char("Moule")
    ref_client       = fields.Char("Réf client")
    category_id      = fields.Many2one('is.category', 'Catégorie')
    gestionnaire_id  = fields.Many2one('is.gestionnaire', 'Gestionnaire')
    qt_livree        = fields.Integer("Quantité livrée", required=True)
    interdit         = fields.Selection([ 
        ('Oui','Oui'),
        ('Non','Non'),
    ], "Substance interdire")
    poids_substances       = fields.Float("Poids total des substances à risque")
    poids_produit          = fields.Float("Poids produit livré")
    pourcentage_substances = fields.Float("% du poids des substances à risque", digits=(14,4))
    cas_ids                = fields.One2many('is.reach.product.cas', 'reach_product_id', u"Substances livrées")


    @api.multi
    def substances_livrees_action(self):
        for obj in self:
            return {
                'name': u'Analyse REACH par substance',
                'view_mode': 'tree,form',
                'view_type': 'form',
                'res_model': 'is.reach.product.cas',
                'domain': [
                    ('reach_id'          ,'=', obj.reach_id.id),
                    ('reach_product_id'  ,'=', obj.id),
                ],
                'context': {
                    'default_reach_id'        : obj.reach_id.id,
                    'default_reach_product_id': obj.id,
                },
                'type': 'ir.actions.act_window',
                'limit': 1000,
            }



class is_reach_product_cas(models.Model):
    _name='is.reach.product.cas'
    _order='name desc'

    reach_product_id = fields.Many2one('is.reach.product', 'Ligne produit REACH', required=True, ondelete='cascade')
    name             = fields.Many2one('is.code.cas', 'Substance livrée')
    reach_id         = fields.Many2one('is.reach', 'Analyse REACH')
    partner_id       = fields.Many2one('res.partner', 'Client livré')
    product_id       = fields.Many2one('product.product', 'Produit livré')
    moule            = fields.Char("Moule")
    ref_client       = fields.Char("Réf client")
    category_id      = fields.Many2one('is.category', 'Catégorie')
    gestionnaire_id  = fields.Many2one('is.gestionnaire', 'Gestionnaire')
    qt_livree        = fields.Integer("Quantité livrée", required=True)
    matiere_id       = fields.Many2one('product.product', 'Matière livrée')
    interdit         = fields.Selection([ 
        ('Oui','Oui'),
        ('Non','Non'),
    ], "Substance interdire")
    poids_substance        = fields.Float("Poids total substance à risque")
    poids_produit          = fields.Float("Poids produit livré")
    pourcentage_substance  = fields.Float("% du poids de cete substance à risque", digits=(14,4))


