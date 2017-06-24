# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import time
import sys
from openerp import pooler
from openerp import models,fields,api
from openerp.tools.translate import _
from math import *
from openerp import workflow
from openerp.exceptions import Warning


class mrp_prevision(models.Model):
    _name = 'mrp.prevision'
    _description = 'Prevision des fabrication dans le secteur automobile'


    @api.one
    def _compute(self):
        uom_obj = self.env["product.uom"]
        quantity_ha = uom_obj._compute_qty(self.uom_id.id, self.quantity, self.uom_po_id.id)
        self.quantity_ha = quantity_ha

    num_od           = fields.Integer("Numéro", readonly=True)
    name             =  fields.Char('OD', size=128, required=True)
    parent_id        = fields.Many2one('mrp.prevision', "FS d'origine", ondelete='cascade')
    type             = fields.Selection([
        ('fs', u"FS"),
        ('ft', u"FT"),
        ('sa', "SA")
    ], "Type", required=True)
    product_id         = fields.Many2one('product.product', 'Article', required=True)
    is_category_id     = fields.Many2one('is.category', 'Catégorie', readonly=True)
    is_gestionnaire_id = fields.Many2one('is.gestionnaire', 'Gestionnaire', readonly=True)
    partner_id         = fields.Many2one('res.partner', 'Fournisseur', readonly=True)
    start_date         = fields.Date('Date de début')
    start_date_cq      = fields.Date('Date début contrôle qualité'   , readonly=True)
    end_date           = fields.Date('Date fin contrôle qualité', required=True)
    quantity           = fields.Float('Quantité')
    quantity_ha        = fields.Float("Quantité (UA)", compute="_compute", digits=(12, 4))
    quantity_origine   = fields.Float("Quantité d'origine")
    uom_id             = fields.Many2one('product.uom', 'Unité'        , related='product_id.uom_id'   , readonly=True)
    uom_po_id          = fields.Many2one('product.uom', "Unité d'achat", related='product_id.uom_po_id', readonly=True)
    delai_cq           = fields.Float("Délai contrôle qualité", readonly=True  , digits=(12, 2))
    tps_fab            = fields.Float("Temps de fabrication (Jour)", readonly=True, digits=(12, 1))
    delai_livraison    = fields.Integer("Délai de livraison", readonly=True)
    note               = fields.Text('Information')
    niveau             = fields.Integer('Niveau', readonly=True, required=True)
    stock_th           = fields.Float('Stock Théorique', readonly=True)
    company_id         = fields.Many2one('res.company', 'Société', required=True, change_default=True, readonly=True)
    active             = fields.Boolean('Active')
    ft_ids             = fields.One2many('mrp.prevision', 'parent_id', u'Composants')
    state              = fields.Selection([('creation', u'Création'),('valide', u'Validé')], u"État", readonly=True, select=True)






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
            if partner.property_product_pricelist_purchase:
                vals={
                    'partner_id'      : partner.id,
                    'is_livre_a_id'   : partner.is_livre_a_id.id,
                    'location_id'     : partner.is_source_location_id.id,
                    'fiscal_position' : partner.property_account_position.id,
                    'payment_term_id' : partner.property_supplier_payment_term.id,
                    'pricelist_id'    : partner.property_product_pricelist_purchase.id,
                }
                order=order_obj.create(vals)
                if order:
                    unlink=True
                    note=False
                    vals=False
                    try:
                        res=order_line_obj.onchange_product_id(
                            order.pricelist_id.id, 
                            obj.product_id.id, 
                            obj.quantity_ha, 
                            obj.uom_po_id.id, 
                            partner.id, 
                            date_order         = False, 
                            fiscal_position_id = partner.property_account_position.id, 
                            date_planned       = obj.start_date_cq, 
                            name               = False, 
                            price_unit         = False, 
                            state              = 'draft'
                        )
                        vals=res['value']
