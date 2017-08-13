# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _


class is_prechauffeur(models.Model):
    _name='is.prechauffeur'
    _sql_constraints = [('name_uniq','UNIQUE(name)', u'Ce code existe déjà')]

    name              = fields.Char(string='N° du préchauffeur')
    site_id           = fields.Many2one('is.database', string='Site')
    presse_id         = fields.Many2one('is.presse', string='Affectation sur le site')
    moule_ids         = fields.Many2many('is.mold','is_prechauffeur_mold_rel','prechauffeur_id','mold_id', string="Moules affectés")
    constructeur      = fields.Char(string='Constructeur')
    marque            = fields.Char(string='Marque')
    type_prechauffeur = fields.Char(string='Type')
    num_serie         = fields.Char(string='N° de série')
    date_fabrication  = fields.Date(string='Date de fabrication')
    poids             = fields.Integer(string='Poids (Kg)')
    longueur          = fields.Integer(string='Longueur en mm')
    largeur           = fields.Integer(string='Largeur en mm')
    hauteur           = fields.Integer(string='Hauteur en mm')
    type_fluide       = fields.Selection([
        ('eau','Eau'),
        ('huile','Huile')], string='Type de fluide')
    temperature_maxi          = fields.Integer(string='Température maximum (°C)')
    puissance_installee       = fields.Integer(string='Puissance installée (KW)')
    puissance_chauffe         = fields.Integer(string='Puissance de chauffe (KW)')
    puissance_refroidissement = fields.Integer(string='Puissance de refroidissement (KW)')
    debit_maximum             = fields.Integer(string='Débit maximum (L/min)')
    pression_maximum          = fields.Integer(string='Pression maximum (BARS)')
    commande_deportee         = fields.Selection([
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
