# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning


class is_demande_transport(models.Model):
    _name='is.demande.transport'
    _order='name desc'

    name                 = fields.Char("N° de demande", readonly=True)
    type_demande         = fields.Selection([('transport', 'Transport'),('enlevement', 'Enlèvement')], "Type de demande", required=True)
    demandeur_id         = fields.Many2one('res.users', 'Demandeur', required=True)
    date_demande         = fields.Date("Date de la demande", required=True)
    dest_raison_sociale  = fields.Char("Raison Sociale", required=True)
    dest_adresse1        = fields.Char("Ligne adresse 1")
    dest_adresse2        = fields.Char("Ligne adresse 2")
    dest_code_postal     = fields.Char("Code postal")
    dest_ville           = fields.Char("Ville")
    dest_pays            = fields.Char("Pays")
    contact              = fields.Char("Contact")
    poids_net            = fields.Float("Poids net")
    poids_brut           = fields.Float("Poids brut")
    colisage             = fields.Char("Colisage")
    enlev_raison_sociale = fields.Char("Raison Sociale")
    enlev_adresse1       = fields.Char("Ligne adresse 1")
    enlev_adresse2       = fields.Char("Ligne adresse 2")
    enlev_code_postal    = fields.Char("Code postal")
    enlev_ville          = fields.Char("Ville")
    enlev_pays           = fields.Char("Pays")
    date_dispo           = fields.Datetime("Date-heure de disponibilité", required=True)
    date_liv_souhaitee   = fields.Datetime("Date-heure de livraison souhaitée", required=True)
    infos_diverses       = fields.Text("Informations diverses ")
    state                = fields.Selection([('en_cours', 'En cours'),('traite', 'Traité')], "Etat")


    _defaults = {
        'type_demande': 'transport',
        'date_demande': lambda *a: fields.datetime.now(),
        'demandeur_id': lambda obj, cr, uid, context: uid,
        'state'       : 'en_cours',
    }


    @api.model
    def create(self, vals):
        data_obj = self.env['ir.model.data']
        sequence_ids = data_obj.search([('name','=','is_demande_transport_seq')])
        if sequence_ids:
            sequence_id = data_obj.browse(sequence_ids[0].id).res_id
            vals['name'] = self.env['ir.sequence'].get_id(sequence_id, 'id')
        obj = super(is_demande_transport, self).create(vals)
        return obj


    @api.multi
    def vers_traite_action(self):
        for obj in self:
            obj.state="traite"


    @api.multi
    def vers_en_cours_action(self):
        for obj in self:
            obj.sudo().state="en_cours"






