# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning
import datetime

#TODO : 

class is_tarif_cial(models.Model):
    _name='is.tarif.cial'
    _order='product_id, partner_id, indice_prix desc'
    _sql_constraints = [('is_indice_prix_uniq','UNIQUE(partner_id, product_id,indice_prix)', 'Cet indice de prix existe déja pour ce client et cet article')]

    display_name        = fields.Char(string='Name', compute='_compute_display_name')
    partner_id          = fields.Many2one('res.partner', 'Client'      , required=True)
    product_id          = fields.Many2one('product.template', 'Article', required=True)
    indice_prix         = fields.Integer("Indice Prix"                 , required=True)
    date_debut          = fields.Date("Date de début")
    date_fin            = fields.Date("Date de fin")
    type_evolution      = fields.Char("Type évolution")
    tarif_matiere       = fields.Float("Tarif Matière"      , digits=(12, 4))
    part_matiere        = fields.Float("Part Matière"       , digits=(12, 4))
    part_composant      = fields.Float("Part Composant"     , digits=(12, 4))
    part_emballage      = fields.Float("Part Emballage"     , digits=(12, 4))
    va_injection        = fields.Float("VA Injection"       , digits=(12, 4))
    va_assemblage       = fields.Float("VA Assemblage"      , digits=(12, 4))
    frais_port          = fields.Float("Frais de Port"      , digits=(12, 4))
    logistique          = fields.Float("Logistique"         , digits=(12, 4))
    amortissement_moule = fields.Float("Amortissement Moule", digits=(12, 4))
    surcout_pre_serie   = fields.Float("Surcôut pré-série"  , digits=(12, 4))
    prix_vente          = fields.Float("Prix de Vente"      , digits=(12, 4))
    numero_dossier      = fields.Char("Numéro de dossier")

    @api.one
    @api.depends('product_id', 'indice_prix')
    def _compute_display_name(self):
        #names = [self.parent_id.name, self.name]
        for obj in self:
            self.display_name = obj.product_id.is_code + " ("+str(obj.indice_prix)+")"

    _defaults = {
        'indice_prix': 999,
    }


    @api.multi
    def copy(self,vals):
        for obj in self:
            res=self.env['is.tarif.cial'].search([
                ['partner_id', '=', obj.partner_id.id], 
                ['product_id', '=', obj.product_id.id],
                ['indice_prix', '!=', 999],
            ], order="indice_prix desc", limit=1)
            indice_prix=1
            for line in res:
                indice_prix=line.indice_prix+1
            vals.update({
                'indice_prix': indice_prix,
            })
        return super(is_tarif_cial, self).copy(vals)






