# -*- coding: utf-8 -*-
from openerp import models,fields,api,SUPERUSER_ID
from openerp.tools.translate import _
from openerp.exceptions import Warning
import datetime
import logging
_logger = logging.getLogger(__name__)


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
            ct=0
            nb=len(result)
            for row in result:
                ct=ct+1
                qt_livree=row[7]
                vals={
                    'reach_id'       : obj.id,
                    'partner_id'     : row[0],
                    'name'           : row[1],
                    'moule'          : row[2],
                    'ref_client'     : row[3],
                    'category_id'    : row[4],
                    'gestionnaire_id': row[5],
                    'qt_livree'      : qt_livree,
                    'interdit'       : 'Non',
                }
                line=self.env['is.reach.product'].create(vals)
                product_id=row[1]
                global ordre
                ordre=0
                product = self.env['product.product'].browse(product_id)
                _logger.info(str(ct)+'/'+str(nb)+' : '+str(product.is_code))
                self.cbb_multi_niveaux(line,product)

                #** Calcul du poids des matières *******************************
                poids_produit=0
                for matiere in line.matiere_ids:
                    poids_produit=poids_produit+matiere.qt_nomenclature
                line.poids_produit_unitaire = poids_produit
                line.poids_produit          = poids_produit*qt_livree
                #***************************************************************


                #** Calcul du poids des substances et des codes cas ************
                poids_substances=0
                codes_cas=[]
                interdits=[]
                for cas in line.cas_ids:
                    interdit=cas.name.interdit
                    if interdit=='Oui':
                        if cas.name.code_cas not in interdits:
                            interdits.append(cas.name.code_cas)
                    cas.poids_produit_unitaire = poids_produit
                    cas.poids_produit          = poids_produit*qt_livree
                    #pourcentage_substance=0
                    #if line.poids_produit!=0:
                    #    pourcentage_substance=100*cas.poids_substance/line.poids_produit
                    #cas.pourcentage_substance=pourcentage_substance
                    
                    poids_substances=poids_substances+cas.poids_substance
                    code_cas=cas.name.code_cas
                    if code_cas not in codes_cas:
                        codes_cas.append(code_cas)
                line.codes_cas=', '.join(codes_cas)
                line.interdit=', '.join(interdits)
                pourcentage_substances=0
                if line.poids_produit!=0:
                    pourcentage_substances=100*poids_substances/line.poids_produit
                line.poids_substances=poids_substances
                line.pourcentage_substances=pourcentage_substances
                #***************************************************************

            #*******************************************************************

    def get_partner(self):
        partner = self.env['res.partner'].search([('is_code', '=', self.clients.split(' ')[0])], limit=1)
        return partner

    def get_poids_substances(self):
        ret = {}
        for product in self.product_ids:
            for cas in product.get_cas_unique():
                name = cas['name']
                ret.setdefault(name, {'name': name,
                                      'interdit': cas['interdit'],
                                      'poids': 0})
                ret[name]['poids'] += cas['poids']
        return ret.values()

    @api.multi
    def cbb_multi_niveaux(self, reach_product,product, quantite=1, niveau=1):
        global ordre

        #** Enregistrement matière livrée **************************************
        if len(product.is_code_cas_ids)>0:
            vals={
                'reach_product_id'     : reach_product.id,
                'reach_id'             : reach_product.reach_id.id,
                'qt_livree'            : reach_product.qt_livree,
                'product_id'           : product.id,
                'qt_nomenclature'      : quantite,
                'qt_matiere_livree'    : reach_product.qt_livree*quantite,
            }
            res=self.env['is.reach.product.matiere'].create(vals)
        #***********************************************************************


        #** Enregistrement des CAS de cet article ******************************
        for cas in product.is_code_cas_ids:
            poids_substance = reach_product.qt_livree * quantite * cas.poids/100
            interdit=cas.code_cas_id.interdit
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
                'matiere_id'           : product.id,
                'name'                 : cas.code_cas_id.id,
                'interdit'             : interdit,
                'poids_substance'      : poids_substance,
                'pourcentage_substance': cas.poids,
                'poids_autorise'       : cas.code_cas_id.poids_autorise, 
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
    def matieres_livrees_action(self):
        for obj in self:
            return {
                'name': u'Analyse REACH par matière',
                'view_mode': 'tree,form',
                'view_type': 'form',
                'res_model': 'is.reach.product.matiere',
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
    interdit         = fields.Char("Substance réglementée")
    poids_substances       = fields.Float("Poids total des substances à risque")
    poids_produit_unitaire = fields.Float("Poids unitaire des matières", digits=(14,4))
    poids_produit          = fields.Float("Poids des matières livrées")
    pourcentage_substances = fields.Float("% du poids des substances à risque", digits=(14,4))
    codes_cas              = fields.Char("Codes CAS livrés")
    cas_ids                = fields.One2many('is.reach.product.cas'    , 'reach_product_id', u"Substances livrées")
    matiere_ids            = fields.One2many('is.reach.product.matiere', 'reach_product_id', u"Matières livrées")

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

    def get_matiere_unique(self):
        matiere_ids = []
        for matiere_id in self.matiere_ids:
            if matiere_id.product_id.id not in matiere_ids:
                matiere_ids.append(matiere_id.product_id.id)
                yield matiere_id

    def get_cas_unique(self):
        ret = {}
        for cas in self.cas_ids:
            name = cas.name.code_cas
            ret.setdefault(name, {'name': name,
                                  'interdit': cas.interdit,
                                  'pourcentage_substance': cas.pourcentage_substance,
                                  'poids': 0})
            ret[name]['poids'] += cas.poids_substance
        return ret.values()


class is_reach_product_matiere(models.Model):
    _name='is.reach.product.matiere'
    _order='product_id'

    reach_id          = fields.Many2one('is.reach', 'Analyse REACH')
    reach_product_id  = fields.Many2one('is.reach.product', 'Ligne produit REACH', required=True, ondelete='cascade')
    qt_livree         = fields.Integer("Quantité produit fini livrée")
    product_id        = fields.Many2one('product.product', 'Matière livrée')
    qt_nomenclature   = fields.Float("Qt nomenclature", digits=(14,6))
    qt_matiere_livree = fields.Float("Quantité matière livrée", digits=(14,2))


class is_reach_product_cas(models.Model):
    _name='is.reach.product.cas'
    _order='name'

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
    ], "Substance réglementée")
    poids_substance        = fields.Float("Poids total substance à risque")
    poids_produit_unitaire = fields.Float("Poids produit unitaire", digits=(14,4))
    poids_produit          = fields.Float("Poids produit livré")
    pourcentage_substance  = fields.Float("% du poids de cette substance à risque", digits=(14,4))
    poids_autorise         = fields.Float('% de poids autorisé')

