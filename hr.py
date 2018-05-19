# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _


class hr_employee(models.Model):
    _name = "hr.employee"
    _inherit = "hr.employee"

    def _badge_count(self):
        badge_obj = self.env['is.badge']
        for obj in self:
            nb = len(badge_obj.search([('employee', '=', obj.id)]))
            obj.is_badge_count=nb


    def _pointage_count(self):
        pointage_obj = self.env['is.pointage']
        for obj in self:
            nb = len(pointage_obj.search([('employee', '=', obj.id)]))
            obj.is_pointage_count=nb


    def action_view_badge(self, cr, uid, ids, context=None):
        res = {}
        res['context'] = "{'employee': " + str(ids[0]) + "}"
        return res


    is_site=fields.Selection([
            ("1", "Gray"), 
            ("4", "ST-Brice"), 
        ], "Site", required=False)
    is_matricule=fields.Char('Matricule', help='N° de matricule du logiciel de paye', required=False)
    is_categorie=fields.Selection([
            ("2x8" , "Équipe en 2x8"), 
            ("2x8r", "Équipe en 2x8 avec recouvrement"), 
            ("nuit", "Équipe de nuit"),
            ("3x8" , "en 3x8"),
            ("jour", "Personnel de journée"),
        ], "Catégorie de personnel", required=False)
    is_interimaire=fields.Boolean('Intérimaire',  help="Cocher pour indiquer que c'est un intérimaire")
    is_badge_count=fields.Integer('# Badges'      , compute='_badge_count'   , readonly=True, store=False)
    is_pointage_count=fields.Integer('# Pointages', compute='_pointage_count', readonly=True, store=False)
    is_jour1=fields.Float('Lundi')
    is_jour2=fields.Float('Mardi')
    is_jour3=fields.Float('Mercredi')
    is_jour4=fields.Float('Jeudi')
    is_jour5=fields.Float('Vendredi')
    is_jour6=fields.Float('Samedi')
    is_jour7=fields.Float('Dimanche')


