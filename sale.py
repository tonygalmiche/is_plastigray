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


    @api.depends('order_line')
    def _compute(self):
        for obj in self:
            obj.is_nb_lignes=len(obj.order_line)


    is_type_commande       = fields.Selection([
        ('standard', 'Ferme'),
        ('ouverte' , 'Ouverte'),
        ('cadence' , 'Cadencé'),
        ('ls'      , 'Liste à servir'),
        ('proforma', 'PROFORMA'),
    ], "Type de commande")
    is_article_commande_id = fields.Many2one('product.product', 'Article de la commande', help="Article pour les commandes ouvertes")
    is_ref_client          = fields.Char("Référence client", store=True, compute='_ref_client')
    is_source_location_id  = fields.Many2one('stock.location', 'Source Location', default=_get_default_location) 
    is_transporteur_id     = fields.Many2one('res.partner', 'Transporteur')
    is_liste_servir_id     = fields.Many2one('is.liste.servir', 'Liste à servir')
    is_info_client         = fields.Text("Information client complèmentaire")
    is_nb_lignes           = fields.Integer("Nb lignes", store=True, compute='_compute')
    is_date_envoi_mail     = fields.Datetime("Mail envoyé le", readonly=False)

    _defaults = {
        'is_type_commande': 'standard',
    }


    @api.multi
    def onchange_client_order_ref(self, client_order_ref,partner_id):
        warning = {}
        if client_order_ref and partner_id:
            orders = self.env['sale.order'].search([('client_order_ref','=',client_order_ref),('partner_id','=',partner_id)],limit=1)
            if orders:
                warning = {
                    'title': _('Warning!'),
                    'message' : u"La commande "+orders[0].name+u" a déjà ce même numéro de commande client !"
                }
        return {
            'value'  : {},
            'warning': warning,
        }


    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False,submenu=False):
        res = super(sale_order, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,submenu=submenu)

        #** Suppression des rapports indiqués **********************************
        indexes=[]
        for idx, print_submenu in enumerate(res.get('toolbar', {}).get('print', [])):
            if print_submenu['display_name'] in ["Devis / Commande"]:
                indexes.append(idx)
        for idx in reversed(indexes):
            res['toolbar']['print'].pop(idx)
        #***********************************************************************

        return res


    @api.multi
    def envoyer_ar_par_mail(self):
        cr , uid, context = self.env.args
        modele_mail = u"""
        <html>
            <head>
                <meta content="text/html; charset=UTF-8" http-equiv="Content-Type">
            </head>
            <body>
                <font>Bonjour, </font>
                <br><br>
                <font> Veuillez trouver ci-joint notre AR de commande.</font>
                <br><br>
                Cordialement <br><br>
                [from]<br>
            </body>
        </html>
        """
        for obj in self:
            mails=[]
            for c in obj.partner_id.child_ids:
                if c.is_type_contact.name == 'Approvisionneur':
                    mail = c.name + u' <' + c.email + u'>'
                    mails.append(mail)
            if not mails:
                raise Warning(u"Aucun mail de type 'Approvisionneur' pour ce client !")
            email_contact = ','.join(mails)
            user  = self.env['res.users'].browse(uid)
            email = user.email
            nom   = user.name
            if email==False:
                raise Warning(u"Votre mail n'est pas renseigné !")

            #** Génération du PDF **********************************************
            name=u'ar_commande-' + obj.client_order_ref + u'.pdf'
            pdf = self.env['report'].get_pdf(obj, 'is_plastigray.report_ar_commande')
            #*******************************************************************

            # ** Recherche si une pièce jointe est déja associèe ***************
            model=self._name
            attachment_obj = self.env['ir.attachment']
            attachments = attachment_obj.search([('res_model','=',model),('res_id','=',obj.id),('name','=',name)])
            # ******************************************************************

            # ** Creation ou modification de la pièce jointe *******************
            vals = {
                'name':        name,
                'datas_fname': name,
                'type':        'binary',
                'res_model':   model,
                'res_id':      obj.id,
                'datas':       pdf.encode('base64'),
            }
            attachment_id=False
            if attachments:
                for attachment in attachments:
                    attachment.write(vals)
                    attachment_id=attachment.id
            else:
                attachment = attachment_obj.create(vals)
                attachment_id=attachment.id
            #*******************************************************************

            email_cc      = nom + u' <'+email+u'>'

            email_from    = email_cc

            subject    = u'AR de commande Plastigray ' + obj.client_order_ref + ' pour ' + obj.partner_id.name
            #subject    = u'AR de commande Plastigray '+obj.client_order_ref+' pour '+obj.partner_id.name+u' (to='+email_contact+u')'

            email_to = email_contact
            #email_to = email_cc

            body_html = modele_mail.replace('[from]', user.name)
            email_vals = {
                'subject'       : subject,
                'email_to'      : email_to,
                'email_cc'      : email_cc,
                'email_from'    : email_from, 
                'body_html'     : body_html.encode('utf-8'), 
                'attachment_ids': [(6, 0, [attachment_id])] 
            }

            email_id = self.env['mail.mail'].create(email_vals)
            if email_id:
                self.env['mail.mail'].send(email_id)

            obj.message_post(u'Commande envoyée par mail à '+ email_contact)
            obj.is_date_envoi_mail=datetime.datetime.now()


    @api.multi
    def actualiser_prix_commande(self):
        for obj in self:
            for line in obj.order_line:
                res=line.onchange_date_livraison(
                    line.is_date_livraison, 
                    line.product_id.id, 
                    line.product_uom_qty, 
                    line.product_uom.id, 
                    obj.partner_id.id, 
                    obj.pricelist_id.id, 
                    obj.company_id.id, 
                    obj.id)
                price=res['value']['price_unit']
                if price:
                    line.price_unit=price


    @api.multi
    def numeroter_lignes(self):
        for obj in self:
            lines = self.env['sale.order.line'].search([('order_id','=',obj.id)],order="is_date_expedition")
            sequence=0
            for line in lines:
                sequence=sequence+1
                line.sequence=sequence





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
    def action_acceder_commande(self):
        for obj in self:
            return {
                'name': "Commande",
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'sale.order',
                'type': 'ir.actions.act_window',
                'res_id': obj.id,
                'domain': '[]',
            }



    @api.multi
    def _verif_tarif(self,vals):
        if 'is_type_commande' in vals and 'is_article_commande_id' in vals and 'pricelist_id' in vals :
            if vals['is_type_commande']=='ouverte':
                product_id=vals['is_article_commande_id']
                product   = self.env['product.product'].browse([product_id])
                partner   = self.env['res.partner'].browse(vals['partner_id'])
                pricelist_id=vals['pricelist_id']
                context={}
                if pricelist_id:
                    pricelist=self.env['product.pricelist'].browse(pricelist_id)
                    qty = self.env['product.template'].get_lot_livraison(product.product_tmpl_id, partner)
                    #date = time.strftime('%Y-%m-%d')
                    date = vals['date_order']
                    ctx = dict(
                        context,
                        uom=product.uom_id.id,
                        date=date,
                    )
                    price = self.pool.get('product.pricelist').price_get(self._cr, self._uid, pricelist_id,
                            product_id, qty, vals['partner_id'], ctx)[pricelist_id]
                    if price is False:
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


    @api.multi
    def _verif_article_livrable(self, obj):
        for line in obj.order_line:
            ok=False
            for l in line.product_id.is_client_ids:
                if l.client_id.id==obj.partner_id.id:
                    ok=True
            if ok==False:
                raise Warning(u"L'article "+line.product_id.is_code+u" n'est pas livrable à ce client (cf fiche article) !")





    @api.model
    def create(self, vals):
        self._verif_tarif(vals)
        obj = super(sale_order, self).create(vals)
        self._verif_existe(vals)
        self._client_order_ref(obj)
        self._verif_article_livrable(obj)
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
                'date_order'             : obj.date_order,
            }
            self._verif_tarif(vals2)
            self._verif_existe(vals2)
            self._client_order_ref(obj)
            self._verif_article_livrable(obj)
        return res





