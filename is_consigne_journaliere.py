# -*- coding: utf-8 -*-
import datetime
from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning
import datetime


class is_consigne_journaliere(models.Model):
    _name = "is.consigne.journaliere"
    _description = "Consignes journalieres"
    _order='name desc'

    name                = fields.Char('Titre')
    chef_atelier        = fields.Char("Chef d'atelier")
    remarque_generale   = fields.Text('Remarque générale')
    date_derniere_modif = fields.Datetime("Date dernière modification", readonly=True)
    total_mod_inj       = fields.Float('Total MOD Injection' , readonly=True, compute='_compute', store=True)
    total_mod_ass       = fields.Float('Total MOD Assemblage', readonly=True, compute='_compute', store=True)
    injection_ids       = fields.One2many('is.consigne.journaliere.inj'  , 'consigne_id', u"Injection")
    assemblage_ids      = fields.One2many('is.consigne.journaliere.ass'  , 'consigne_id', u"Assemblage")


    @api.depends('injection_ids','assemblage_ids')
    def _compute(self):
        for obj in self:
            total_mod_inj=0
            for line in obj.injection_ids:
                total_mod_inj=total_mod_inj+line.mod1
            total_mod_ass=0
            for line in obj.assemblage_ids:
                total_mod_ass=total_mod_ass+line.mod
            obj.total_mod_inj=total_mod_inj
            obj.total_mod_ass=total_mod_ass


    @api.multi
    def write(self,vals):
        vals['date_derniere_modif']=datetime.datetime.now()
        res = super(is_consigne_journaliere, self).write(vals)
        return res




class is_consigne_journaliere_inj(models.Model):
    _name='is.consigne.journaliere.inj'
    _order='consigne_id,sequence'

    consigne_id = fields.Many2one('is.consigne.journaliere', 'Consigne journaliere', required=True, ondelete='cascade', readonly=True)
    sequence    = fields.Integer('Ordre')
    presse      = fields.Char('Presse')
    numof1_id   = fields.Many2one('mrp.production', 'OF en cours', domaine=[('state','!=','done')])
    mod1        = fields.Float('MOD')
    operateur   = fields.Char('Opérateur')
    moule1      = fields.Char('Moule')
    matiere1    = fields.Char('Matière')
    tps_arret   = fields.Char('Tps arrêt matière')
    heure       = fields.Char('Heure')
    numof2_id   = fields.Many2one('mrp.production', 'OF suivant', domaine=[('state','!=','done')])
    mod2        = fields.Float('MOD')
    moule2      = fields.Char('Moule')
    matiere2    = fields.Char('Matière')
    remarque    = fields.Text('Remarques / Consignes')

    @api.multi
    def numof1_id_change(self, production_id):
        values = {}
        if production_id:
            production = self.env['mrp.production'].browse(production_id)
            mod=0
            for line in production.routing_id.workcenter_lines:
                if line.is_nb_mod:
                    mod=line.is_nb_mod
            matiere=production.product_id.is_couleur
            values['mod1']     = mod
            values['moule1']   = production.product_id.is_mold_dossierf
            values['matiere1'] = matiere
        return {'value': values}

    @api.multi
    def numof2_id_change(self, production_id):
        values = {}
        if production_id:
            production = self.env['mrp.production'].browse(production_id)
            mod=0
            for line in production.routing_id.workcenter_lines:
                if line.is_nb_mod:
                    mod=line.is_nb_mod
            matiere=production.product_id.is_couleur
            values['mod2']     = mod
            values['moule2']   = production.product_id.is_mold_dossierf
            values['matiere2'] = matiere
        return {'value': values}



class is_consigne_journaliere_ass(models.Model):
    _name='is.consigne.journaliere.ass'
    _order='consigne_id,sequence'

    consigne_id    = fields.Many2one('is.consigne.journaliere', 'Consigne journaliere', required=True, ondelete='cascade', readonly=True)
    sequence       = fields.Integer('Ordre')
    poste          = fields.Char('Poste')
    priorite       = fields.Char('Priorité')
    mod            = fields.Float('MOD')
    operateur      = fields.Char('Opérateur')
    of_en_cours_id = fields.Many2one('mrp.production', 'OF en cours', domaine=[('state','!=','done')])
    of_suivant_id  = fields.Many2one('mrp.production', 'OF suivant', domaine=[('state','!=','done')])
    remarque       = fields.Text('Remarques / Consignes')





