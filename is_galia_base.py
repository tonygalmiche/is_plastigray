# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _
import datetime
import pytz


class is_galia_base(models.Model):
    _name='is.galia.base'
    _order='num_eti desc'
    _rec_name='num_eti'

    num_eti       = fields.Integer(u"N°Étiquette", select=True)
    soc           = fields.Integer(u"Société"    , select=True)
    type_eti      = fields.Char(u"Type étiquette", select=True)
    num_of        = fields.Char(u"N°OF"          , select=True)
    num_carton    = fields.Integer(u"N°Carton"   , select=True)
    qt_pieces     = fields.Integer(u"Qt Pièces")
    date_creation = fields.Datetime(u"Date de création")
    login         = fields.Char(u"Login")


class is_galia_base_um(models.Model):
    _name='is.galia.base.um'
    _order='name desc'
    _sql_constraints = [('name_uniq','UNIQUE(name)', u'Cette étiquette UM existe déjà')]

    @api.depends('uc_ids')
    def _compute(self):
        for obj in self:
            qt_pieces  = 0
            product_id = False
            for line in obj.uc_ids:
                qt_pieces += line.qt_pieces
                product_id = line.product_id
            obj.product_id = product_id
            obj.qt_pieces  = qt_pieces

    name             = fields.Char(u"N°Étiquette UM", readonly=True, select=True)
    liste_servir_id  = fields.Many2one('is.liste.servir', u'Liste à servir')
    bon_transfert_id = fields.Many2one('is.bon.transfert', u'Bon de transfert')
    uc_ids           = fields.One2many('is.galia.base.uc'  , 'um_id', u"UCs")
    product_id       = fields.Many2one('product.product', 'Article', readonly=True, compute='_compute', store=False)
    qt_pieces        = fields.Integer(u"Qt Pièces"                 , readonly=True, compute='_compute', store=False)


    @api.model
    def create(self, vals):
        data_obj = self.env['ir.model.data']
        sequence_ids = data_obj.search([('name','=','is_galia_base_um_seq')])
        if sequence_ids:
            sequence_id = data_obj.browse(sequence_ids[0].id).res_id
            vals['name'] = self.env['ir.sequence'].get_id(sequence_id, 'id')
        res = super(is_galia_base_um, self).create(vals)
        return res


    @api.multi
    def acceder_um_action(self):
        dummy, view_id = self.env['ir.model.data'].get_object_reference('is_plastigray', 'is_galia_base_um_form_view')
        for obj in self:
            return {
                'name': "Etiquettes UM",
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'is.galia.base.um',
                'type': 'ir.actions.act_window',
                'res_id': obj.id,
                'domain': '[]',
            }





class is_galia_base_uc(models.Model):
    _name='is.galia.base.uc'
    _order='num_eti desc'
    _rec_name='num_eti'
    _sql_constraints = [('num_eti_uniq','UNIQUE(num_eti)', u'Cette étiquette existe déjà')]

    um_id         = fields.Many2one('is.galia.base.um', 'UM', required=True, ondelete='cascade')
    num_eti       = fields.Integer(u"N°Étiquette UC", required=True, select=True)
    type_eti      = fields.Char(u"Type étiquette", required=True   , select=True)
    num_carton    = fields.Integer(u"N°Carton", required=True      , select=True)
    qt_pieces     = fields.Integer(u"Qt Pièces", required=True)
    date_creation = fields.Datetime(u"Date de création", required=True)
    production_id = fields.Many2one('mrp.production', 'Ordre de fabrication')
    product_id    = fields.Many2one('product.product', 'Article', required=True)


