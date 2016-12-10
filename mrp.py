# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _



class mrp_bom(models.Model):
    _name     = 'mrp.bom'
    _inherit  = 'mrp.bom'
    _order    = 'product_tmpl_id'
    _rec_name = 'product_tmpl_id'

    is_gamme_generique_id = fields.Many2one('mrp.routing', 'Gamme générique', help="Gamme générique utilisée dans le plan directeur")
    is_sous_traitance     = fields.Boolean('Nomenclature de sous-traitance')
    is_negoce             = fields.Boolean('Nomenclature de négoce')
    is_inactive           = fields.Boolean('Nomenclature inactive')
    is_qt_uc              = fields.Integer("Qt par UC", compute='_compute')
    is_qt_um              = fields.Integer("Qt par UM", compute='_compute')
    segment_id            = fields.Many2one('is.product.segment', 'Segment', related='product_tmpl_id.segment_id', readonly=True)


    @api.one
    @api.depends('product_tmpl_id')
    def _compute(self):
        for obj in self:
            obj.is_qt_uc = obj.product_tmpl_id.get_uc()
            obj.is_qt_um = obj.product_tmpl_id.get_um()





class mrp_bom_line(models.Model):
    _name = 'mrp.bom.line'
    _inherit = 'mrp.bom.line'
    _order = "sequence, id"


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
    is_qt_uc          = fields.Float("Qt par UC", digits=(12, 2), compute='_compute')
    is_qt_um          = fields.Float("Qt par UM", digits=(12, 2), compute='_compute')
    is_bom            = fields.Boolean('Nomenclature existante' , compute='_compute')

    _defaults = {
        'is_article_fourni': 'non',
    }


    @api.one
    @api.depends('bom_id.product_tmpl_id', 'product_qty')
    def _compute(self):
        for obj in self:
            obj.is_qt_uc = obj.product_qty*obj.bom_id.product_tmpl_id.get_uc()
            obj.is_qt_um = obj.product_qty*obj.bom_id.product_tmpl_id.get_um()

            product_tmpl_id=obj.product_id.product_tmpl_id.id
            nomenclatures=self.env['mrp.bom'].search([['product_tmpl_id', '=', product_tmpl_id]])
            is_bom=False
            if len(nomenclatures)>0:
                is_bom=True
            obj.is_bom=is_bom





    @api.multi
    def action_acces_nomenclature(self):
        for obj in self:
            product_tmpl_id=obj.product_id.product_tmpl_id.id
            nomenclatures=self.env['mrp.bom'].search([['product_tmpl_id', '=', product_tmpl_id]])
            if len(nomenclatures)>0:
                res_id=nomenclatures[0].id
                view_id=self.env.ref('is_plastigray.is_mrp_bom_form_view')
                return {
                    'name': obj.product_id.name,
                    'view_mode': 'form',
                    'view_type': 'form',
                    'res_model': 'mrp.bom',
                    'type': 'ir.actions.act_window',
                    'view_id': view_id.id,
                    'res_id': res_id,
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
    is_nb_mod        = fields.Selection([('0.25', '0.25'), ('0.3', '0.3'), ('0.5', '0.5'), ('0.75', '0.75'), ('1', '1'), ('1.5', '1.5'), ('2', '2')], 'Nombre de MOD', help='Donnée utilisée en particlier pour le planning')



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




class mrp_production_workcenter_line(models.Model):
    _inherit = 'mrp.production.workcenter.line'

    is_ordre       = fields.Integer("Ordre", help="Ordre sur le planning")
    is_qt_restante = fields.Integer("Quantité restante", help="Quantité restante pour le planning")
    is_tps_restant = fields.Float("Temps restant", help="Temps restant pour le planning")
    is_date_tri    = fields.Datetime('Date tri', help="Date de tri du planning")

