# -*- coding: utf-8 -*-
from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning


#TODO : 
# - Prix en automatique (mais modifiable ?) lors du changement de la quantité ou de l'article
# - Envoi d'un mail à l'acheteur lors du transmis achat
# - Droits à mettre en place en fonction de l'état de la demande
# - Bloquer si plusieurs lignes (sur le onchange de l'article) ou dés l'ajout d'une ligne si possible
# -> TODO : Test avec on_change sur l'article et avec un champ calculé sur le nombre de lignes mais sans succès
# -> TODO : A revoir ultéreurement
# - Bouton pour générer la commande et solder la DA
# - Revoir le CBN pour qu'il génére une DAS à la place des devis pour les anomalies


class is_demande_achat_serie(models.Model):
    _name='is.demande.achat.serie'
    _order='name desc'


    name                 = fields.Char("N° demande achat série", readonly=True)
    createur_id          = fields.Many2one('res.users', 'Créateur', required=True)
    date_creation        = fields.Date("Date de création", required=True)
    acheteur_id          = fields.Many2one('res.users', 'Acheteur', required=True)
    fournisseur_id       = fields.Many2one('res.partner', 'Fournisseur', domain=[('is_company','=',True),('supplier','=',True)], required=True)
    delai_livraison      = fields.Date("Délai de livraison", required=True)
    lieu_livraison_id    = fields.Many2one('res.partner', 'Lieu de livraison', domain=[('is_company','=',True),('customer','=',True)], required=True)
    motif                = fields.Selection([
        ('pas_tarif'    , "Pas de tarif de créé"),
        ('fin_vie'      , "Produit en fin de vie (Lot trop important)"),
        ('inf_lot_appro', "Besoin inférieur au lot d'appro"),
        ('gest_18'      , "Gest 18 = Achat réalisé par le service achat"),
    ], "Motif")
    commentaire          = fields.Text("Commentaire")
    state                = fields.Selection([
        ('brouillon'     , 'Brouillon'),
        ('transmis_achat', 'Transmis achat'),
        ('solde'         , 'Soldé'),
        ('annule'        , 'Annulé'),
    ], "Etat")
    line_ids             = fields.One2many('is.demande.achat.serie.line'  , 'da_id', u"Lignes")


    @api.multi
    def _lieu_livraison_id(self):
        user = self.env['res.users'].browse(self._uid)
        partner_id = user.company_id.partner_id.id
        return partner_id


    _defaults = {
        'date_creation'    : lambda *a: fields.datetime.now(),
        'createur_id'      : lambda obj, cr, uid, context: uid,
        'state'            : 'brouillon',
        'lieu_livraison_id': lambda self,cr,uid,context: self._lieu_livraison_id(cr,uid,context),
    }


    @api.model
    def create(self, vals):
        data_obj = self.env['ir.model.data']
        sequence_ids = data_obj.search([('name','=','is_demande_achat_serie_seq')])
        if sequence_ids:
            sequence_id = data_obj.browse(sequence_ids[0].id).res_id
            vals['name'] = self.env['ir.sequence'].get_id(sequence_id, 'id')
        obj = super(is_demande_achat_serie, self).create(vals)
        return obj


    @api.multi
    def vers_brouillon_action(self):
        for obj in self:
            obj.state="brouillon"


    @api.multi
    def vers_transmis_achat_action(self):
        for obj in self:
            obj.state="transmis_achat"


    @api.multi
    def vers_solde_action(self):
        for obj in self:
            obj.state="solde"


    @api.multi
    def vers_annule_action(self):
        for obj in self:
            obj.state="annule"


class is_demande_achat_serie_line(models.Model):
    _name='is.demande.achat.serie.line'
    _order='da_id,sequence'


    @api.depends('product_id','quantite','prix')
    def _compute(self):
        for obj in self:
            if obj.product_id:
                obj.uom_id=obj.product_id.uom_po_id
            obj.montant=obj.quantite*obj.prix

    da_id                  = fields.Many2one('is.demande.achat.serie', "Demande d'achat", required=True, ondelete='cascade', readonly=True)
    sequence               = fields.Integer('Ordre')
    product_id             = fields.Many2one('product.product', 'Article', domain=[('is_category_id.name','<','62')], required=True)
    uom_id                 = fields.Many2one('product.uom', "Unité d'achat", compute='_compute', readonly=True, store=True)
    quantite               = fields.Float("Quantité", digits=(14,4), required=True)
    prix                   = fields.Float("Prix"    , digits=(14,4))
    montant                = fields.Float("Montant", compute='_compute', readonly=True, store=True)


    @api.multi
    def product_id_on_change(self,parent,product_id):
        #nb=len(line_ids)
        print 'parent=',parent, len(parent.line_ids)
        #if nb>1:
        #    raise Warning('Une seule ligne autorisée !')


#    @api.multi
#    def product_id_change(self, product_id):
#        values = {}
#        if product_id:
#            product = self.env['product.product'].browse(product_id)
#            values['description']            = product.name
#            values['ref_client']             = product.is_ref_client
#            values['origine_id']             = product.is_origine_produit_id.id
#            values['nomenclature_douaniere'] = product.is_nomenclature_douaniere
#            values['qt_par_colis']           = product.is_uc_qt
#        return {'value': values}


#    @api.multi
#    def qt_change(self, product_id,qt_livree,qt_par_colis):
#        values = {}
#        if product_id:
#            product = self.env['product.product'].browse(product_id)
#            values['poids_net']  = product.weight_net*qt_livree
#            values['poids_brut'] = product.weight*qt_livree
#        nb_colis=0
#        if qt_par_colis>0:
#            nb_colis=qt_livree/qt_par_colis
#        values['nb_colis'] = nb_colis
#        return {'value': values}