#                        vals['order_id']=order.id
#                        vals['product_id']=obj.product_id.id
#                        if 'taxes_id' in vals:
#                            vals.update({'taxes_id': [[6, False, vals['taxes_id']]]})
#                        order_line=order_line_obj.create(vals)
#                        order.wkf_bid_received() 
#                        order.wkf_confirm_order()
#                        order.action_picking_create() 
#                        order.wkf_approve_order()
                    except:
                        unlink=False
                        note='\n'.join(sys.exc_info()[1])
                    if vals==False:
                        vals={
                            'name'        : obj.product_id.name, 
                            'product_uom' : obj.uom_po_id.id, 
                            'product_qty' : obj.quantity_ha, 
                            'price_unit'  : False, 
                            'date_planned': obj.start_date_cq, 
                            'taxes_id'    : False
                        }
                    vals['order_id']=order.id
                    vals['product_id']=obj.product_id.id
                    if 'taxes_id' in vals:
                        vals.update({'taxes_id': [[6, False, vals['taxes_id']]]})
                    try:
                        order_line=order_line_obj.create(vals)
                        order.wkf_bid_received() 
                        order.wkf_confirm_order()
                        order.action_picking_create() 
                        order.wkf_approve_order()
                    except:
                        unlink=False
                        if note==False:
                            note='\n'.join(sys.exc_info()[1])
                        else:
                            note=note+'\n'+'\n'.join(sys.exc_info()[1])
                    obj.note=unicode(note)
                    if unlink:
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
                        'bom_id': bom_id,
                        'routing_id': routing_id,
                        'origin': obj.name,
                })
                name=obj.name
                unlink=True
                try:
                    #workflow.trg_validate(self._uid, 'mrp.production', mrp_id.id, 'button_confirm', self._cr)
                    mrp_id.action_confirm()
                    mrp_id.force_production()
                    mrp_id.action_in_production()
                    #break
                except Exception as inst:
                    unlink=False
                    msg="Impossible de convertir la "+name+'\n('+str(inst)+')'
                    obj.note=msg
                    #raise Warning(msg)

                if unlink:
                    obj.unlink()



    @api.multi
    def _start_date(self, product_id, quantity, end_date):

        start_date=end_date
        for obj in self:
            product_obj = self.pool.get('product.product')
            for product in product_obj.browse(self._cr, self._uid, [product_id], context=self._context):
                end_date = datetime.strptime(end_date, '%Y-%m-%d')
                #days=int(quantity*product.temps_realisation/(3600*24))
                #days=product.produce_delay+int(quantity*product.temps_realisation/(3600*24))
                tps_fab=quantity*product.temps_realisation/(3600*24)
                days=int(ceil(tps_fab))
                start_date= end_date - timedelta(days=days)
                start_date = start_date.strftime('%Y-%m-%d')
        return start_date




    @api.model
    def create(self, vals):
        partner_obj = self.env['res.partner']
        user        = self.env["res.users"].browse(self._uid)
        product_id  = vals.get('product_id', None)
        product     = self.env['product.product'].browse(product_id)
        company     = user.company_id

        vals['is_gestionnaire_id'] = product.is_gestionnaire_id.id
        vals['is_category_id']     = product.is_category_id.id

        #** Quantité arrondie au lot à la création uniquement ******************
        type       = vals.get('type'      , None)
        quantity   = vals.get('quantity'  , None)

        end_date   = vals.get('end_date'  , None)
        if (type=='sa' or type=='fs') and quantity:
            quantity=self.get_quantity2lot(product, quantity)
            vals["quantity"]         = quantity
            vals["quantity_origine"] = quantity
        #***********************************************************************


        #** Fournisseur par défaur *********************************************
        partner_id=False
        if type=='sa':
            if len(product.seller_ids)>0:
                partner_id=product.seller_ids[0].name.id
        vals["partner_id"]=partner_id
        #*******************************************************************

        if type=='sa' and end_date:
            #** Date de fin des SA pendant les jours ouvrés de l'entreprise ****
            end_date=partner_obj.get_date_dispo(company.partner_id, end_date)
            vals["end_date"]=end_date
            r=self.get_delai_cq_tps_fab_start_date(type, product_id, quantity, end_date, partner_id)
            vals.update(r)

            #** Date de début des SA en tenant compte du délai de livraison ****
            #vals["start_date"]=self.get_start_date_sa(product, end_date)
            #*******************************************************************

        if type=='fs':
            r=self.get_delai_cq_tps_fab_start_date(type, product_id, quantity, end_date, partner_id)
            vals.update(r)

            #** Date début des FS en tenant compte du temps de fabrication *****
            #start_date=self._start_date(product_id, quantity, end_date)
            #** Date début des FS pendant les jours ouvrés de l'entreprise *****
            #start_date=partner_obj.get_date_dispo(company.partner_id, start_date)
            #vals["start_date"]=start_date
            #*******************************************************************

        #** Numérotation *******************************************************
        data_obj = self.env['ir.model.data']
        sequence_ids = data_obj.search([('name','=','seq_mrp_prevision_'+str(type))])
        if sequence_ids:
            sequence_id = sequence_ids[0].res_id
            vals['name'] = self.env['ir.sequence'].get_id(sequence_id, 'id')
        obj = super(mrp_prevision, self).create(vals)
        #***********************************************************************

        #** Recherche des composants de la nomenclature pour les fs ************
        if obj:
            id=obj.id
            for row in self.browse([id]):
                if row.type=='fs':
                    #** Recherche en tenant compte des articles fantomes *******
                    bom_obj = self.env['mrp.bom']
                    bom_id = bom_obj._bom_find(row.product_id.product_tmpl_id.id, properties=None)
                    bom = bom_obj.browse(bom_id)
                    res= bom_obj._bom_explode(bom, row.product_id, row.quantity)
                    for line in res[0]:
                        vals={
                            'parent_id'       : row.id,
                            'type'            : 'ft',
                            'product_id'      : line['product_id'],
                            'start_date'      : row.start_date,
                            'start_date_cq'   : row.start_date,
                            'end_date'        : row.start_date,
                            'quantity'        : line['product_qty'],
                            'quantity_origine': line['product_qty'],
                            'state'           : 'valide',
                        }
                        self.create(vals)
                    #***********************************************************

