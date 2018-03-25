# -*- coding: utf-8 -*-
from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning
import datetime


class is_demande_achat_invest(models.Model):
    _name='is.demande.achat.invest'
    _order='name desc'

    def _compute(self):
        uid=self._uid
        for obj in self:
            vsb=False
            if obj.state!='brouillon' and (uid==obj.chef_service_id.id or uid==obj.acheteur_id.id):
                vsb=True
            obj.vers_brouillon_vsb=vsb
            vsb=False
            if obj.state=='brouillon' and uid==obj.createur_id.id:
                vsb=True
            obj.vers_validation_rsp_vsb=vsb
            vsb=False
            if obj.state=='validation_rsp' and uid==obj.chef_service_id.id:
                vsb=True
            obj.vers_validation_direction_vsb=vsb
            vsb=False
            if obj.state=='validation_direction' and uid==obj.direction_id.id:
                vsb=True
            obj.vers_transmis_achat_vsb=vsb
            vsb=False
            if obj.state=='transmis_achat' and uid==obj.acheteur_id.id:
                vsb=True
            obj.vers_solde_vsb=vsb
            vsb=False
            if obj.state=='brouillon' and uid==obj.createur_id.id:
                vsb=True
            if obj.state=='validation_rsp' and uid==obj.chef_service_id.id:
                vsb=True
            if obj.state=='transmis_achat' and uid==obj.acheteur_id.id:
                vsb=True
            obj.vers_annule_vsb=vsb


    name                 = fields.Char("N°DA FG", readonly=True)
    createur_id          = fields.Many2one('res.users', 'Demandeur', required=True)
    chef_service_id      = fields.Many2one('res.users', 'Chef de service', required=True)
    direction_id         = fields.Many2one('res.users', 'Direction', readonly=True)
    date_creation        = fields.Date("Date de création", required=True)
    acheteur_id          = fields.Many2one('res.users', 'Acheteur', required=True)
    fournisseur_id       = fields.Many2one('res.partner', 'Fournisseur', domain=[('is_company','=',True),('is_segment_achat.name','=',u"Fournisseurs d'Investissements")])
    pricelist_id         = fields.Many2one('product.pricelist', "Liste de prix", related='fournisseur_id.property_product_pricelist_purchase', readonly=True)
    fournisseur_autre    = fields.Char("Fournisseur autre")
    delai_livraison      = fields.Date("Délai de livraison", required=True)
    lieu_livraison_id    = fields.Many2one('res.partner', 'Lieu de livraison', domain=[('is_company','=',True)], required=True)
    num_devis            = fields.Char("N° du devis")
    date_devis           = fields.Date("Date du devis")
    commentaire          = fields.Text("Commentaire")
    state                = fields.Selection([
        ('brouillon'           , 'Brouillon'),
        ('validation_rsp'      , 'Validation responsable'),
        ('validation_direction', 'Validation direction'),
        ('transmis_achat'      , 'Transmis achat'),
        ('solde'               , 'Soldé'),
        ('annule'              , 'Annulé'),
    ], "Etat")
    line_ids             = fields.One2many('is.demande.achat.invest.line'  , 'da_id', u"Lignes", copy=True)
    order_id             = fields.Many2one('purchase.order', 'Commande générée', readonly=True , copy=False)

    vers_brouillon_vsb            = fields.Boolean('Champ technique', compute='_compute', readonly=True, store=False)
    vers_validation_rsp_vsb       = fields.Boolean('Champ technique', compute='_compute', readonly=True, store=False)
    vers_validation_direction_vsb = fields.Boolean('Champ technique', compute='_compute', readonly=True, store=False)
    vers_transmis_achat_vsb       = fields.Boolean('Champ technique', compute='_compute', readonly=True, store=False)
    vers_solde_vsb                = fields.Boolean('Champ technique', compute='_compute', readonly=True, store=False)
    vers_annule_vsb               = fields.Boolean('Champ technique', compute='_compute', readonly=True, store=False)


    @api.multi
    def _lieu_livraison_id(self):
        user = self.env['res.users'].browse(self._uid)
        partner_id = user.company_id.partner_id.id
        return partner_id


    @api.multi
    def _dirigeant_id(self):
        if self._uid==1:
            return 1
        user = self.env['res.users'].search([('login','=','eg')])
        return user.id


    _defaults = {
        'date_creation'    : lambda *a: fields.datetime.now(),
        'createur_id'      : lambda obj, cr, uid, context: uid,
        'direction_id'     : lambda self,cr,uid,context: self._dirigeant_id(cr,uid,context),
        'state'            : 'brouillon',
        'lieu_livraison_id': lambda self,cr,uid,context: self._lieu_livraison_id(cr,uid,context),
    }


    @api.multi
    def fournisseur_id_on_change(self,fournisseur_id):
        res={}
        if fournisseur_id:
            res['value']={}
            partner = self.env['res.partner'].browse(fournisseur_id)
            lieu_livraison_id=partner.is_livre_a_id.id
            if lieu_livraison_id:
                res['value']['lieu_livraison_id']=lieu_livraison_id
        return res


    @api.model
    def create(self, vals):
        data_obj = self.env['ir.model.data']
        sequence_ids = data_obj.search([('name','=','is_demande_achat_invest_seq')])
        if sequence_ids:
            sequence_id = data_obj.browse(sequence_ids[0].id).res_id
            vals['name'] = self.env['ir.sequence'].get_id(sequence_id, 'id')
        obj = super(is_demande_achat_invest, self).create(vals)
        return obj


    @api.multi
    def vers_brouillon_action(self):
        for obj in self:
            #if obj.acheteur_id.id==self._uid or obj.chef_service_id.id==self._uid:
            obj.sudo().state="brouillon"


    @api.multi
    def vers_validation_rsp_action(self):
        for obj in self:
            subject=u'['+obj.name+u'] Validation responsable'
            email_to=obj.chef_service_id.email
            user  = self.env['res.users'].browse(self._uid)
            email_from = user.email
            nom   = user.name
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url=base_url+u'/web#id='+str(obj.id)+u'&view_type=form&model=is.demande.achat.invest'
            body_html=u"""
                <p>Bonjour,</p>
                <p>"""+nom+""" vient de passer la demande d'investissement <a href='"""+url+"""'>"""+obj.name+"""</a> à l'état 'Validation responsable'.</p>
                <p>Merci d'en prendre connaissance.</p>
            """
            self.envoi_mail(email_from,email_to,subject,body_html)
            obj.state="validation_rsp"


    @api.multi
    def vers_validation_direction_action(self):
        for obj in self:
            subject=u'['+obj.name+u'] Validation direction'
            email_to=obj.direction_id.email
            user  = self.env['res.users'].browse(self._uid)
            email_from = user.email
            nom   = user.name
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url=base_url+u'/web#id='+str(obj.id)+u'&view_type=form&model=is.demande.achat.invest'
            body_html=u"""
                <p>Bonjour,</p>
                <p>"""+nom+""" vient de passer la demande d'investissement <a href='"""+url+"""'>"""+obj.name+"""</a> à l'état 'Validation direction'.</p>
                <p>Merci d'en prendre connaissance.</p>
            """
            self.envoi_mail(email_from,email_to,subject,body_html)
            obj.state="validation_direction"


    @api.multi
    def vers_transmis_achat_action(self):
        for obj in self:
            subject=u'['+obj.name+u'] Transmis achat'
            email_to=obj.acheteur_id.email
            user  = self.env['res.users'].browse(self._uid)
            email_from = user.email
            nom   = user.name
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url=base_url+u'/web#id='+str(obj.id)+u'&view_type=form&model=is.demande.achat.invest'
            body_html=u"""
                <p>Bonjour,</p>
                <p>"""+nom+""" vient de passer la demande d'investissement <a href='"""+url+"""'>"""+obj.name+"""</a> à l'état 'Transmis achat'.</p>
                <p>Merci d'en prendre connaissance.</p>
            """
            self.envoi_mail(email_from,email_to,subject,body_html)
            obj.state="transmis_achat"


    @api.multi
    def vers_solde_action(self):
        for obj in self:
            order_obj      = self.env['purchase.order']
            order_line_obj = self.env['purchase.order.line']
            partner=obj.fournisseur_id
            if partner.id==False:
                raise Warning('Fournisseur obligatoire pour générer la commande !')
            for line in obj.line_ids:
                if line.num_chantier==False:
                    raise Warning('N° du chantier obligatoire sur toutes les lignes de la commande !')
                else:
                    if len(line.num_chantier)!=5:
                        raise Warning('N° du chantier sur 5 chiffres obligatoire sur toutes les lignes de la commande !')
            if partner.property_product_pricelist_purchase.id == False:
                raise Warning('Liste de prix non renseignée pour ce fournisseur')
            else:
                is_document=False
                #for line in obj.line_ids:
                #    is_document=u'M0000/'+line.num_chantier
                vals={
                    'partner_id'      : partner.id,
                    'is_livre_a_id'   : obj.lieu_livraison_id.id,
                    'location_id'     : partner.is_source_location_id.id,
                    'fiscal_position' : partner.property_account_position.id,
                    'payment_term_id' : partner.property_supplier_payment_term.id,
                    'pricelist_id'    : partner.property_product_pricelist_purchase.id,
                    'currency_id'     : partner.property_product_pricelist_purchase.currency_id.id,
                    'is_num_da'       : obj.name,
                    #'is_document'     : is_document,
                    'is_demandeur_id' : obj.createur_id.id,
                }
                order=order_obj.create(vals)
                obj.order_id=order.id
                if order:
                    for line in obj.line_ids:
                        vals={}
                        res=order_line_obj.onchange_product_id(
                            order.pricelist_id.id, 
                            line.product_id.id, 
                            line.quantite, 
                            line.uom_id.id, 
                            partner.id, 
                            date_order         = False, 
                            fiscal_position_id = partner.property_account_position.id, 
                            date_planned       = False, 
                            name               = False, 
                            price_unit         = line.prix, 
                            state              = 'draft'
                        )
                        vals=res['value']
                        vals['order_id']        = order.id
                        vals['date_planned']    = obj.delai_livraison
                        vals['product_id']      = line.product_id.id
                        vals['is_num_chantier'] = u'M0000/'+str(line.num_chantier)
                        name=[]
                        if line.product_id.id:
                            name.append(line.product_id.is_code+u' - '+line.product_id.name)
                        if line.designation1:
                            name.append(line.designation1)
                        if line.designation2:
                            name.append(line.designation2)
                        vals['name']='\n'.join(name)
                        if 'taxes_id' in vals:
                            vals.update({'taxes_id': [[6, False, vals['taxes_id']]]})
                        order_line=order_line_obj.create(vals)
                    order.wkf_bid_received() 
                    res=order.wkf_confirm_order()
                    order.action_picking_create() 
                    order.wkf_approve_order()
                    obj.sudo().state="solde"



    @api.multi
    def vers_annule_action(self):
        for obj in self:
            if obj.createur_id.id==self._uid or obj.acheteur_id.id==self._uid:
                obj.sudo().state="annule"


    @api.multi
    def envoi_mail(self, email_from,email_to,subject,body_html):
        for obj in self:
            vals={
                'email_from'    : email_from, 
                'email_to'      : email_to, 
                'email_cc'      : email_from,
                'subject'       : subject,
                'body_html'     : body_html, 
            }
            email=self.env['mail.mail'].create(vals)
            if email:
                self.env['mail.mail'].send(email)


