# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import Warning
from datetime import datetime

class is_instrument_mesure(models.Model):
    _name = 'is.instrument.mesure'
    _order = 'code_pg'

    @api.depends('famille_id', 'fabriquant_id')
    def _compute_periodicite(self):
        for obj in self:
            obj.periodicite = ''

    code_pg = fields.Char("Code PG")
    designation = fields.Char("Désignation")
    famille_id = fields.Many2one("is.famille.instrument", "Famille")
    fabriquant_id = fields.Many2one("res.partner", "Fabricant")
    num_serie = fields.Char("N° de série")
    date_reception = fields.Date("Date de réception")
    type = fields.Char("Type")
    etendue = fields.Char("Etendue")
    resolution = fields.Char("Résolution")
    type_boolean = fields.Boolean('Is Type?', default=False)
    etendue_boolean = fields.Boolean('Is Etendue?', default=False)
    resolution_boolean = fields.Boolean('Is Résolution?', default=False)
    site_id = fields.Many2one("is.emplacement.outillage", "Site d'affectation")
    lieu_stockage = fields.Char("Lieu de stockage")
    service_affecte = fields.Char("Personne/Service auquel est affecté l'instrument")
    
    
    frequence = fields.Selection([('intensive', 'utilisation quotidienne'), ('moyenne', 'utilisation plusieurs jours par semaine'),
                                  ('faible', 'utilisation 1 fois par semaine ou moins')], "Fréquence")
    periodicite = fields.Char("Périodicité", store=True, compute='_compute_periodicite')
    
    
    controle = fields.Selection([('creation', 'Création'), ('verification', 'Vérification'), ('maintenance', 'Maintenance'),
                                 ('arret', 'Arrêt'), ('visuel', 'Visuel'), ('etalonnage', 'étalonnage')], string="Contrôle")
    cause_arret = fields.Char("Cause arrêt")
    commentaire = fields.Char("Commentaire")
    date_controle = fields.Date("Date du contrôle")
    organisme_controleur = fields.Selection([('interne', 'Interne'), ('externe', 'Externe')], "Organisme contrôleur")
    fournisseur_id = fields.Many2one('res.partner', 'Fournisseur')
    classe = fields.Selection([('0', '0'), ('1', '1'), ('2', '2'), ('3', '3'), ('na', '/NA')], "Classe")
    classe_boolean = fields.Boolean('Is Classe?', default=False)
    etat_conformite = fields.Selection([('conforme', 'Conforme'), ('non_conforme', 'Non Conforme')], string="Etat de la conformité")
    rapport_de_controle = fields.Binary("Rapport de contrôle")
    
    @api.onchange('famille_id')
    def onchange_famille_id(self):
        self.type_boolean = self.famille_id.afficher_type
        self.etendue_boolean = self.famille_id.afficher_type
        self.resolution_boolean = self.famille_id.afficher_type
        self.classe_boolean = self.famille_id.afficher_classe
        
        
class is_famille_instrument(models.Model):
    _name = 'is.famille.instrument'
    
    name = fields.Char("Nom de la famille")
    intensive = fields.Char("INTENSIVE (fréquence f >= 1 fois / jour) en mois")
    moyenne = fields.Char("MOYENNE ( 1fois / 5 jours < f < 1fois / jour ) en mois")
    faible = fields.Char("FAIBLE (f <=1fois / 5 jours) en mois")
    tolerance = fields.Char("Tolérance")
    afficher_classe = fields.Boolean("Afficher le champ Classe", default=False)
    afficher_type = fields.Boolean("Afficher les champs Type, Etendue et Résolution", default=False)
    
    
