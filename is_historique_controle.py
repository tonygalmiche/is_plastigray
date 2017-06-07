# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning
from datetime import datetime

class is_historique_controle(models.Model):
    _name='is.historique.controle'
    _order='date_controle desc'
    _rec_name='date_controle'

    plaquette_id = fields.Many2one('is.plaquette.etalon', string='Plaquette étalon')
    instrument_id = fields.Many2one('is.instrument.mesure', string='Instruments de mesure')
    gabarit_id = fields.Many2one('is.gabarit.controle', string='Gabarit de contrôle')
    date_controle = fields.Date(string='Date du contrôle', default=fields.Date.context_today, copy=False)
    site_id = fields.Many2one('is.database', string='Site')
    affectation = fields.Char(string='Affectation')
    operation = fields.Selection([
        ('C','Création'),
        ('V','Vérification'),
        ('E','Étalonnage'),
        ('M','Maintenance'),
        ('T','Transfert de société'),
        ('A','Arrêt étalonnage'),
        ('F',' Fin de vie')
    ], string='Opération')
    organisme = fields.Char(string='Organisme')
    resultat = fields.Char(string='Résultat')
    commentaire = fields.Char(string='Commentaire')
    classe = fields.Char(string='Classe')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4
