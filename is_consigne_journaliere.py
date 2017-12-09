# -*- coding: utf-8 -*-
import datetime
from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning
import datetime


class is_consigne_journaliere(models.Model):
    _name = "is.consigne.journaliere"
    _description = "Consignes journalieres"
    _order='create_date desc'

    name                = fields.Char('Titre')
    chef_atelier        = fields.Char("Chef d'atelier")
    remarque_generale   = fields.Text('Remarque générale')
    date_derniere_modif = fields.Datetime("Date dernière modification", readonly=True)
    total_mod_inj       = fields.Float('Total MOD Injection' , readonly=True, compute='_compute', store=True)
    total_mod_ass       = fields.Float('Total MOD Assemblage', readonly=True, compute='_compute', store=True)
    injection_ids       = fields.One2many('is.consigne.journaliere.inj'  , 'consigne_id', u"Injection" , copy=True)
    assemblage_ids      = fields.One2many('is.consigne.journaliere.ass'  , 'consigne_id', u"Assemblage", copy=True)


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
    presse_id   = fields.Many2one('mrp.workcenter', 'Presse', 
                    domain=[('resource_type','=','material'),('code','<','9000'),('name','not ilike','GENERIQUE')])
    of1_id      = fields.Many2one('is.mrp.production.workcenter.line', 'OF en cours')
    mod1        = fields.Float('MOD')
    operateur   = fields.Char('Opérateur')
    moule1      = fields.Char('Moule')
    matiere1    = fields.Char('Matière')
    tps_arret   = fields.Char('Tps arrêt matière')
    heure       = fields.Char('Heure')
    of2_id      = fields.Many2one('is.mrp.production.workcenter.line', 'OF suivant')
    mod2        = fields.Float('MOD')
    moule2      = fields.Char('Moule')
    matiere2    = fields.Char('Matière')
    remarque    = fields.Text('Remarques / Consignes')

    @api.multi
    def of1_id_change(self, mpwl_id):
        values = {}
        if mpwl_id:
            mpwl = self.env['is.mrp.production.workcenter.line'].browse(mpwl_id)
            mod=0
            matieres=[]
            for line in mpwl.name.product_lines:
                code=line.product_id.is_code
                if code[:1]=='5':
                    if code not in matieres:
                        matieres.append(code)
            matieres=u', '.join(matieres)
            for line in mpwl.name.routing_id.workcenter_lines:
                if line.is_nb_mod:
                    mod=line.is_nb_mod
            values['mod1']     = mod
            values['moule1']   = mpwl.name.product_id.is_mold_dossierf
            values['matiere1'] = matieres
        return {'value': values}

    @api.multi
    def of2_id_change(self, mpwl_id):
        values = {}
        if mpwl_id:
            mpwl = self.env['is.mrp.production.workcenter.line'].browse(mpwl_id)
            mod=0
            matieres=[]
            for line in mpwl.name.product_lines:
                code=line.product_id.is_code
                if code[:1]=='5':
                    if code not in matieres:
                        matieres.append(code)
            matieres=u', '.join(matieres)
            for line in mpwl.name.routing_id.workcenter_lines:
                if line.is_nb_mod:
                    mod=line.is_nb_mod
            matiere=mpwl.name.product_id.is_couleur
            values['mod2']     = mod
            values['moule2']   = mpwl.name.product_id.is_mold_dossierf
            values['matiere2'] = matieres
        return {'value': values}



class is_consigne_journaliere_ass(models.Model):
    _name='is.consigne.journaliere.ass'
    _order='consigne_id,sequence'

    consigne_id    = fields.Many2one('is.consigne.journaliere', 'Consigne journaliere', required=True, ondelete='cascade', readonly=True)
    sequence       = fields.Integer('Ordre')
    poste_id       = fields.Many2one('mrp.workcenter', 'Poste', 
                    domain=[('resource_type','=','material'),('code','>=','9000'),('name','not ilike','GENERIQUE')])
    priorite       = fields.Char('Priorité')
    mod            = fields.Float('MOD')
    operateur      = fields.Char('Opérateur')
    of1_id         = fields.Many2one('is.mrp.production.workcenter.line', 'OF en cours')
    of2_id         = fields.Many2one('is.mrp.production.workcenter.line', 'OF suivant')
    remarque       = fields.Text('Remarques / Consignes')

