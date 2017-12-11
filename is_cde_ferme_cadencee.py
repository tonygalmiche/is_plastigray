# -*- coding: utf-8 -*-
from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning


modele_mail=u"""
    <html>
        <head>
            <meta content="text/html; charset=UTF-8" http-equiv="Content-Type">
        </head>
        <body>
            <p>Bonjour, </p>
            <p>Veuillez trouver ci-joint notre document.</p>
            <p>Cordialement</p>
            <p>[from]</p>
        </body>
    </html>
"""


class is_cde_ferme_cadencee(models.Model):
    _name='is.cde.ferme.cadencee'
    _order='name desc'

    name           = fields.Char("N° de commande ferme cadencée", readonly=True)
    partner_id     = fields.Many2one('res.partner'    , 'Fournisseur', required=True)
    contact_id     = fields.Many2one('res.partner', 'Contact Logistique')
    is_livre_a_id  = fields.Many2one('res.partner', 'Livrer à', related='partner_id.is_livre_a_id')
    product_id     = fields.Many2one('product.product', u"Article"   , required=True)
    demandeur_id   = fields.Many2one('res.users', 'Demandeur', readonly=True)
    order_ids      = fields.One2many('is.cde.ferme.cadencee.order', 'cfc_id', u"Commandes")
    historique_ids = fields.One2many('is.cde.ferme.cadencee.histo'  , 'order_id', u"Historique")

    @api.model
    def create(self, vals):

        data_obj = self.env['ir.model.data']
        sequence_ids = data_obj.search([('name','=','is_cde_ferme_cadencee_seq')])
        if sequence_ids:
            sequence_id = data_obj.browse(sequence_ids[0].id).res_id
            vals['name'] = self.env['ir.sequence'].get_id(sequence_id, 'id')
        obj = super(is_cde_ferme_cadencee, self).create(vals)
        self.verification_saisies(obj)
        return obj


    @api.multi
    def write(self,vals):
        res=super(is_cde_ferme_cadencee, self).write(vals)
        for obj in self:
            self.verification_saisies(obj)
        return res


    @api.multi
    def verification_saisies(self, obj):
        for line in obj.order_ids:
            nb=len(line.order_id.order_line)
            if nb!=1:
                raise Warning(u"La commande "+str(line.order_id.name)+u" à "+str(nb)+u" lignes")
            for row in line.order_id.order_line:
                if row.product_id!=obj.product_id:
                    raise Warning(u"L'article de la commande "+str(line.order_id.name)+u" ne correspond pas à l'article indiqué")


    @api.multi
    def set_histo(self, order_id, description):
        vals={
            'order_id'   : order_id,
            'description': description,
        }
        histo=self.env['is.cde.ferme.cadencee.histo'].create(vals)


    @api.multi
    def actualiser_commandes(self):
        cr , uid, context = self.env.args
        for obj in self:

            #** Recherche du contact logistique ********************************
            if obj.contact_id.id==False:
                SQL="""
                    select rp.id, rp.is_type_contact, itc.name
                    from res_partner rp inner join is_type_contact itc on rp.is_type_contact=itc.id
                    where rp.parent_id="""+str(obj.partner_id.id)+""" and itc.name ilike '%logistique%' limit 1
                """
                cr.execute(SQL)
                result = cr.fetchall()
                for row in result:
                    obj.contact_id=row[0]
            #*******************************************************************

            self.set_histo(obj.id, u'Actualisation des commandes')
            obj.demandeur_id=uid
            for order in obj.order_ids:
                #** Recherche du dernier numéro de BL **************************
                SQL="""
                    select sp.is_num_bl, sp.is_date_reception, sm.product_uom_qty
                    from stock_picking sp inner join stock_move sm on sm.picking_id=sp.id
                    where 
                        sm.product_id="""+str(obj.product_id.id)+""" and
                        sp.is_date_reception is not null and
                        sm.state='done' and
                        sp.picking_type_id=1 and 
                        sp.partner_id="""+str(obj.partner_id.id)+""" and
                        sp.is_purchase_order_id="""+str(order.order_id.id)+""" 
                    order by sp.is_date_reception desc, sm.date desc
                    limit 1
                """
                cr.execute(SQL)
                result = cr.fetchall()
                num_bl  = False
                date_bl = False
                for row in result:
                    num_bl  = row[0]
                    date_bl = row[1]
                #***************************************************************

                #** Recherche du total réceptionné *****************************
                SQL="""
                    select sum(sm.product_uom_qty)
                    from stock_picking sp inner join stock_move sm on sm.picking_id=sp.id
                    where 
                        sm.product_id="""+str(obj.product_id.id)+""" and
                        sp.is_date_reception is not null and
                        sm.state='done' and
                        sp.picking_type_id=1 and 
                        sp.partner_id="""+str(obj.partner_id.id)+""" and
                        sp.is_purchase_order_id="""+str(order.order_id.id)+""" 
                    limit 1
                """
                cr.execute(SQL)
                result = cr.fetchall()
                qt_rcp = 0
                for row in result:
                    qt_rcp  = row[0] or 0
                #***************************************************************
                order.num_bl       = num_bl
                order.date_bl      = date_bl
                order.qt_rcp       = qt_rcp
                order.qt_reste     = order.product_qty-qt_rcp
                order.date_planned = order.order_id.minimum_planned_date


    @api.multi
    def envoyer_par_mail(self):
        for obj in self:
            # ** Recherche si une pièce jointe est déja associèe ***************
            attachment_obj = self.env['ir.attachment']
            model=self._name
            name='commande-ferme-cadencee.pdf'
            attachments = attachment_obj.search([('res_model','=',model),('res_id','=',obj.id),('name','=',name)])
            # ******************************************************************

            # ** Creation ou modification de la pièce jointe *******************
            pdf = self.env['report'].get_pdf(obj, 'is_plastigray.report_cde_ferme_cadencee')
            vals = {
                'name':        name,
                'datas_fname': name,
                'type':        'binary',
                'res_model':   model,
                'res_id':      obj.id,
                'datas':       pdf.encode('base64'),
            }
            if attachments:
                for attachment in attachments:
                    attachment.write(vals)
                    attachment_id=attachment.id
            else:
                attachment = attachment_obj.create(vals)
                attachment_id=attachment.id
            # ******************************************************************

            subject=u'Commande ferme cadencée '+str(obj.partner_id.name)
            email_to=obj.contact_id.email
            self.set_histo(obj.id, u'Commande envoyée par mail à '+str(email_to))
            if email_to==False:
                raise Warning(u"Mail non renseigné pour ce contact !")
            user  = self.env['res.users'].browse(self._uid)
            email = user.email
            nom   = user.name
            if email==False:
                raise Warning(u"Votre mail n'est pas renseigné !")
            if email:
                email_vals = {}
                body_html=modele_mail.replace('[from]', nom)
                email_vals.update({
                    'subject'       : subject,
                    'email_to'      : email_to, 
                    'email_cc'      : email,
                    'email_from'    : email, 
                    'body_html'     : body_html.encode('utf-8'), 
                    'attachment_ids': [(6, 0, [attachment_id])] 
                })
                email_id=self.env['mail.mail'].create(email_vals)
                if email_id:
                    self.env['mail.mail'].send(email_id)


