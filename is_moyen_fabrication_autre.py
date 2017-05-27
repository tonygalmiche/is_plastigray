# -*- coding: utf-8 -*-

from openerp import models,fields,api

class is_moyen_fabrication_autre(models.Model):
    _name='is.moyen.fabrication.autre'

    name            = fields.Char(string='Numéro')
    type_equipement = fields.Many2one('is.type.equipement', string='Type équipement')
    designation     = fields.Char(string='Désignation')
    mold_id         = fields.Many2one('is.mold', string='Moule')
    site_id         = fields.Many2one('is.database', string='Site')
    emplacement     = fields.Char(string='Emplacement')


