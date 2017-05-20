# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _


class is_prechauffeur(models.Model):
    _name='is.prechauffeur'

    name = fields.Char(string='N° du préchauffeur')
    site_id = fields.Many2one('is.emplacement.outillage', string='Site')
    presse_id = fields.Many2one('is.presse', string='Affectation sur le site')
    constructeur_id = fields.Many2one('is.outillage.constructeur', string='CONSTRUCTEUR')
    type_prechauffeur = fields.Char(string='TYPE')
    num_serie = fields.Char(string='N° DE SERIE')
    date_fabrication = fields.Date(string='Date de fabrication')
    poids = fields.Integer(string='Poids (Kg)')
    longueur = fields.Integer(string='Longueur en mm')
    largeur = fields.Integer(string='largeur en mm')
    hauteur = fields.Integer(string='Hauteur en mm')
    type_fluide = fields.Selection([
        ('eau','Eau'),
        ('huile','Huile')], string='Type de fluide')
    temperature_maxi = fields.Integer(string='Température maximum (°C)')
    puissance_installee = fields.Integer(string='Puissance installée (KW)')
    puissance_chauffe = fields.Integer(string='Puissance de chauffe (KW)')
    puissance_refroidissement = fields.Integer(string='Puissance de refroidissement (KW)')
    debit_maximum = fields.Integer(string='Débit maximum (L/min)')
    pression_maximum = fields.Integer(string='Pression maximuù (BARS)')
    commande_deportee = fields.Selection([
        ('oui','Oui'),
        ('non','Non'),
    ], string='Commande déportée sur presse')
    option_depression = fields.Selection([
        ('oui','Oui'),
        ('non','Non'),
    ], string='Option déprésssion')
    mesure_debit = fields.Selection([
        ('oui','Oui'),
        ('non','Non'),
    ], string='Mesure débit')
