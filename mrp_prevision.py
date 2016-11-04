# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import time
from openerp import pooler
from openerp import models,fields,api
from openerp.tools.translate import _
from math import *
from openerp import workflow
from openerp.exceptions import Warning


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
    def convertir_sa(self):
        ids=[]
        for obj in self:
            if obj.type=='sa':
                if len(obj.product_id.seller_ids)>0:
                    ids.append(obj)
                else:
                    obj.note="Aucun fournisseur indiqué dans la fiche article => Convertion en commande impossible"

        order_obj      = self.env['purchase.order']
        order_line_obj = self.env['purchase.order.line']

        for obj in ids:
            partner=obj.product_id.seller_ids[0].name
            orders = order_obj.search([('partner_id','=',partner.id),('state','=','draft')])
            order=False
            if len(orders)>0:
                order=orders[0]
            else:
                if partner.property_product_pricelist_purchase:
                    vals={
                        'partner_id'   : partner.id,
                        'location_id'  : partner.is_source_location_id.id,
                        'pricelist_id' : partner.property_product_pricelist_purchase.id,
                    }
                    order=order_obj.create(vals)
            if order:
                res=order_line_obj.onchange_product_id(order.pricelist_id.id, \
                    obj.product_id.id, obj.quantity, obj.product_id.uom_id.id, \
                    partner.id, False, False, obj.end_date, False, False, 'draft')
                vals=res['value']
                vals['order_id']=order.id
                vals['product_id']=obj.product_id.id
                order_line=order_line_obj.create(vals)
                obj.unlink()




        
            




    @api.multi
    def convertir_fs(self):
        ids=[]
        for obj in self:
            if obj.type=='fs':
                if len(obj.ft_ids)>0:
                    ids.append(obj)
                else:
                    obj.note="Aucune nomenclature pour cet article => Convertion en OF impossible"

        for obj in ids:
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
                name=obj.name
                try:
                    workflow.trg_validate(self._uid, 'mrp.production', mrp_id.id, 'button_confirm', self._cr)
                    #break
                except Exception as inst:
                    msg="Impossible de convertir la "+name+'\n('+str(inst)+')'
                    #obj.note=msg
                    raise Warning(msg)









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




    @api.model
    def create(self, vals):

        #** Quantité arrondie au lot à la création uniquement ******************
        type       = vals.get('type'    , None)
        quantity   = vals.get('quantity', None)
        product_id = vals.get('product_id', None)
        if (type=='sa' or type=='fs') and quantity:
            product=self.env['product.product'].browse(product_id)
            quantity=self.get_quantity2lot(product, quantity)
            vals["quantity"]         = quantity
            vals["quantity_origine"] = quantity
        #***********************************************************************

        end_date   = vals.get('end_date', None)
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

        for obj in self:
            #** Date de début des SA en tenant compte du délai de livraison ****
            end_date = vals.get('end_date', None)
            if obj.type=='sa' and end_date:
                vals["start_date"]=self.get_start_date_sa(obj.product_id, end_date)
            #*******************************************************************

#            #** Quantité arrondie au lot ***************************************
#            quantity = vals.get('quantity', None)
#            if obj.type=='sa' and quantity:
#                vals["quantity"]=self.get_quantity2lot(obj.product_id, quantity)
#            #*******************************************************************




        if end_date:
            for fs in self.browse(ids):
                if fs.type=='fs':
                    #if not quantity:
                    #    quantity=fs.quantity
                    #quantity=self._quantity2lot(fs.product_id, quantity)
                    #vals["quantity"]=quantity
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



    @api.multi
    def get_quantity2lot(self, product, quantity):
        if quantity<product.lot_mini:
            quantity=product.lot_mini
        delta=quantity-product.lot_mini
        if delta>0:
            if product.multiple!=0:
                x=ceil(delta/product.multiple)
                quantity=product.lot_mini+x*product.multiple
        return quantity


    @api.multi
    def get_start_date_sa(self,product, end_date):
        """
        Date de début des SA en tenant compte du délai de livraison
        """
        start_date=end_date
        if len(product.seller_ids)>0:
            partner_obj=self.env['res.partner']
            delay=product.seller_ids[0].delay
            partner_id=product.seller_ids[0].name
            new_date = datetime.strptime(end_date, '%Y-%m-%d')
            new_date = new_date - timedelta(days=delay)
            new_date = new_date.strftime('%Y-%m-%d')
            new_date = partner_obj.get_date_dispo(product.seller_ids[0].name, new_date)
            start_date=new_date
        return start_date



