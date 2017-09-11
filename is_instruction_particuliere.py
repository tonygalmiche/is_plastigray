# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import Warning
import datetime


class is_instruction_particuliere(models.Model):
    _name = 'is.instruction.particuliere'
    _order = 'name desc'

    name          = fields.Char("N°", required=False, readonly=True, select=True)
    createur_id   = fields.Many2one('res.users', 'Créateur', readonly=True)
    date_creation = fields.Date('Date de création', readonly=True)
    mold_ids      = fields.Many2many('is.mold'        ,'is_instruction_particuliere_mold_rel'    ,'ip_id','mold_id'    , string="Moules")
    dossierf_ids  = fields.Many2many('is.dossierf'    ,'is_instruction_particuliere_dossierf_rel','ip_id','dossierf_id', string="Dossiers F")
    product_ids   = fields.Many2many('product.product','is_instruction_particuliere_product_rel' ,'ip_id','product_id' , string="Articles")
    date_validite = fields.Date("Date de validité", required=True)
    commentaire   = fields.Text("Commentaire")
    contenu       = fields.Binary("Image du contenu")

    _defaults = {
        'createur_id': lambda obj, cr, uid, context: uid,
        'date_creation': datetime.date.today(),
    }


    @api.model
    def create(self, vals):
        print 'ok'

        data_obj = self.env['ir.model.data']
        sequence_ids = data_obj.search([('name','=','is_instruction_particuliere_seq')])
        print 'sequence_ids=',sequence_ids
        if len(sequence_ids)>0:
            sequence_id = sequence_ids[0].res_id
            vals['name'] = self.env['ir.sequence'].get_id(sequence_id, 'id')
        print vals
        res = super(is_instruction_particuliere, self).create(vals)
        return res




