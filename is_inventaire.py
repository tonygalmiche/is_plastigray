# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning
import datetime
import base64


#TODO : 
# Faire la mise à jour des stocks : 
# - Rechercher les emplacement saisie et créer un inventaire pour chaque emplacement => brouillon
# - Rechercher les lots (importés) et créer les lots manquant si necessaire
# - Si les lots sont indiqués  : Regrouper pour chaque article et lot et mettre à jour le lot concerné
# - Si les lots ne sont pas indiqués : 
# => Faire le total par article, faire la liste des lots dans Odoo et pour les lots les plus récents mettre la même quantité
# => Si quantité inférieur, réduire la quanité sur les lots les plus anciens
# => Si quantité trop grande => Créer un nouveau lot 'INV-DATE' et mettre la quantité en trop sur ce lot



# - Limiter la mise à jour des stocks à un groupe limité de personnes
# - Une fois l'inventaire validé, plus rien n'est modifiable
# - Faire une doc (saisie en US ou UC, sasie unqiuement au clavier et tri des lignes


class is_inventaire(models.Model):
    _name='is.inventaire'
    _order='name desc'

    name          = fields.Char("N°", readonly=True)
    date_creation = fields.Date("Date de l'inventaire", required=True)
    createur_id   = fields.Many2one('res.users', 'Créé par', readonly=True)
    commentaire   = fields.Text('Commentaire')
    line_ids      = fields.One2many('is.inventaire.feuille', 'inventaire_id', u"Lignes")
    state         = fields.Selection([('creation', u'Création'),('cloture', u'Cloturé'),('traite', u'Traité')], u"État", readonly=True, select=True)

    def _date_creation():
        return datetime.date.today() # Date du jour

    _defaults = {
        'date_creation': _date_creation(),
        'createur_id': lambda obj, cr, uid, ctx=None: uid,
        'state': 'creation',
    }


    @api.model
    def create(self, vals):
        data_obj = self.pool.get('ir.model.data')
        sequence_ids = data_obj.search(self._cr, self._uid, [('name','=','is_inventaire_seq')])
        if sequence_ids:
            sequence_id = data_obj.browse(self._cr, self._uid, sequence_ids[0]).res_id
            vals['name'] = self.pool.get('ir.sequence').get_id(self._cr, self._uid, sequence_id, 'id')
        new_id = super(is_inventaire, self).create(vals)
        return new_id



    @api.multi
    def creer_feuille(self,obj):
        dummy, view_id = self.env['ir.model.data'].get_object_reference('is_plastigray', 'is_inventaire_feuille_form_view')
        context=self._context
        if context is None:
            context = {}
        ctx = context.copy()
        ctx.update({'default_inventaire_id': obj.id})
        return {
            'name': "Feuille d'inventaire",
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 'is.inventaire.feuille',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context':ctx,
        }

    @api.multi
    def action_creer_feuille(self):
        for obj in self:
            return self.creer_feuille(obj)



    @api.multi
    def action_fin(self):
        for obj in self:
            print obj
            obj.state="cloture"


    @api.multi
    def action_maj_stock(self):
        for obj in self:
            obj.state="traite"




