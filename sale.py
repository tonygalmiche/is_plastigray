# -*- coding: utf-8 -*-

import time
import datetime
from openerp import models,fields,api
from openerp.tools.translate import _
from math import *
from openerp.exceptions import Warning


class sale_order(models.Model):
    _inherit = "sale.order"

    is_type_commande       = fields.Selection([('standard', 'Ferme'),('ouverte', 'Ouverte'),('cadence', 'Cadencé')], "Type de commande")
    is_article_commande_id = fields.Many2one('product.product', 'Article de la commande', help="Article pour les commandes ouvertes")
    is_ref_client          = fields.Char("Référence client", store=True, compute='_ref_client')

    _defaults = {
        'is_type_commande': 'standard',
    }


    def onchange_partner_id(self, cr, uid, ids, part, context=None):
        res = super(sale_order, self).onchange_partner_id(cr, uid, ids, part, context=context)
        if part:
            partner = self.pool.get('res.partner').browse(cr, uid, part, context=context)
#            if partner.is_adr_livraison:
#                res['value'].update({'partner_shipping_id': partner.is_adr_livraison.id })
            if partner.is_adr_facturation:
                res['value'].update({'partner_invoice_id': partner.is_adr_facturation.id })
#            if partner.is_adr_groupe:
#                res['value'].update({'partner_group_id': partner.is_adr_groupe.id })
#            else:
#                res['value'].update({'partner_group_id': res['value']['partner_invoice_id'] })

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
    def write(self,vals):
        res=super(sale_order, self).write(vals)
        for obj in self:
            r=self.env['sale.order'].search([
                ['partner_id', '=', obj.partner_id.id],
                ['is_article_commande_id', '=', obj.is_article_commande_id.id],
                ['is_type_commande', '=', 'ouverte'],
            ])
            if len(r)>1 :
                raise Warning(u"Il exite déjà une commande ouverte pour cet article et ce client")

            for line in obj.order_line:
                if not line.is_client_order_ref:
                    line.is_client_order_ref=obj.client_order_ref
        return res





class sale_order_line(models.Model):
    _inherit = "sale.order.line"
    _order = 'order_id desc, is_date_livraison, sequence, id'

    is_justification      = fields.Char("Justification", help="Ce champ est obligatoire si l'article n'est pas renseigné ou le prix à 0")
    is_date_livraison     = fields.Date("Date de livraison")
    is_date_expedition    = fields.Date("Date d'expédition", store=True, compute='_date_expedition')
    is_type_commande      = fields.Selection([('ferme', 'Ferme'),('previsionnel', 'Prév.')], "Type")
    is_client_order_ref   = fields.Char("Commande client")

    _defaults = {
        'is_type_commande': 'previsionnel',
    }

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
                is_api = self.pool.get('is.api')
                # jours de fermeture de la société
                jours_fermes = is_api.num_closing_days(cr, uid, order.order_id.company_id.partner_id, context=context)
                # Jours de congé de la société
                leave_dates = is_api.get_leave_dates(cr, uid, order.order_id.company_id.partner_id, context=context)
                delai_transport = order.order_id.partner_id.is_delai_transport
                if delai_transport:
                    date = datetime.datetime.strptime(order.is_date_livraison, '%Y-%m-%d') - datetime.timedelta(days=delai_transport)
                    date = date.strftime('%Y-%m-%d')
                    num_day = time.strftime('%w', time.strptime(date, '%Y-%m-%d'))
                    date_expedition = is_api.get_working_day(cr, uid, date, num_day, jours_fermes, leave_dates, context=context)         
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
            print "product_tmpl_id=",obj.product_id.product_tmpl_id.id,
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




    def check_date_livraison(self, cr, uid, ids, date_livraison,  partner_id, context=None):
        is_api = self.pool.get('is.api')
        if partner_id:
            partner = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
            # jours de fermeture de la société
            jours_fermes = is_api.num_closing_days(cr, uid, partner, context=context)
            # Jours de congé de la société
            leave_dates = is_api.get_leave_dates(cr, uid, partner, context=context)
            # num de jour dans la semaine de la date de livraison
            num_day = time.strftime('%w', time.strptime(date_livraison, '%Y-%m-%d'))
            
            if int(num_day) in jours_fermes or date_livraison in leave_dates:
                return False
        return True


    def onchange_date_livraison(self, cr, uid, ids, date_livraison, partner_id, company_id, order_id=False, context=None):
        v = {}
        warning = {}
        if order_id:
            order = self.pool.get('sale.order').browse(cr, uid, order_id, context=context)
            if order:
                partner_id=order.partner_id.id
                company_id=order.company_id.id
        if partner_id and date_livraison:
            partner = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
            company = self.pool.get('res.company').browse(cr, uid, company_id, context=context)
            is_api = self.pool.get('is.api')
            # jours de fermeture de la société
            jours_fermes = is_api.num_closing_days(cr, uid, company.partner_id, context=context)
            # Jours de congé de la société
            leave_dates = is_api.get_leave_dates(cr, uid, company.partner_id, context=context)
            delai_transport = partner.is_delai_transport
            date_expedition = date_livraison
            if delai_transport:
                i = 0
                while i < delai_transport:
                    date = datetime.datetime.strptime(date_expedition, '%Y-%m-%d') - datetime.timedelta(days=1)
                    date = date.strftime('%Y-%m-%d')
                    num_day = time.strftime('%w', time.strptime(date, '%Y-%m-%d'))
                    date_expedition = is_api.get_day_except_weekend(cr, uid, date, num_day, context=context)         
                    i += 1
                
                date_expedition = is_api.get_working_day(cr, uid, date, num_day, jours_fermes, leave_dates, context=context)
                
            v['is_date_expedition'] = date_expedition 
        
            check_date = self.check_date_livraison(cr, uid, ids, date_livraison, partner_id, context=context)
            if not check_date:
                warning = {
                            'title': _('Warning!'),
                            'message' : 'La date de livraison tombe pendant la fermeture du client.'
                }
        
        return {'value': v,
                'warning': warning}



    # Arrondir au lot et au multiple du lot dans la saisie des commandes
    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, context=None):

        product_obj = self.pool.get('product.product').browse(cr, uid, product, context=context)
        lot      = product_obj.lot_livraison
        multiple = product_obj.multiple_livraison
        if multiple==0:
            multiple=1
        if qty<lot:
            qty=lot
        else:
            delta=qty-lot
            qty=lot+multiple*ceil(delta/multiple)

        vals = super(sale_order_line, self).product_id_change(cr, uid, ids, pricelist, product, qty,
                                                                     uom, qty_uos, uos, name, partner_id,
                                                                     lang, update_tax, date_order, packaging,
                                                                     fiscal_position, flag, context=context)

        vals['value']['product_uom_qty']=qty

        return vals




