# -*- coding: utf-8 -*-
from openerp import models,fields,api
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta


class is_piece_montabilite(models.Model):
    _name='is.piece.montabilite'
    _rec_name = 'code_pg'
    
    @api.depends('moule_ids')
    def compute_client_id(self):
        for rec in self:
            client_id = False
            for moule in rec.moule_ids:
                if moule.client_id:
                    client_id = moule.client_id.id
                    break;
            rec.client_id = client_id
    
    code_pg = fields.Char("Code PG", required=True)
    designation = fields.Char("Désignation")
    fabriquant = fields.Selection([('client','Client'),
                                   ('plastigray','Plastigray'),
                                   ('autre','Autre')
                                   ], string="Fabricant")
    fabricant_client_id = fields.Many2one('res.partner', string='Fabricant (Client)', domain=[('supplier','=',True),('is_company','=',True)])
    fabriquant_mold_id = fields.Many2one('is.mold', string='Fabricant (Moule)')
    fabriquant_autre = fields.Char("Fabricant (Autre)")
    date_reception = fields.Date("Date de réception")
    moule_ids = fields.Many2many('is.mold','is_piece_montabilite_id', 'is_mold_id_piece_mont', string='Moules affectés')
    client_id = fields.Many2one('res.partner', string='Client', compute="compute_client_id", store=True)
    site_id = fields.Many2one('is.database', string='Site')
    lieu_stockage = fields.Char("Lieu de stockage")
    periodicite = fields.Integer("Périodicité ( en mois )")
    type_controle = fields.Many2one('is.type.controle.gabarit', string='Type de contrôle')
    date_prochain_controle= fields.Date("Date prochain contrôle", compute='_compute_date_prochain_controle', readonly=True, store=True)


#    controle = fields.Selection([('creation','Création'),
#                                   ('verification','Vérification'),
#                                   ('maintenance','Maintenance'),
#                                   ('arret','Arrêt'),
#                                   ('visuel','Visuel'),
#                                   ], string="Contrôle")
#    cause_arret = fields.Char("Cause arrêt")
#    cause_visuel = fields.Char("Cause visuel")
#    date_controle = fields.Date("Date du contrôle")
#    date_prochain_controle= fields.Date("Date prochain contrôle", compute='_compute_date_prochain_controle', readonly=True, store=True)
#    organisme_controleur = fields.Selection([('interne','Interne'),
#                                             ('externe','Externe'),
#                                   ], string="Organisme contrôleur")
#    fournisseur_id = fields.Many2one('res.partner', string='Fournisseur')
#    etat_conformite = fields.Selection([('conforme','Conforme'),
#                                        ('non_conforme','Non Conforme'),
#                                   ], string="Etat de la conformité")
#    rapport_de_controle = fields.Binary(string='Rapport de contrôle')
    controle_ids = fields.One2many('is.historique.controle', 'piece_id', string='Historique des contrôles')


    @api.multi
    @api.depends('controle_ids','periodicite')
    def _compute_date_prochain_controle(self):
        for rec in self:
            if rec.controle_ids:
                date_controle=rec.controle_ids[0].date_controle
                if date_controle:
                    date_controle = datetime.strptime(date_controle, "%Y-%m-%d")
                    if rec.periodicite:
                        periodicite = int(rec.periodicite)
                    else:periodicite = 0
                    date_prochain_controle = date_controle + relativedelta(months=periodicite)
                    rec.date_prochain_controle = date_prochain_controle.strftime('%Y-%m-%d')


#    @api.multi
#    @api.depends('date_controle','periodicite')
#    def _compute_date_prochain_controle(self):
#        for rec in self:
#            if rec.date_controle:
#                date_controle = datetime.strptime(rec.date_controle, "%Y-%m-%d")
#                date_prochain_controle = date_controle + relativedelta(months=rec.periodicite)
#                rec.date_prochain_controle = date_prochain_controle.strftime('%Y-%m-%d')



#class is_historique_controle(models.Model):
#    _inherit='is.historique.controle'

#    piece_id = fields.Many2one('is.piece.montabilite', string='Piece Montabilite')

