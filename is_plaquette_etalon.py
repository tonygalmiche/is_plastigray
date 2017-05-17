# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning
from datetime import datetime


class is_plaquette_etalon(models.Model):
    _name='is.plaquette.etalon'
    _order='code_pg'

    code_pg = fields.Char("Code PG", required=True)
    designation = fields.Char("Désignation", required=True)
    fabriquant_id = fields.Many2one("res.partner","Fabricant")
    date_reception = fields.Date("Date de réception")
    site_id = fields.Many2one("is.emplacement.outillage","Site d'affectation")
    lieu_stockage = fields.Char("Lieu de stockage")
    
    periodicite = fields.Integer("Périodicité (en mois)")
    type_controle = fields.Selection([('colorimetre','colorimètre'),('visuel','visuel')],string="Type de contrôle")
    
    controle = fields.Selection([('verification','Vérification'),('arret','Arrêt'),('visuel','Visuel')],string="Contrôle")
    cause_arret = fields.Char("Cause Arrêt")
    commentaire = fields.Char("Commentaire")
    date_controle = fields.Date("Date du Contrôle")
    organisme_controleur = fields.Selection([('interne','Interne'),('externe', 'Externe')],string="Organisme contrôleur")
    fournisseur_id = fields.Many2one('res.partner','Fournisseur')
    etat_conformite = fields.Selection([('conforme','Conforme'),('non_conforme', 'Non Conforme')],string="Etat de la conformité")
    rapport_de_controle = fields.Binary('Rapport de contrôle')
    controle_ids = fields.One2many('is.historique.controle', 'plaquette_id', string='Historique des contrôles')
