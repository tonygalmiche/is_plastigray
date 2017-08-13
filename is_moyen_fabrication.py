# -*- coding: utf-8 -*-
from openerp import models,fields,api
import time
from datetime import datetime

class is_type_equipement(models.Model):
    _name='is.type.equipement'

    name = fields.Char("Name", required=True)


class is_moyen_fabrication(models.Model):
    _name='is.moyen.fabrication'
    _sql_constraints = [('name_uniq','UNIQUE(name)', u'Ce code existe déjà')]


    name = fields.Char("Code", required=True)
    type_equipement = fields.Many2one('is.type.equipement', string='Type équipement', required=True)
    designation = fields.Char("Désignation", required=False)
    mold_ids     = fields.Many2many('is.mold'    ,'is_moyen_fabrication_id'         , 'is_mold_id_fabric'    , string='Moule')
    dossierf_ids = fields.Many2many('is.dossierf','is_moyen_fabrication_dossierf_id', 'is_dossierf_id_fabric', string='Dossier F')
    base_capacitaire = fields.Char("Base capacitaire")
    site_id = fields.Many2one('is.database', string='Site')
    emplacement = fields.Char("Emplacement")
    fournisseur_id = fields.Many2one('res.partner', string='Fournisseur', domain=[('supplier','=',True),('is_company','=',True)])
    ref_fournisseur = fields.Char("Réf fournisseur")
    date_creation = fields.Date('Date de création')
    date_fin = fields.Date('Date de fin')


