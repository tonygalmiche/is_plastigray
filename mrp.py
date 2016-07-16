# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _



class mrp_bom(models.Model):
    _name    = 'mrp.bom'
    _inherit = 'mrp.bom'
    _order   = 'product_tmpl_id'

    is_gamme_generique_id = fields.Many2one('mrp.routing', 'Gamme générique', help="Gamme générique utilisée dans le plan directeur")
    is_sous_traitance     = fields.Boolean('Nomenclature de sous-traitance')


class mrp_bom_line(models.Model):
    _name = 'mrp.bom.line'
    _inherit = 'mrp.bom.line'


    #Si la catégorie est 'Fantôme', tous les liens des nomenclatures doivent passer en 'Fantôme'
    @api.depends("product_id", "product_id.product_tmpl_id.is_category_id", "product_id.product_tmpl_id.is_category_id.fantome")
    def _type(self):
        for obj in self:
            type='normal'
            if obj.product_id:
                if obj.product_id.product_tmpl_id:
                    if obj.product_id.product_tmpl_id.is_category_id:
                        if obj.product_id.product_tmpl_id.is_category_id.fantome==True:
                            type='phantom'
            obj.type=type
    type = fields.Selection([('normal', 'Normal'), ('phantom', 'Phantom')], 'BoM Line Type', required=True, compute='_type')

    is_article_fourni = fields.Selection([('oui', 'Oui'), ('non', 'Non')], 'Article fourni')

    _defaults = {
        'is_article_fourni': 'non',
    }




class mrp_routing(models.Model):
    _name = 'mrp.routing'
    _inherit = 'mrp.routing'
    
    is_nb_empreintes = fields.Integer("Nombre d'empreintes par pièce", help="Nombre d'empreintes pour cette pièce dans le moule")
    is_coef_theia    = fields.Integer("Coefficient Theia"            , help="Nombre de pièces différentes dans le moule")

    _defaults = {
        'is_nb_empreintes': 1,
        'is_coef_theia': 1,
    }




class mrp_routing_workcenter(models.Model):
    _name    = 'mrp.routing.workcenter'
    _inherit = 'mrp.routing.workcenter'
    _order   = 'routing_id,sequence'
    

    @api.depends('is_nb_secondes')
    def _hour_nbr(self):
        for obj in self:
            v = 0.0
            obj.hour_nbr=obj.is_nb_secondes/float(3600)

    hour_nbr         = fields.Float("Nombre d'heures"      , digits=(12,6), method=True, type='float', store=True, readonly=True, compute='_hour_nbr')
    is_nb_secondes   = fields.Float("Nombre de secondes"   , digits=(12,2), required=False, help="Nombre de secondes")




class is_atelier(models.Model):
    _name='is.atelier'
    _order='name'
    name = fields.Char("Atelier", required=True)


class is_ilot(models.Model):
    _name='is.ilot'
    _order='name'
    name = fields.Char("Ilot", required=True)


class mrp_workcenter(models.Model):
    _inherit = 'mrp.workcenter'
    _order   = 'code,name'

    is_atelier_id = fields.Many2one('is.atelier', 'Atelier')
    is_ilot_id    = fields.Many2one('is.ilot'   , 'Ilot')

    is_ordre = fields.Integer("Ordre")





