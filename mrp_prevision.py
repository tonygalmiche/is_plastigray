# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import time
from openerp import pooler
from openerp import models,fields,api
from openerp.tools.translate import _
from math import *
from openerp import workflow

class mrp_prevision(models.Model):
    _name = 'mrp.prevision'
    _description = 'Prevision des fabrication dans le secteur automobile'

    num_od = fields.Integer("Numéro", readonly=True)
    name=  fields.Char('OD', size=128, required=True)
    parent_id = fields.Many2one('mrp.prevision', "FS d'origine", ondelete='cascade')
    type = fields.Selection([('fs', u"FS"),
                              ('ft', u"FT"),
                              ('sa', "SA")], "Type", required=True)
    product_id = fields.Many2one('product.product', 'Article', required=True)
    start_date = fields.Date('Date de début')
    end_date = fields.Date('Date de fin', required=True)
    quantity = fields.Float('Quantité')
    quantity_origine = fields.Float("Quantité d'origine")
    note = fields.Text('Information')
    niveau = fields.Integer('Niveau', readonly=True, required=True)
    stock_th = fields.Float('Stock Théorique', readonly=True)
    company_id = fields.Many2one('res.company', 'Société', required=True, change_default=True, readonly=True)
    active = fields.Boolean('Active')
    ft_ids = fields.One2many('mrp.prevision', 'parent_id', u'Composants')
    state = fields.Selection([('creation', u'Création'),('valide', u'Validé')], u"État", readonly=True, select=True)


    _defaults = {
        'active': True,
        'niveau': 0,
        'name': lambda obj, cr, uid, context: '/',
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'mrp.prevision', context=c),
        'state': 'creation'
    }



    @api.multi
    def button_mrp_create(self):
        for obj in self:

            if obj.type=='fs':

                mrp_production_obj = self.env['mrp.production']
                bom_obj = self.env['mrp.bom']


                bom_id = bom_obj._bom_find(product_id=obj.product_id.id, properties=[])
                routing_id = False
                if bom_id:
                    bom_point = bom_obj.browse(bom_id)
                    routing_id = bom_point.routing_id.id or False
                mrp_id = mrp_production_obj.create({
                        'product_id': obj.product_id.id,
                        'product_uom': obj.product_id.uom_id.id,
                        'product_qty': obj.quantity,
                        'date_planned': obj.start_date,
                        'mrp_product_suggestion_id': obj.id,
                        'bom_id': bom_id,
                        'routing_id': routing_id,
                        'origin': obj.name,
                })
                print "Convertion ",obj.name, mrp_id
                workflow.trg_validate(self._uid, 'mrp.production', mrp_id.id, 'button_confirm', self._cr)


    @api.multi
    def _start_date(self, product_id, quantity, end_date):
        start_date=end_date
        product_obj = self.pool.get('product.product')
        for product in product_obj.browse(self._cr, self._uid, [product_id], context=self._context):
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            days=product.produce_delay+int(quantity*product.temps_realisation/(3600*24))
            start_date= end_date - timedelta(days=days)
            start_date = start_date.strftime('%Y-%m-%d')
        return start_date


    @api.multi
    def _quantity2lot(self, product, quantity):
        if quantity<product.lot_mini:
            quantity=product.lot_mini
        delta=quantity-product.lot_mini
        if delta>0:
            if product.multiple!=0:
                x=ceil(delta/product.multiple)
                quantity=product.lot_mini+x*product.multiple
        return quantity


    @api.model
    def create(self, vals):
        type=vals.get('type', None)
        quantity = vals.get('quantity', 0)
        if type=='fs' or type=='sa':
            product_id = vals.get('product_id', False)
            if product_id:
                product_obj = self.pool.get('product.product')
                for product in product_obj.browse(self._cr, self._uid, [product_id], context=self._context):
                    quantity=self._quantity2lot(product, quantity)
                    vals["quantity"]=quantity
        vals["quantity_origine"]=quantity
        end_date   = vals.get('end_date', None)
        product_id = vals.get('product_id', None)
        type       = vals.get('type', None)
        if quantity and end_date and product_id and type=="fs":
            start_date=self._start_date(product_id, quantity, end_date)
            vals["start_date"]=start_date

        data_obj = self.pool.get('ir.model.data')

        sequence_ids = data_obj.search(self._cr, self._uid, [('name','=','seq_mrp_prevision_'+str(type))], context=self._context)
        if sequence_ids:
            sequence_id = data_obj.browse(self._cr, self._uid, sequence_ids[0], self._context).res_id
            vals['name'] = self.pool.get('ir.sequence').get_id(self._cr, self._uid, sequence_id, 'id', context=self._context)
        obj = super(mrp_prevision, self).create(vals)

        #** Recherche des composants de la nomenclature pour les fs ************
        if obj:
            id=obj.id
            for row in self.browse([id]):
                if row.type=='fs':
                    bom_obj = self.pool.get('mrp.bom')
                    template_id = row.product_id.product_tmpl_id.id
                    if template_id:
                        bom_ids = bom_obj.search(self._cr, self._uid, [('product_tmpl_id','=',template_id),], context=self._context)
                        if bom_ids:
                            for line in bom_obj.browse(self._cr, self._uid, bom_ids[0], context=self._context).bom_line_ids:
                                vals={
                                    'parent_id': row.id,
                                    'type': 'ft',
                                    'product_id': line.product_id.id,
                                    'start_date': row.start_date,
                                    'end_date': row.start_date,
                                    'quantity': row.quantity*line.product_qty,
                                    'quantity_origine': row.quantity*line.product_qty,
                                    'state': 'valide',
                                }
                                self.create(vals)
        return obj


    @api.multi
    def write(self,vals):
        cr      = self._cr
        uid     = self._uid
        context = self._context
        ids = [self.id]

        quantity = vals.get('quantity', None)
        end_date = vals.get('end_date', None)
        if quantity or end_date:
            for fs in self.browse(ids):
                if fs.type=='fs':
                    if not quantity:
                        quantity=fs.quantity
                    quantity=self._quantity2lot(fs.product_id, quantity)
                    vals["quantity"]=quantity
                    if not end_date:
                        end_date=fs.end_date
                    start_date=self._start_date(fs.product_id.id, quantity, end_date)
                    vals["start_date"]=start_date
        state = vals.get('state', False)
        if not state:
            vals['state']='valide'
        res = super(mrp_prevision, self).write(vals)
        for fs in self.browse(ids):
            obj = self.pool.get('mrp.prevision')
            coef=0
            if fs.quantity!=0:
                coef=fs.quantity_origine/fs.quantity
            ft_ids = obj.search(self._cr, self._uid, [('type','=','ft'),('parent_id','=',fs.id),],context=self._context)
            if ft_ids:
                for row in obj.browse(self._cr, self._uid, ft_ids, context=self._context):
                    quantity=fs.quantity
                    if coef!=0:
                        quantity=row.quantity_origine/coef
                    vals={
                        'quantity'  : quantity,
                        'start_date': fs.start_date,
                        'end_date'  : fs.start_date,
                    }
                    obj.write(cr, uid, row.id, vals, context=context)
        return res