class is_cde_ferme_cadencee_order(models.Model):
    _name='is.cde.ferme.cadencee.order'
    _order='date_planned'

    @api.depends('order_id')
    def _compute(self):
        for obj in self:
            if obj.order_id:
                for line in obj.order_id.order_line:
                    obj.date_planned = line.date_planned
                    obj.product_qty  = line.product_qty
                    obj.product_uom  = line.product_uom

    cfc_id       = fields.Many2one('is.cde.ferme.cadencee', 'Commande ferme cadencée', required=True, ondelete='cascade', readonly=True)
    order_id     = fields.Many2one('purchase.order', 'Commande Fournisseur', required=True)
    date_planned = fields.Date("Date prévue"              , compute='_compute', readonly=True, store=True)
    product_uom  = fields.Many2one('product.uom', 'Unité' , compute='_compute', readonly=True, store=True)
    product_qty  = fields.Float("Quantité commandée"      , compute='_compute', readonly=True, store=True)

    qt_rcp       = fields.Float("Quantité réceptionnée", readonly=True)
    qt_reste     = fields.Float("Reste à réceptionner" , readonly=True)
    num_bl       = fields.Char("Dernier BL"            , readonly=True)
    date_bl      = fields.Date("Date BL"               , readonly=True)


class is_cde_ferme_cadencee_histo(models.Model):
    _name='is.cde.ferme.cadencee.histo'
    _order='name desc'

    order_id    = fields.Many2one('is.cde.ferme.cadencee', 'Commande ferme cadencée', required=True, ondelete='cascade', readonly=True)
    name        = fields.Datetime("Date")
    user_id     = fields.Many2one('res.users', 'Utilisateur')
    description = fields.Char("Opération éffectuée")

    _defaults = {
        'name'   : lambda *a: fields.datetime.now(),
        'user_id': lambda obj, cr, uid, context: uid,
    }

