# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning


class is_rgpd_service(models.Model):
    _name='is.rgpd.service'
    _order='name'

    name = fields.Char("Service", required=True)


class is_rgpd_traitement(models.Model):
    _name='is.rgpd.traitement'
    _order='name'

    name                     = fields.Char("N° du traitement", readonly=True)
    traitement               = fields.Char("Traitement", required=True)
    annee_creation           = fields.Char("Année de création", required=True)
    mise_a_jour              = fields.Char("Mise à jour")
    service_id               = fields.Many2one('is.rgpd.service', 'Service responsable du traitement', required=True)
    finalite                 = fields.Text("Finalité principale", required=True)
    sous_finalite            = fields.Text("Sous finalité")
    mesure_technique         = fields.Text("Mesure de sécurité technique", required=True)
    mesure_organisationnelle = fields.Text("Mesure organisationnelle", required=True)
    commentaire              = fields.Text("Commentaire")
    createur_id              = fields.Many2one('res.users', 'Créateur', required=True)
    date_creation            = fields.Date("Date de création")
    conforme                 = fields.Selection([('Oui', 'Oui'),('Non', 'Non')], "Conforme")
    action_id                = fields.Many2one('is.rgpd.action', 'Action')


    _defaults = {
        'createur_id'  : lambda obj, cr, uid, context: uid,
        'date_creation': lambda *a: fields.datetime.now(),
    }

    @api.model
    def create(self, vals):
        data_obj = self.env['ir.model.data']
        sequence_ids = data_obj.search([('name','=','is_rgpd_traitement_seq')])
        if sequence_ids:
            sequence_id = data_obj.browse(sequence_ids[0].id).res_id
            vals['name'] = self.env['ir.sequence'].get_id(sequence_id, 'id')
        obj = super(is_rgpd_traitement, self).create(vals)
        return obj


    def name_get(self, cr, uid, ids, context=None):
        res = []
        for obj in self.browse(cr, uid, ids, context=context):
            name=u'['+obj.name+u'] '+obj.traitement
            res.append((obj.id,name))
        return res

    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if name:
            ids = self.search(cr, user, ['|',('name','ilike', name),('traitement','ilike', name)], limit=limit, context=context)
        else:
            ids = self.search(cr, user, args, limit=limit, context=context)
        result = self.name_get(cr, user, ids, context=context)
        return result



    @api.multi
    def liste_donnees_action(self):
        for obj in self:
            return {
                'name': u'Données personnelles',
                'view_mode': 'tree,form',
                'view_type': 'form',
                'res_model': 'is.rgpd.donnee.personnelle',
                'domain': [
                    ('traitement_ids','in', obj.id),
                ],
                'type': 'ir.actions.act_window',
                'limit': 100,
            }





class is_rgpd_lieu_stockage(models.Model):
    _name='is.rgpd.lieu.stockage'
    _order='name'

    name = fields.Char("Traitement", required=True)


class is_rgpd_action(models.Model):
    _name='is.rgpd.action'
    _order='name'

    name            = fields.Char("N° action", readonly=True)
    action          = fields.Char("Action", required=True)
    responsable_id  = fields.Many2one('res.users', 'Responsable', required=True)
    date_fin_prevue = fields.Date("Date de fin prévue", required=True)
    date_realisee   = fields.Date("Date réalisée")

    @api.model
    def create(self, vals):
        data_obj = self.env['ir.model.data']
        sequence_ids = data_obj.search([('name','=','is_rgpd_action_seq')])
        if sequence_ids:
            sequence_id = data_obj.browse(sequence_ids[0].id).res_id
            vals['name'] = self.env['ir.sequence'].get_id(sequence_id, 'id')
        obj = super(is_rgpd_action, self).create(vals)
        return obj


    @api.multi
    def write(self,vals):
        for obj in self:
            traitements=self.env['is.rgpd.traitement'].search([('action_id','=',obj.id)])
            for traitement in traitements:
                traitement.conforme='Oui'
            donnees=self.env['is.rgpd.donnee.personnelle'].search([('action_id','=',obj.id)])
            for donnee in donnees:
                donnee.conforme='Oui'
        res = super(is_rgpd_action, self).write(vals)
        return res


    def name_get(self, cr, uid, ids, context=None):
        res = []
        for obj in self.browse(cr, uid, ids, context=context):
            name=u'['+obj.name+u'] '+obj.action
            res.append((obj.id,name))
        return res

    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if name:
            ids = self.search(cr, user, ['|',('name','ilike', name),('action','ilike', name)], limit=limit, context=context)
        else:
            ids = self.search(cr, user, args, limit=limit, context=context)
        result = self.name_get(cr, user, ids, context=context)
        return result


    @api.multi
    def liste_donnees_action(self):
        for obj in self:
            return {
                'name': u'Données personnelles',
                'view_mode': 'tree,form',
                'view_type': 'form',
                'res_model': 'is.rgpd.donnee.personnelle',
                'domain': [
                    ('action_id','=', obj.id),
                ],
                'type': 'ir.actions.act_window',
                'limit': 100,
            }


    @api.multi
    def liste_traitemments_action(self):
        for obj in self:
            return {
                'name': u'Traitements',
                'view_mode': 'tree,form',
                'view_type': 'form',
                'res_model': 'is.rgpd.traitement',
                'domain': [
                    ('action_id','=', obj.id),
                ],
                'type': 'ir.actions.act_window',
                'limit': 100,
            }




class is_rgpd_donnee_personnelle(models.Model):
    _name='is.rgpd.donnee.personnelle'
    _order='name'

    name               = fields.Char("Donnée personnelle", required=True)
    service_id         = fields.Many2one('is.rgpd.service', 'Service responsable de la donnée', required=True)
    traitement_ids     = fields.Many2many('is.rgpd.traitement','is_rgpd_donnee_personnelle_traitement_rel','donnee_personnelle_id','traitement_id', string="Traitements")
    lieu_stockage_id   = fields.Many2one('is.rgpd.lieu.stockage', 'Lieu de stockage', required=True)
    duree_conservation = fields.Char("Durée de conservation")
    acces              = fields.Char("Qui a accès")
    commentaire        = fields.Text("Commentaire")
    createur_id        = fields.Many2one('res.users', 'Créateur', required=True)
    date_creation      = fields.Date("Date de création")
    conforme           = fields.Selection([('Oui', 'Oui'),('Non', 'Non')], "Conforme")
    action_id          = fields.Many2one('is.rgpd.action', 'Action')

    _defaults = {
        'createur_id'  : lambda obj, cr, uid, context: uid,
        'date_creation': lambda *a: fields.datetime.now(),
    }


    @api.multi
    def liste_traitemments_action(self):
        for obj in self:
            traitements=[]
            for traitement in obj.traitement_ids:
                traitements.append(traitement.id)
            return {
                'name': u'Traitements',
                'view_mode': 'tree,form',
                'view_type': 'form',
                'res_model': 'is.rgpd.traitement',
                'domain': [
                    ('id','in', traitements),
                ],
                'type': 'ir.actions.act_window',
                'limit': 100,
            }





