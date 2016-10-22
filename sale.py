# -*- coding: utf-8 -*-

import time
import datetime
from openerp import models,fields,api
from openerp.tools.translate import _
from math import *
from openerp.exceptions import Warning


class sale_order(models.Model):
    _inherit = "sale.order"

    @api.model
    def _get_default_location(self):
        company_id = self.env.user.company_id.id
        warehouse_obj = self.env['stock.warehouse']
        warehouse_id = warehouse_obj.search([('company_id','=',company_id)])
        location = warehouse_id.out_type_id and  warehouse_id.out_type_id.default_location_src_id
        return location and location or False


    is_type_commande       = fields.Selection([('standard', 'Ferme'),('ouverte', 'Ouverte'),('cadence', 'Cadencé'),('ls', 'Liste à servir')], "Type de commande")
    is_article_commande_id = fields.Many2one('product.product', 'Article de la commande', help="Article pour les commandes ouvertes")
    is_ref_client          = fields.Char("Référence client", store=True, compute='_ref_client')
    is_source_location_id  = fields.Many2one('stock.location', 'Source Location', default=_get_default_location) 
    is_transporteur_id     = fields.Many2one('res.partner', 'Transporteur')

    _defaults = {
        'is_type_commande': 'standard',
    }


    def onchange_partner_id(self, cr, uid, ids, partner_id, context=None):
        res = super(sale_order, self).onchange_partner_id(cr, uid, ids, partner_id, context=context)
        if partner_id:
            partner = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
            if partner.is_adr_facturation:
                res['value'].update({'partner_invoice_id': partner.is_adr_facturation.id })
            if partner.is_source_location_id:
                res['value'].update({'is_source_location_id': partner.is_source_location_id.id })
            if partner.is_transporteur_id:
                res['value'].update({'is_transporteur_id': partner.is_transporteur_id.id })
        return res


    @api.depends('is_article_commande_id', 'is_article_commande_id.is_ref_client', 'is_article_commande_id.product_tmpl_id.is_ref_client')
    def _ref_client(self):
        for order in self:
            if order.is_article_commande_id:
                order.is_ref_client = order.is_article_commande_id.is_ref_client


    def onchange_order_line(self, cr, uid, ids, type_commande, order_line, context=None):
        value = {}
        if len(order_line)>1:
            value.update({'is_type_commande_ro': True})
        else:
            value.update({'is_type_commande_ro': False})
        value.update({'note': str(len(order_line))})
        return {'value': value}


    @api.multi
    def action_acceder_client(self):
        dummy, view_id = self.env['ir.model.data'].get_object_reference('base', 'view_partner_form')
        for obj in self:
            return {
                'name': "Client",
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'res.partner',
                'type': 'ir.actions.act_window',
                'res_id': obj.partner_id.id,
                'domain': '[]',
            }


    @api.multi
    def _verif_tarif(self,vals):
        if 'is_type_commande' in vals and 'is_article_commande_id' in vals and 'pricelist_id' in vals :
            if vals['is_type_commande']=='ouverte':
                product_id=vals['is_article_commande_id']
                product   = self.env['product.product'].browse([product_id])
                partner   = self.env['res.partner'].browse(vals['partner_invoice_id'])
                pricelist_id=vals['pricelist_id']
                context={}
                if pricelist_id:
                    pricelist=self.env['product.pricelist'].browse(pricelist_id)

                    qty = self.env['product.template'].get_lot_livraison(product.product_tmpl_id, partner)
                    date = time.strftime('%Y-%m-%d')
                    ctx = dict(
                        context,
                        uom=product.uom_id.id,
                        date=date,
                    )
                    price = self.pool.get('product.pricelist').price_get(self._cr, self._uid, pricelist_id,
                            product_id, qty, vals['partner_id'], ctx)[pricelist_id]
                    if not price:
                        raise Warning("Il n'existe pas de tarif (liste de prix) pour l'article '"+str(product.is_code)+"' / qt="+str(qty)+ " / date="+str(date))


    @api.multi
    def _verif_existe(self,vals):
        if 'is_article_commande_id' in vals:
            r=self.env['sale.order'].search([
                ['partner_id'            , '=', vals['partner_id']],
                ['is_article_commande_id', '=', vals['is_article_commande_id']],
                ['is_type_commande'      , '=', vals['is_type_commande']],
                ['state'                 , '=', 'draft'],
                ['is_type_commande'      , '=', 'ouverte'],
            ])
            if len(r)>1 :
                raise Warning(u"Il exite déjà une commande ouverte pour cet article et ce client")


    @api.multi
    def _client_order_ref(self, obj):
        if obj.is_type_commande!='ls':
            for line in obj.order_line:
                line.is_client_order_ref=obj.client_order_ref


    @api.model
    def create(self, vals):
        self._verif_tarif(vals)
        self._verif_existe(vals)
        obj = super(sale_order, self).create(vals)
        self._client_order_ref(obj)
        return obj


    @api.multi
    def write(self,vals):
        res=super(sale_order, self).write(vals)
        for obj in self:
            vals2={
                'is_type_commande'       : obj.is_type_commande,
                'is_article_commande_id' : obj.is_article_commande_id.id,
                'pricelist_id'           : obj.pricelist_id.id,
                'partner_id'             : obj.partner_id.id,
                'partner_invoice_id'     : obj.partner_invoice_id.id,
            }
            self._verif_tarif(vals2)
            self._verif_existe(vals2)
            self._client_order_ref(obj)
        return res





