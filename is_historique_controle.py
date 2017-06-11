# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning
from datetime import datetime

class is_historique_controle(models.Model):
    _name='is.historique.controle'
    _order='date_controle desc'
    _rec_name='date_controle'

    plaquette_id  = fields.Many2one('is.plaquette.etalon' , string='Plaquette étalon')
    instrument_id = fields.Many2one('is.instrument.mesure', string='Instruments de mesure')
    gabarit_id    = fields.Many2one('is.gabarit.controle' , string='Gabarit de contrôle')
    piece_id      = fields.Many2one('is.piece.montabilite', string='Piece Montabilite')


    @api.depends('instrument_id.famille_id')
    def _compute(self):
        for obj in self:
            #print self, self.instrument_id.famille_id.afficher_classe
            obj.classe_boolean = obj.instrument_id.famille_id.afficher_classe


#    operation_controle = fields.Selection([
#        ('creation', 'Création'), 
#        ('verification', 'Vérification'), 
#        ('maintenance', 'Maintenance'),
#        ('arret', 'Arrêt'), 
#        ('visuel', 'Visuel'), 
#        ('etalonnage', 'étalonnage')
#    ], string="Opération de contrôle", required=True)


    operation_controle_id   = fields.Many2one('is.operation.controle', 'Opération de contrôle', required=True)
    operation_controle_code = fields.Char("Code de l'Opération de contrôle", related='operation_controle_id.code')

    cause_arret   = fields.Char("Cause arrêt")
    cause_visuel  = fields.Char("Cause visuel")
    date_controle = fields.Date(string='Date du contrôle', default=fields.Date.context_today, copy=False, required=True)

    organisme_controleur = fields.Selection([('interne', 'Interne'), ('externe', 'Externe')], "Organisme contrôleur", required=True)
    fournisseur_id       = fields.Many2one('res.partner', 'Fournisseur')
    classe               = fields.Selection([('0', '0'), ('1', '1'), ('2', '2'), ('3', '3'), ('na', '/NA')], "Classe")
    classe_boolean       = fields.Boolean('Is Classe?', compute=_compute, store=False)
    resultat             = fields.Char(string='Résultat')
    etat_conformite      = fields.Selection([('conforme', 'Conforme'), ('non_conforme', 'Non Conforme')], string="Etat de la conformité", required=True)
    rapport_de_controle  = fields.Binary("Rapport de contrôle")



class is_operation_controle(models.Model):
    _name='is.operation.controle'
    _order='name'

    name       = fields.Char(string='Opération de contrôle'          , required=True)
    code       = fields.Char(string="Code de l'Opération de contrôle", required=True)
    plaquette  = fields.Boolean('Plaquette étalon')
    instrument = fields.Boolean('Instruments de mesure')
    gabarit    = fields.Boolean('Gabarit de contrôle')
    piece      = fields.Boolean('Piece Montabilite')




# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4
