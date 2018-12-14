# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning
from math import *
from openerp.addons.purchase import purchase
from datetime import datetime


class purchase_order_line(models.Model):
    _inherit = "purchase.order.line"

    is_justification = fields.Char("Justification" , help="Ce champ est obligatoire si l'article n'est pas renseigné ou le prix à 0")
    is_num_chantier  = fields.Char("N° du chantier", help="Champ utilisé pour la gestion des investissements sous la forme Mxxxx/xxxxx")

    def init(self, cr):
        cr.execute("""
CREATE OR REPLACE FUNCTION get_pricelist_justif(pricelisttype text, pricelistid integer, productid integer, qt float, date date) RETURNS text AS $$
BEGIN
    RETURN (
        select justification
        from product_pricelist ppl inner join product_pricelist_version ppv on ppv.pricelist_id=ppl.id
                                   inner join product_pricelist_item    ppi on ppi.price_version_id=ppv.id
        where ppi.product_id=productid
            and ppl.id=pricelistid
            and min_quantity<=qt
            and ppl.type=pricelisttype and ppl.active='t'
            and (ppv.date_end   is null or ppv.date_end   >= date)
            and (ppv.date_start is null or ppv.date_start <= date)

            and (ppi.date_end   is null or ppi.date_end   >= date)
            and (ppi.date_start is null or ppi.date_start <= date)
        order by ppi.sequence limit 1
    );
END;
$$ LANGUAGE plpgsql;
        """)

    @api.multi
    def onchange_product_id(self, pricelist_id, product_id, qty, uom_id,
            partner_id, date_order=False, fiscal_position_id=False, date_planned=False,
            name=False, price_unit=False, state='draft'):
        res = super(purchase_order_line, self).onchange_product_id(pricelist_id, product_id, qty, uom_id,
            partner_id, date_order=date_order, fiscal_position_id=fiscal_position_id, date_planned=date_planned,
            name=name, price_unit=price_unit, state=state)
        if product_id:
            product = self.env['product.product'].browse(product_id)
            product_uom_obj = self.env['product.uom']
            if not uom_id:
                uom_id=product.uom_po_id.id
            qty = product_uom_obj._compute_qty(uom_id, qty, product.uom_id.id)
            lot      = product.lot_mini
            multiple = product.multiple
            if multiple==0:
                multiple=1
            if qty<lot:
                qty=lot
            else:
                delta=round(qty-lot,8)
                qty=lot+multiple*ceil(delta/multiple)
            qty = product_uom_obj._compute_qty(product.uom_id.id, qty, uom_id)
            res['value']['product_qty'] = qty
            if pricelist_id is not False and date_order is not False:
                # supression de l'heure à la date
                date = date_order.split()[0]
                SQL="SELECT get_pricelist_justif('purchase', {}, {}, {}, '{}') FROM product_product WHERE id={}".format(pricelist_id, product_id, qty, date, product_id)
                self._cr.execute(SQL)
                result = self._cr.fetchone()

                res['value']['is_justification'] = result[0];
        return res


    @api.multi
    def onchange_date_planned(self, date_planned, partner_id, company_id):
        v = {}
        warning = {}
        res=True
        partner_obj=self.env['res.partner']
        #** Recherche si le partner est ouvert cette journée avec les jours fériés du pays
        if partner_id:
            partner = partner_obj.browse(partner_id)
            if partner:
                res = partner_obj.test_date_dispo(date_planned, partner, avec_jours_feries=True)
        #** Recherche si plastigray est ouvert cette journée sans les jours fériés du pays
        if company_id and res:
            partner = self.env['res.company'].browse(company_id).partner_id
            if partner:
                res = partner_obj.test_date_dispo(date_planned, partner, avec_jours_feries=False)
        if res==False:
            warning = {
                'title': _('Warning!'),
                'message' : 'La date prévue tombe pendant la fermeture du fournisseur ou de plastigray !'
            }
        return {
            'value': v,
            'warning': warning,
        }