class is_demande_achat_invest_line(models.Model):
    _name='is.demande.achat.invest.line'
    _order='da_id,sequence'


    @api.depends('product_id','quantite','prix')
    def _compute(self):
        for obj in self:
            if obj.product_id:
                obj.uom_id=obj.product_id.uom_po_id
            obj.montant=obj.quantite*obj.prix

    da_id                  = fields.Many2one('is.demande.achat.invest', "Demande d'achat", required=True, ondelete='cascade', readonly=True)
    sequence               = fields.Integer('Ordre')
    product_id             = fields.Many2one('product.product', 'Article', domain=[('is_category_id.name','=','72')])
    designation1           = fields.Char("Désignation 1")
    designation2           = fields.Char("Désignation 2")
    uom_id                 = fields.Many2one('product.uom', "Unité d'achat")
    quantite               = fields.Float("Quantité", digits=(14,4), required=True)
    prix                   = fields.Float("Prix"    , digits=(14,4))
    montant                = fields.Float("Montant", compute='_compute', readonly=True, store=True)
    num_chantier           = fields.Char("N° du chantier sur 5 chiffres", help="Saisir 5 chiffres uniquement")

    @api.multi
    def product_id_on_change(self,parent,product_id,quantite):
        cr=self._cr
        res={}
        fournisseur_id=parent.fournisseur_id
        if fournisseur_id:
            partner = self.env['res.partner'].browse(fournisseur_id)
            pricelist_id=partner.property_product_pricelist_purchase.id
            if product_id and pricelist_id:
                res['value']={}
                product = self.env['product.product'].browse(product_id)
                now=datetime.datetime.now().strftime('%Y-%m-%d')
                sql="""
                    select 
                        is_prix_achat("""+str(pricelist_id)+""", """+str(product_id)+""", """+str(quantite)+""", '"""+now+"""') 
                    from product_product
                    where id="""+str(product_id)+"""
                """
                cr.execute(sql)
                prix=0
                for row in cr.fetchall():
                    prix=row[0]
                if prix>0:
                    res['value']['prix']=prix
        return res