class is_inventaire_feuille(models.Model):
    _name='is.inventaire.feuille'
    _order='name'

    inventaire_id      = fields.Many2one('is.inventaire', 'Inventaire', required=True, ondelete='cascade', readonly=True)
    name            = fields.Char('Numéro de feuille', required=True)
    date_creation   = fields.Date("Date de création"         , readonly=True)
    createur_id     = fields.Many2one('res.users', 'Créé par', readonly=True)
    fichier         = fields.Binary('Fichier à importer')
    line_ids        = fields.One2many('is.inventaire.line', 'feuille_id', u"Lignes")

    def _date_creation():
        return datetime.date.today() # Date du jour

    _defaults = {
        'createur_id': lambda obj, cr, uid, ctx=None: uid,
        'date_creation': _date_creation(),
    }


    @api.multi
    def action_acceder_feuille(self):
        dummy, view_id = self.env['ir.model.data'].get_object_reference('is_plastigray', 'is_inventaire_feuille_form_view')
        for obj in self:
            return {
                'name': "Feuille d'inventaire",
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'is.inventaire.feuille',
                'type': 'ir.actions.act_window',
                'res_id': obj.id,
                'domain': '[]',
            }


    @api.multi
    def action_creer_feuille(self):
        for obj in self:
            return obj.inventaire_id.creer_feuille(obj.inventaire_id)


    @api.multi
    def action_import_fichier(self):
        for obj in self:

            for row in obj.line_ids:
                row.unlink()


            csvfile=base64.decodestring(obj.fichier)
            print csvfile
            csvfile=csvfile.split("\n")
            tab=[]
            sequence=0
            for row in csvfile:
                lig=row.split(",")
                ligne=[]
                for cel in lig:
                    if cel.startswith('"'):
                        cel = cel[1:]
                    if cel.endswith('"'):
                        cel = cel[0:-1]
                    ligne.append(cel)
                tab.append(ligne)
                # Recherche de l'article
                products=self.env['product.product'].search([['is_code', '=', ligne[0]]])
                product_id=0
                for product in products:
                    product_id=product.id
                # Recherche emplacement
                location_id=0
                statut=""
                if len(ligne)>4:
                    # Si statur = Q recherche d'un autre emplacement
                    emplacement = ligne[2]
                    statut      = ligne[3][0:1]
                    if statut=="Q":
                        emplacement="Q0"
                    locations=self.env['stock.location'].search([ ['usage','=','internal'],['name','like',emplacement]  ])
                    for location in locations:
                        location_id=location.id
                #Quantité
                qt=0
                if len(ligne)>6:
                    if statut=="Q":
                        val=ligne[6]
                    else:
                        val=ligne[4]
                    val=val.replace(" ", "")
                    try:
                        qt=float(val)
                    except ValueError:
                        continue
                if product_id and location_id:
                    sequence=sequence+1
                    vals={
                        'feuille_id': obj.id,
                        'sequence': sequence,
                        'product_id':product_id,
                        'location_id':location_id,
                        'qt_us': qt,
                        'lot': ligne[1],
                    }
                    self.env['is.inventaire.line'].create(vals)







class is_inventaire_line(models.Model):
    _name='is.inventaire.line'
    _order='feuille_id,sequence,id'

    inventaire_id   = fields.Many2one('is.inventaire', 'Inventaire', store=True, compute='_compute')
    feuille_id      = fields.Many2one('is.inventaire.feuille', 'Feuille Inventaire', required=True, ondelete='cascade')
    sequence        = fields.Integer('Séquence')
    product_id      = fields.Many2one('product.product', 'Article' , required=True)
    uc              = fields.Char('UC', store=True, compute='_compute')
    uc_us           = fields.Integer('UC/US', store=True, compute='_compute')
    location_id     = fields.Many2one('stock.location', 'Emplacement', required=True)
    qt_us           = fields.Float("Qt US saisie")
    qt_uc           = fields.Float("Qt UC saisie")
    qt_us_calc      = fields.Float('Qt US', store=True, compute='_compute')
    lieu            = fields.Char('Lieu')
    lot             = fields.Char('Lot')

    _defaults = {
        'sequence': 10,
    }


    @api.depends('product_id','qt_us','qt_uc')
    def _compute(self):
        for obj in self:
            obj.inventaire_id=obj.feuille_id.inventaire_id.id
            if obj.product_id:
                obj.uc_us=1
                if len(obj.product_id.packaging_ids):
                    packaging=obj.product_id.packaging_ids[0]
                    obj.uc=packaging.ul.name
                    obj.uc_us=packaging.qty
                if obj.qt_uc!=0:
                    obj.qt_us_calc=obj.qt_uc*obj.uc_us
                else:
                    obj.qt_us_calc=obj.qt_us

    @api.multi
    def onchange_product_id(self,product_id):
        v={}
        valeur=self.env['is.mem.var'].get(self._uid,'location_id')
        v['location_id'] = int(valeur)
        return {'value': v}


    @api.multi
    def onchange_location_id(self,product_id,location_id,qt_us,qt_uc,lieu):
        v={}
        v['product_id']  = product_id
        v['location_id'] = location_id
        v['qt_us']       = qt_us
        v['qt_uc']       = qt_uc
        v['lieu']        = lieu
        if location_id:
            self.env['is.mem.var'].set(self._uid, 'location_id', location_id)
        return {'value': v}