class sale_order_line(models.Model):
    _inherit = "sale.order.line"
    _order = 'order_id desc, is_date_livraison, sequence, id'

    is_justification      = fields.Char("Justification", help="Ce champ est obligatoire si l'article n'est pas renseigné ou le prix à 0")
    is_date_livraison     = fields.Date("Date de livraison")
    is_date_expedition    = fields.Date("Date d'expédition", store=True, compute='_date_expedition')
    is_type_commande      = fields.Selection([('ferme', 'Ferme'),('previsionnel', 'Prév.')], "Type")
    is_client_order_ref   = fields.Char("Commande client")

#    _defaults = {
#        'is_type_commande': 'previsionnel',
#    }

#    def _is_type_commande():
#        now = datetime.date.today()         # Date du jour
#        return now.strftime('%Y-%m-%d')     # Formatage

#    _defaults = {
#        'is_type_commande':  _is_type_commande(),
#    }





    @api.depends('is_date_livraison')
    def _date_expedition(self):
        for order in self:
            if order.is_date_livraison:
                cr      = self._cr
                uid     = self._uid
                context = self._context
                res_partner = self.env['res.partner']
                # jours de fermeture de la société
                jours_fermes = res_partner.num_closing_days(order.order_id.company_id.partner_id)
                # Jours de congé de la société
                leave_dates = res_partner.get_leave_dates(order.order_id.company_id.partner_id)
                delai_transport = order.order_id.partner_id.is_delai_transport
                if delai_transport:
                    date = datetime.datetime.strptime(order.is_date_livraison, '%Y-%m-%d') - datetime.timedelta(days=delai_transport)
                    date = date.strftime('%Y-%m-%d')
                    num_day = time.strftime('%w', time.strptime(date, '%Y-%m-%d'))
                    date_expedition = res_partner.get_working_day(date, num_day, jours_fermes, leave_dates)
                    order.is_date_expedition=date_expedition
                else:
                    order.is_date_expedition = order.is_date_livraison 


    @api.multi
    def action_acceder_commande(self):
        dummy, view_id = self.env['ir.model.data'].get_object_reference('sale', 'view_order_form')
        for obj in self:
            return {
                'name': "Commande",
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'sale.order',
                'type': 'ir.actions.act_window',
                'res_id': obj.order_id.id,
                'domain': '[]',
            }

    @api.multi
    def action_acceder_client(self):
        dummy, view_id = self.env['ir.model.data'].get_object_reference('base', 'view_partner_form')
        for obj in self:
            return {
                'name': "Client",
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'res.partner',
                'type': 'ir.actions.act_window',
                'res_id': obj.order_id.partner_id.id,
                'domain': '[]',
            }


    @api.multi
    def action_acceder_article(self):
        dummy, view_id = self.env['ir.model.data'].get_object_reference('is_pg_product', 'is_product_template_only_form_view')
        for obj in self:
            return {
                'name': "Article",
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'product.template',
                'type': 'ir.actions.act_window',
                'res_id': obj.product_id.product_tmpl_id.id,
                'domain': '[]',
            }



    @api.multi
    def check_date_livraison(self, date_livraison,  partner_id, context=None):
        res_partner = self.env['res.partner']
        if partner_id:
            partner = self.env['res.partner'].browse(partner_id)
            # jours de fermeture de la société
            jours_fermes = res_partner.num_closing_days(partner)
            # Jours de congé de la société
            leave_dates = res_partner.get_leave_dates(partner)
            # num de jour dans la semaine de la date de livraison
            num_day = time.strftime('%w', time.strptime(date_livraison, '%Y-%m-%d'))
            
            if int(num_day) in jours_fermes or date_livraison in leave_dates:
                return False
        return True


    @api.multi
    def onchange_date_livraison(self, date_livraison, product_id, qty, uom, partner_id, pricelist, company_id, order_id=False):
        context=self._context
        v = {}
        warning = {}
        if order_id:
            order = self.env['sale.order'].browse(order_id)
            if order:
                partner_id=order.partner_id.id
                company_id=order.company_id.id
        if partner_id and date_livraison:
            partner     = self.env['res.partner'].browse(partner_id)
            company     = self.env['res.company'].browse(company_id)
            res_partner = self.env['res.partner']
            # jours de fermeture de la société
            jours_fermes = res_partner.num_closing_days(company.partner_id)
            # Jours de congé de la société
            leave_dates = res_partner.get_leave_dates(company.partner_id)
            delai_transport = partner.is_delai_transport
            date_expedition = date_livraison
            if delai_transport:
                i = 0
                while i < delai_transport:
                    date = datetime.datetime.strptime(date_expedition, '%Y-%m-%d') - datetime.timedelta(days=1)
                    date = date.strftime('%Y-%m-%d')
                    num_day = time.strftime('%w', time.strptime(date, '%Y-%m-%d'))
                    date_expedition = res_partner.get_day_except_weekend(date, num_day)         
                    i += 1
                
                date_expedition = res_partner.get_working_day(date, num_day, jours_fermes, leave_dates)
                
            v['is_date_expedition'] = date_expedition 


            #Type de commande = previsionnel pour les commandes ouvertes
            is_type_commande='ferme'
            if 'is_type_commande' in context:
                if context['is_type_commande']=='ouverte':
                    is_type_commande='previsionnel'
            v['is_type_commande']   = is_type_commande
        
            check_date = self.check_date_livraison(date_livraison, partner_id, context=context)
            if not check_date:
                warning = {
                            'title': _('Warning!'),
                            'message' : 'La date de livraison tombe pendant la fermeture du client.'
                }


            #** Recherche prix dans liste de prix pour la date et qt ***********
            if pricelist:
                ctx = dict(
                    context,
                    uom=uom,
                    date=date_livraison,
                )
                price = self.pool.get('product.pricelist').price_get(self._cr, self._uid, [pricelist],
                        product_id, qty or 1.0, partner_id, ctx)[pricelist]
                v['price_unit'] = price
            #*******************************************************************

        
        return {'value': v,
                'warning': warning}



    # Arrondir au lot et au multiple du lot dans la saisie des commandes
    #def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
    @api.multi
    def product_id_change(self, pricelist_id, product_id, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, context=None):
        qty=self.env['product.template'].get_arrondi_lot_livraison(product_id, partner_id, qty)
        vals = super(sale_order_line, self).product_id_change(pricelist_id, product_id, qty,
                                                                     uom, qty_uos, uos, name, partner_id,
                                                                     lang, update_tax, date_order, packaging,
                                                                     fiscal_position, flag, context=context)
        vals['value']['product_uom_qty'] = qty
        # Le prix est forcé à 0, car il sera calculé avec la date d'expédition
        vals['value']['price_unit'] = 0    

        return vals




