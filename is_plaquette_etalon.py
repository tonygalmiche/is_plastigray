# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning
from datetime import datetime
from dateutil.relativedelta import relativedelta


class is_plaquette_etalon(models.Model):
    _name='is.plaquette.etalon'
    _order='code_pg'
    _rec_name='code_pg'
    _sql_constraints = [('code_pg_uniq','UNIQUE(code_pg)', u'Ce code existe déjà')]

    code_pg = fields.Char("Code PG", required=True)
    designation = fields.Char("Désignation", required=True)
    #fabriquant_id = fields.Many2one("res.partner","Fabricant")
    fabriquant     = fields.Char("Fabricant")
    date_reception = fields.Date("Date de réception")
    site_id = fields.Many2one("is.database", "Site")
    lieu_stockage = fields.Char("Lieu de stockage")
    
    periodicite = fields.Integer("Périodicité (en mois)")
    type_controle = fields.Selection([('colorimetre','colorimètre'),('visuel','visuel')],string="Type de contrôle")
    date_prochain_controle= fields.Date("Date prochain contrôle", compute='_compute_date_prochain_controle', readonly=True, store=True)    


#    controle = fields.Selection([('verification','Vérification'),('arret','Arrêt'),('visuel','Visuel')],string="Contrôle")
#    cause_arret = fields.Char("Cause Arrêt")
#    commentaire = fields.Char("Commentaire")
#    date_controle = fields.Date("Date du Contrôle")
#    date_prochain_controle= fields.Date("Date prochain contrôle", compute='_compute_date_prochain_controle', readonly=True, store=True)
#    organisme_controleur = fields.Selection([('interne','Interne'),('externe', 'Externe')],string="Organisme contrôleur")
#    fournisseur_id = fields.Many2one('res.partner','Fournisseur')
#    etat_conformite = fields.Selection([('conforme','Conforme'),('non_conforme', 'Non Conforme')],string="Etat de la conformité")
#    rapport_de_controle = fields.Binary('Rapport de contrôle')
    controle_ids = fields.One2many('is.historique.controle', 'plaquette_id', string='Historique des contrôles')



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


