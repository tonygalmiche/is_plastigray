# -*- coding: utf-8 -*-

from openerp import models,fields,api

class is_moyen_fabrication_autre(models.Model):
    _name='is.moyen.fabrication.autre'
    _sql_constraints = [('name_uniq','UNIQUE(name)', u'Ce code existe déjà')]

    name            = fields.Char(string='Code', required=True)
    type_equipement = fields.Many2one('is.type.equipement', string='Type équipement', required=True)
    designation     = fields.Char(string='Désignation', required=False)
    mold_id         = fields.Many2one('is.mold'    , string='Moule')
    dossierf_id     = fields.Many2one('is.dossierf', string='Dossier F')
    site_id         = fields.Many2one('is.database', string='Site')
    emplacement     = fields.Char(string='Emplacement')