class purchase_order(models.Model):
    _inherit = "purchase.order"


    is_contact_id        = fields.Many2one('res.partner', 'Contact Logistique')
    is_livre_a_id        = fields.Many2one('res.partner', 'Livrer à', help="Indiquez l'adresse de livraison si celle-ci est différente de celle de la société")
    is_num_da            = fields.Char("N°Demande d'achat")
    is_document          = fields.Char("Document (N° de dossier)")
    is_demandeur_id      = fields.Many2one('res.users', 'Demandeur')
    is_date_confirmation = fields.Date("Date de confirmation du fournisseur")
    is_commentaire       = fields.Text("Commentaire")
    is_acheteur_id       = fields.Many2one('res.users','Acheteur')
    is_date_envoi_mail   = fields.Datetime("Mail envoyé le", readonly=True)
    is_cfc_id            = fields.Many2one('is.cde.ferme.cadencee', 'Commande ferme cadencée', readonly=True)
    is_date_end_cfc      = fields.Date("Date de fin de la cde ferme cadencée", readonly=True)

    _defaults = {
        'is_demandeur_id': lambda obj, cr, uid, ctx=None: uid,
    }


    @api.multi
    def envoyer_par_mail(self):
        cr , uid, context = self.env.args
        modele_mail=u"""
        <html>
            <head>
                <meta content="text/html; charset=UTF-8" http-equiv="Content-Type">
            </head>
            <body>
                <font>Bonjour, </font>
                <br><br>
                <font> Veuillez trouver ci-joint notre commande.</font>
                <br><br>
                Cordialement <br><br>
                [from]<br>
            </body>
        </html>
        """

        for obj in self:
            email_contact=obj.is_contact_id.email
            if email_contact==False:
                raise Warning(u"Mail non renseigné pour ce contact !")
            user  = self.env['res.users'].browse(uid)
            email = user.email
            nom   = user.name
            if email==False:
                raise Warning(u"Votre mail n'est pas renseigné !")


            #** Génération du PDF **********************************************
            name=u'commande-'+obj.name+u'.pdf'
            pdf = self.env['report'].get_pdf(obj, 'is_plastigray.is_report_purchaseorder')
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

            email_cc      = nom+u' <'+email+u'>'

            #** Demandeur en copie *********************************************
            if obj.is_demandeur_id.email:
                print obj.is_demandeur_id.name, obj.is_demandeur_id.email
                email_cc = email_cc + ',' + obj.is_demandeur_id.name + u' <'+obj.is_demandeur_id.email+u'>'
            #*******************************************************************

            email_from    = email_cc
            email_contact = obj.is_contact_id.name+u' <'+obj.is_contact_id.email+u'>'

            subject    = u'Commande Plastigray '+obj.name+' pour '+obj.partner_id.name
            #subject    = u'Commande Plastigray '+obj.name+' pour '+obj.partner_id.name+u' (to='+email_contact+u')'

            email_to = email_contact
            #email_to = email_cc

            email_vals = {}
            body_html=modele_mail.replace('[from]', user.name)
            email_vals.update({
                'subject'       : subject,
                'email_to'      : email_to,
                'email_cc'      : email_cc,
                'email_from'    : email_from, 
                'body_html'     : body_html.encode('utf-8'), 
                'attachment_ids': [(6, 0, [attachment_id])] 
            })

            email_id=self.env['mail.mail'].create(email_vals)
            if email_id:
                self.env['mail.mail'].send(email_id)

            obj.message_post(u'Commande envoyée par mail à '+email_contact)
            obj.is_date_envoi_mail=datetime.now()


    @api.multi
    def onchange_partner_id(self, partner_id, context=None):
        cr , uid, context = self.env.args
        res = super(purchase_order, self).onchange_partner_id(partner_id)


        #** Recherche du contact logistique ************************************
        if partner_id:
            SQL="""
                select rp.id, rp.is_type_contact, itc.name
                from res_partner rp inner join is_type_contact itc on rp.is_type_contact=itc.id
                where 
                    rp.parent_id="""+str(partner_id)+""" and 
                    rp.active='t' and
                    itc.name ilike '%logistique%' 
                limit 1
            """
            cr.execute(SQL)
            result = cr.fetchall()
            for row in result:
                if 'value' in res:
                    res['value'].update({
                        'is_contact_id': row[0]
                    })
        #***********************************************************************


        if 'value' in res:
            partner = self.env['res.partner'].browse(partner_id)
            res['value'].update({
                'is_livre_a_id': partner.is_livre_a_id.id
            })
        return res


    @api.multi
    def actualiser_prix_commande(self):
        for obj in self:
            for line in obj.order_line:
                res = line.onchange_product_id(
                    obj.pricelist_id.id, 
                    line.product_id.id, 
                    line.product_qty, 
                    line.product_uom.id,
                    obj.partner_id.id, 
                    date_order   = line.date_planned+u' 12:00:00',
                    date_planned = line.date_planned,
                )
                price=res['value']['price_unit']
                if not price:
                    raise Warning(u"Modification non éffectuée, car prix non trouvé")
                line.price_unit=price


    @api.multi
    def actualiser_taxes_commande(self):
        for obj in self:
            order_line_obj = self.env['purchase.order.line']
            obj.fiscal_position = obj.partner_id.property_account_position.id
            obj.payment_term_id = obj.partner_id.property_supplier_payment_term.id

            for line in obj.order_line:
                res=order_line_obj.onchange_product_id(
                    obj.pricelist_id.id, 
                    line.product_id.id, 
                    line.product_qty, 
                    line.product_uom.id, 
                    obj.partner_id.id, 
                    date_order         = line.date_order, 
                    fiscal_position_id = obj.partner_id.property_account_position.id, 
                    date_planned       = line.date_planned, 
                    name               = line.name, 
                    price_unit         = line.price_unit, 
                )
                taxes_id=[]
                for taxe_id in res['value']['taxes_id']:
                    taxes_id.append(taxe_id)
                line.taxes_id=[(6,0,taxes_id)]


    @api.multi
    def test_prix0(self,obj):
        for line in obj.order_line:
            if not line.is_justification and not line.price_unit:
                raise Warning(u"Prix à 0 sans justification pour l'article "+str(line.product_id.is_code))


    @api.multi
    def write(self,vals):
        res=super(purchase_order, self).write(vals)
        for obj in self:
            self.test_prix0(obj)
        return res


    @api.model
    def create(self, vals):
        obj = super(purchase_order, self).create(vals)
        self.test_prix0(obj)
        return obj


    @api.multi
    def get_da(self):
        res=False
        for obj in self:
            if obj.is_num_da:
                type_da=obj.is_num_da[:4]
                model=False
                if type_da=='DAFG':
                    model = 'is.demande.achat.fg'
                if type_da=='DAI-':
                    model = 'is.demande.achat.invest'
                if type_da=='DAM-':
                    model = 'is.demande.achat.moule'
                if model:
                    das = self.env[model].search([('name','=',obj.is_num_da)])
                    for da in das:
                        date_devis=da.date_devis
                        if date_devis:
                            d=datetime.strptime(date_devis,'%Y-%m-%d')
                            date_devis=d.strftime('%d/%m/%Y')
                        res=''
                        if da.num_devis:
                            res=res+da.num_devis
                        if date_devis:
                            res=res+' du '+date_devis
        return res 



