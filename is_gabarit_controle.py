# -*- coding: utf-8 -*-
from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning
from datetime import datetime

class is_gabarit_controle(models.Model):
    _name='is.gabarit.controle'
    _order='code_pg'
    _rec_name='code_pg'
    
    code_pg        = fields.Char("Code PG"    , required=True)
    designation    = fields.Char("Désignation", required=True)
    fabriquant_id  = fields.Many2one("res.partner","Fabricant")
    date_reception = fields.Date("Date de réception")
    reference_plan = fields.Char("Référence plan")
    indice_plan    = fields.Char("Indice plan")
    moule_ids      = fields.Many2many('is.mold','is_gabarit_mold_rel','gabarit_id','mold_id', string="Moules affectés")
    client_id      = fields.Many2one("res.partner","Client")
    site_id        = fields.Many2one("is.emplacement.outillage","Site d'affectation")
    lieu_stockage  = fields.Char("Lieu de stockage")
    periodicite    = fields.Integer("Périodicité ( en mois )")
    type_controle  = fields.Many2one("is.type.controle.gabarit","Type de contrôle")
    controle       = fields.Selection([('creation','Création'),('verification','Vérification'),
                                 ('maintenance','Maintenance'),('arret','Arrêt')], string="Contrôle")
    cause_arret          = fields.Char("Cause arrêt")
    date_controle        = fields.Date("Date du contrôle")
    organisme_controleur = fields.Selection([('interne','Interne'),('externe', 'Externe')], string="Organisme contrôleur")
    fournisseur_id       = fields.Many2one("res.partner","Fournisseur")
    etat_conformite      = fields.Selection([('conforme','Conforme'),('non_conforme','Non Conforme')], string="Etat de la conformité")
    rapport_de_controle  = fields.Binary("Rapport de contrôle ")
    controle_ids = fields.One2many('is.historique.controle', 'gabarit_id', string='Historique des contrôles')
    
    

class is_emplacement_outillage(models.Model):
    _name = "is.emplacement.outillage"
    
    name = fields.Char("Name")
    
    
class is_type_controle_gabarit(models.Model):
    _name = "is.type.controle.gabarit"
    
    name = fields.Char("Name")
    
    
    