#                    bom_obj = self.env['mrp.bom']
#                    template_id = row.product_id.product_tmpl_id.id
#                    if template_id:
#                        bom_ids = bom_obj.search([('product_tmpl_id','=',template_id),])
#                        if len(bom_ids)>0:
#                            bom=bom_ids[0]
#                            for line in bom.bom_line_ids:
#                                vals={
#                                    'parent_id': row.id,
#                                    'type': 'ft',
#                                    'product_id': line.product_id.id,
#                                    'start_date': row.start_date,
#                                    'end_date': row.start_date,
#                                    'quantity': row.quantity*line.product_qty,
#                                    'quantity_origine': row.quantity*line.product_qty,
#                                    'state': 'valide',
#                                }
#                                self.create(vals)
        #***********************************************************************
        return obj


    @api.multi
    def write(self,vals):
        partner_obj = self.env['res.partner']
        user = self.env["res.users"].browse(self._uid)
        company = user.company_id

        for obj in self:
            product_id = vals.get('product_id', obj.product_id.id)
            partner_id = vals.get('partner_id', obj.partner_id.id)
            quantity   = vals.get('quantity'  , obj.quantity)
            end_date   = vals.get('end_date'  , obj.end_date)

            if obj.type=='sa' and end_date:
                #** Date de fin des SA pendant les jours ouvrés de l'entreprise ****
                end_date=partner_obj.get_date_dispo(company.partner_id, end_date)
                vals["end_date"]=end_date
                r=self.get_delai_cq_tps_fab_start_date(obj.type, product_id, quantity, end_date, partner_id)
                vals.update(r)

                #** Date de début des SA en tenant compte du délai de livraison ****
                #vals["start_date"]=self.get_start_date_sa(obj.product_id, end_date)
                #*******************************************************************

            if obj.type=='fs':
                r=self.get_delai_cq_tps_fab_start_date(obj.type, product_id, quantity, end_date, partner_id)
                vals.update(r)
#                ##** Date début des FS en tenant compte du temps de fabrication *****
#                #start_date=self._start_date(product_id, quantity, end_date)
#                ##** Date début des FS pendant les jours ouvrés de l'entreprise *****
#                #start_date=partner_obj.get_date_dispo(company.partner_id, start_date)
#                #vals["start_date"]=start_date
#                ##*******************************************************************

        res = super(mrp_prevision, self).write(vals)

        #** Calcul quantity et date des FT *************************************
        for obj in self:
            if obj.type=='fs':
                coef=0
                if obj.quantity!=0:
                    coef=obj.quantity_origine/obj.quantity
                ft_ids = self.search([('type','=','ft'),('parent_id','=',obj.id),])
                for row in ft_ids:
                    quantity=row.quantity
                    if coef!=0:
                        quantity=row.quantity_origine/coef
                    row.quantity      = quantity
                    row.start_date    = obj.start_date
                    row.start_date_cq = obj.start_date
                    row.end_date      = obj.start_date
        #***********************************************************************
        return res


    @api.multi
    def get_delai_cq_tps_fab_start_date(self, type_od, product_id, quantity, end_date, partner_id):
        partner_obj = self.env['res.partner']
        user = self.env["res.users"].browse(self._uid)
        company = user.company_id
        vals={}
        start_date=end_date
        product_obj = self.pool.get('product.product')
        for product in product_obj.browse(self._cr, self._uid, [product_id], context=self._context):
            delai_cq = ceil(product.delai_cq)
            #TODO : Le 09/04/2017 : Ajout de 2 jours en dur au délai CQ pour les SA
            if type_od=='sa':
                delai_cq=delai_cq+2
            start_date_cq = partner_obj.get_date_debut(company.partner_id, end_date, delai_cq)
            #La date d'arrivée (= start_date_cq) doit tomber sur un jour d'ouverture du fournisseur pour fixer la date de réception par fournisseur
            if type_od=='sa' and partner_id:
                partner = self.env["res.partner"].browse(partner_id)
                start_date_cq = partner_obj.get_date_dispo(partner, start_date_cq)
            start_date = start_date_cq
            days=0
            tps_fab=0
            delai_livraison=0
            if type_od=='sa':
                if len(product.seller_ids)>0:
                    partner_obj=self.env['res.partner']
                    days=product.seller_ids[0].delay
                    delai_livraison=days
                    start_date = datetime.strptime(start_date_cq, '%Y-%m-%d')  - timedelta(days=days)
                    start_date = start_date.strftime('%Y-%m-%d')
                    start_date = partner_obj.get_date_dispo(company.partner_id, start_date)
            if type_od=='fs':
                tps_fab = round(quantity*product.temps_realisation/(3600*24),1)
                days    = ceil(tps_fab)
                start_date = partner_obj.get_date_debut(company.partner_id, start_date, days)
            vals={
                'delai_cq'        : product.delai_cq,
                'delai_livraison' : delai_livraison,
                'tps_fab'         : tps_fab,
                'start_date_cq'   : start_date_cq,
                'start_date'      : start_date,
            }
        return vals





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