class sale_order_line(models.Model):
    _inherit = "sale.order.line"
    _order = 'order_id desc, sequence, is_date_livraison, id'


    #TODO : J'ai du surcharger ce champ pour ajouter un index (select=true)
    product_id            = fields.Many2one('product.product', 'Product', domain=[('sale_ok', '=', True)], change_default=True, readonly=True, states={'draft': [('readonly', False)]}, ondelete='restrict',select=True)

    is_justification      = fields.Char("Justif.", help="Ce champ est obligatoire si l'article n'est pas renseigné ou le prix à 0")
    is_date_livraison     = fields.Date("Date de liv.",select=True)
    is_date_expedition    = fields.Date("Date d'expé.", store=True, compute='_date_expedition',select=True)
    is_type_commande      = fields.Selection([('ferme', 'Ferme'),('previsionnel', 'Prév.')], "Type",select=True)
    is_client_order_ref   = fields.Char("Commande client")
    is_ref_client         = fields.Char('Réf. client', related='product_id.is_ref_client', readonly=True)
    is_date_confirmation  = fields.Date("Date de confirmation")
    is_comment_confirm    = fields.Char("Commentaire de confirmation")
    is_ref_plan           = fields.Char("Réf. plan", related='product_id.is_ref_plan', readonly=True)
    is_ind_plan           = fields.Char("Indice plan", related='product_id.is_ind_plan', readonly=True)



    # Le 22/06/2020 à 12:02, Caroline CHEVALLIER a écrit :
    # Date de livraison - délai de transport = date d'expédition.
    # Il faut ensuite comparer la date d'expédition au calendrier usine. 
    # Si la la date d'expédition se situe un jour où l'entreprise est fermée, il faut ramener la date d'expédition au 1er jour ouvré.

    # J'ai aussi une autre demande qui concerne le calendrier usine : nous avons besoin de 2 calendriers usine : un calendrier pour la production 
    # et qui sert au calcul de besoin et un calendrier pour les expéditions qui sert au calcul de la date d'expédition. 
    # La plupart du temps, ces 2 calendriers sont identiques mais en période estivale, ces calendriers sont différents 
    # car nous avons besoin d'avoir une permanence logistique et nous avons besoin de pouvoir expédier des produits.

    # Date de livraison = 31/07/2020
    # Nous avons fermé le calendrier de la société les 29/30/31 juillet : 
    # le temps de transport est inchangé : 2 jours : le 29/07 étant fermé, 
    # le système devrait positionné la commande au 28/07 : premier jour ouvert dans le calendrier.

    @api.depends('is_date_livraison')
    def _date_expedition(self):
        for order in self:
            if order.is_date_livraison:
                cr      = self._cr
                uid     = self._uid
                context = self._context
                res_partner = self.env['res.partner']
                delai_transport = order.order_id.partner_id.is_delai_transport
                date_expedition = order.is_date_livraison
                date_expedition = datetime.datetime.strptime(date_expedition, '%Y-%m-%d')
                #Delai de transport en jour ouvrés (sans samedi et dimanches)
                if delai_transport:
                    while delai_transport>0:
                        date_expedition = date_expedition - datetime.timedelta(days=1)
                        weekday = date_expedition.weekday()
                        if weekday not in [5,6]:
                            delai_transport = delai_transport - 1
                # jours de fermeture de la société
                jours_fermes = res_partner.num_closing_days(order.order_id.company_id.is_calendrier_expedition_id)
                # Jours de congé de la société
                leave_dates = res_partner.get_leave_dates(order.order_id.company_id.is_calendrier_expedition_id)
                #date_expedition = date_expedition - datetime.timedelta(days=delai_transport)
                new_date = date_expedition
                while True:
                    date_txt=new_date.strftime('%Y-%m-%d')
                    num_day = int(time.strftime('%w', time.strptime( date_txt, '%Y-%m-%d')))
                    if (num_day in jours_fermes or date_txt in leave_dates):
                        new_date = new_date - datetime.timedelta(days=1)
                    else:
                        break
                date_expedition = new_date.strftime('%Y-%m-%d')
                order.is_date_expedition=date_expedition


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
            leave_dates = res_partner.get_leave_dates(partner,avec_jours_feries=True)

            # Jours fériés du pays du client 
            #jours_feries=res_partner.get_jours_feries(partner)

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
#            # jours de fermeture de la société
#            jours_fermes = res_partner.num_closing_days(company.partner_id)
#            # Jours de congé de la société
#            leave_dates = res_partner.get_leave_dates(company.partner_id)
#            delai_transport = partner.is_delai_transport
#            date_expedition = date_livraison
#            if delai_transport:
#                i = 0
#                while i < delai_transport:
#                    date = datetime.datetime.strptime(date_expedition, '%Y-%m-%d') - datetime.timedelta(days=1)
#                    date = date.strftime('%Y-%m-%d')
#                    num_day = time.strftime('%w', time.strptime(date, '%Y-%m-%d'))
#                    date_expedition = res_partner.get_day_except_weekend(date, num_day)         
#                    i += 1
#                
#                date_expedition = res_partner.get_working_day(date, num_day, jours_fermes, leave_dates)
#                
#            v['is_date_expedition'] = date_expedition 


        
            check_date = self.check_date_livraison(date_livraison, partner_id, context=context)
            if not check_date:
                warning = {
                            'title': _('Warning!'),
                            'message' : 'La date de livraison tombe pendant la fermeture du client.'
                }


            #** Recherche prix dans liste de prix pour la date et qt ***********
            if pricelist and product_id:
                ctx = dict(
                    context,
                    uom=uom,
                    date=date_livraison,
                )
                price = self.pool.get('product.pricelist').price_get(self._cr, self._uid, [pricelist],
                        product_id, qty or 1.0, partner_id, ctx)[pricelist]
                v['price_unit'] = price
                # mettre à jour is_justification
                if product_id is not False and pricelist is not False and date_livraison is not False:
                    SQL="SELECT get_pricelist_justif('sale', {}, {}, {}, '{}') FROM product_product WHERE id={}".format(pricelist, product_id, qty or 1.0, date_livraison, product_id)
                    self._cr.execute(SQL)
                    result = self._cr.fetchone()

                    v['is_justification'] = result[0];
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
        if date_order is False:
            if 'warning' in vals:
                vals['warning']=False
            return vals

        #** Recherche prix dans liste de prix pour la date et qt ***********
        price=0
        if date_order:
            if len(date_order)==10:
                if pricelist_id:
                    ctx = dict(
                        context,
                        uom=uom,
                        date=date_order,
                    )
                    price = self.pool.get('product.pricelist').price_get(self._cr, self._uid, [pricelist_id],
                            product_id, qty or 1.0, partner_id, ctx)[pricelist_id]
        #*******************************************************************
        vals['value']['price_unit'] = price
        # mettre à jour is_justification
        if product_id is not False and pricelist_id is not False and date_order is not False:
            SQL="SELECT get_pricelist_justif('sale', {}, {}, {}, '{}') FROM product_product WHERE id={}".format(pricelist_id, product_id, qty, date_order, product_id)
            self._cr.execute(SQL)
            result = self._cr.fetchone()

            vals['value']['is_justification'] = result[0];
        return vals

