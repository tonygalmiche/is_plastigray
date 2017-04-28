# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning
import base64
import tempfile
import os
from pyPdf import PdfFileWriter, PdfFileReader
from contextlib import closing
import datetime


modele_mail=u"""
<html>
  <head>
    <meta content="text/html; charset=UTF-8" http-equiv="Content-Type">
  </head>
  <body>
<font>Bonjour, </font>
<br><br>
<font> Veuillez trouver ci-joint notre document.</font>
<br><br>
<font> <u><b>RAPPEL : Exigences particulières / mode de fonctionnement</b></u></font>
<br><br>
<table border="1" cellpadding="2" cellspacing="2">
  <tbody>
    <tr>
      <td valign="top"><font><b><u>LOGISTIQUE : </u></b></font><br>
        <br>
        <div align="justify"><font
           >Pour chaque commande, un Accusé
            Réception doit être envoyé sous 72 heures. Au delà,
            toute commande non discutée est considérée comme
            acceptée dans l'état.</font><font><br>
          </font> <font>Les
            variations entre prévisionnel et ferme de l'ordre de
            +/-30% seront considérées comme standards. </font><font
           >Les demandes
            de livraison supplémentaires ou diminution de
            commande pourront être effectuées 72h avant la date
            de livraison. </font><font><br>
          </font> <font><br>
          </font> <font><font
             >PLASTIGRAY s'engage sur une
              prise de stock que sur le ferme et non sur le
              ferme + prévisionnel. </font></font><font
           ><br>
          </font> <font><font
             >Durant les périodes de
              congés, les commandes ne seront pas anticipées, le
              fournisseur prendra les mesures nécessaires pour
              livrer aux dates demandées.</font></font><font
           ><br>
          </font> <font><br>
          </font> <font><font
             >Les transports
              exceptionnels, pour retard de livraisons ou
              remplacement de pièces non conformes seront à la
              charge du fournisseur. <br>
            </font></font><font><b><small>L<font
                 ><font>e(s) cout(s) et quantité(s) mis en
                    cause, devront être communiqués au service
                    Achats (Ces informations seront prises en
                    compte dans la prestation commerciale
                    annuelle, mais ne pourront, en aucun cas et
                    à quelque titre que ce soit, être
                    considérées comme constituant une
                    justification de la prise en charge des
                    coûts par PLASTIGRAY SAS.)</font></font></small></b><br>
          </font> </div>
      </td>
      <td valign="top"><font><u><b>DOCUMENTAIRES</b></u></font><br>
        <br>
        <font><font><font>Le bordereau de livraison doit mentionner : </font></font></font><br>
        <ul>
          <li><font><font
               ><font>le numéro de commande</font></font></font><font
             > <font><font
                 ><font>Plastigray</font></font></font></font></li>
          <li><font><font
               ><font>le code article Plastigray</font></font></font></li>
          <li><font><font
               ><font>la désignation </font></font></font><font
             ><font
               ><font>Plastigray</font></font></font></li>
          <li><font><font
               ><font>la quantité livrée </font></font></font><br>
            <font><font
               ><font> </font></font></font></li>
        </ul>
        <p><font>Pour <b>les
            </b><b>matières</b><b> </b><b>premières</b><b>, le
              certificat de conformité</b><b>/d'analyse</b> doit
            obligatoirement être fourni au moment de la
            livraison. </font><font><br>
          </font> </p>
        <br>
      </td>
    </tr>
    <tr>
      <td valign="top"><font><u><b>QUALITE </b></u><u><b>/
              TECHNIQUE</b></u></font><br>
        <font><u><b> </b></u></font><br>
        <font> Les produits livrés doivent être conformes aux EI validés et cahier des charges.</font><br>
        <font> Les demandes de dérogation
          doivent être envoyées et acceptées par votre contact
          Qualité avant l'expédition des produits.</font><br>
        <font> Toute modification envisagée du
          produit ou du process doit être validée au préalable
          par l'équipe projet PLASTIGRAY. La responsabilité du
          fournisseur sera engagée, en cas de modification du
          produit ou du process effectuée sans l'accord de
          PLASTIGRAY.</font></td>
      <td valign="top"><font><u><b>ACHATS </b></u></font><br>
        <br>
        <font> En cas de modification de prix ou
          de délai de livraison habituel, le service achats doit
          être prévenu dans un délai suffisant, pour permettre à
          PLASTIGRAY de répercuter les changements à ses clients.</font></td>
    </tr>
  </tbody>
</table>
<br>
<br>
Cordialement <br><br>
[from]<br>
</body></html>
"""



type_commande_list=[
    ('ouverte'         , 'Commande ouverte'),
    ('ferme'           , 'Commande ferme avec horizon'),
    ('ferme_uniquement', 'Commande ferme uniquement')
]

class is_cde_ouverte_fournisseur(models.Model):
    _name='is.cde.ouverte.fournisseur'
    _order='partner_id'

    name                 = fields.Char("N°", readonly=True)
    partner_id           = fields.Many2one('res.partner', 'Fournisseur'        , required=True)
    contact_id           = fields.Many2one('res.partner', 'Contact Logistique')
    pricelist_id         = fields.Many2one('product.pricelist', 'Liste de prix', related='partner_id.property_product_pricelist_purchase', readonly=True)
    type_commande        = fields.Selection(type_commande_list, "Type de commande", required=True)
    sans_commande        = fields.Selection([('oui', 'Oui'),('non', 'Non')], "Articles sans commandes", help="Imprimer dans les documents les articles sans commandes")
    attente_confirmation = fields.Integer("Attente confirmation fournisseur", readonly=True)
    commentaire          = fields.Text("Commentaire")
    product_ids          = fields.One2many('is.cde.ouverte.fournisseur.product', 'order_id', u"Articles")
    tarif_ids            = fields.One2many('is.cde.ouverte.fournisseur.tarif'  , 'order_id', u"Tarifs")
    historique_ids       = fields.One2many('is.cde.ouverte.fournisseur.histo'  , 'order_id', u"Historique")


    @api.model
    def create(self, vals):
        self.test_unique(vals['partner_id'])
        data_obj = self.env['ir.model.data']
        sequence_ids = data_obj.search([('name','=','is_cde_ouverte_fournisseur_seq')])
        if sequence_ids:
            sequence_id = data_obj.browse(sequence_ids[0].id).res_id
            vals['name'] = self.env['ir.sequence'].get_id(sequence_id, 'id')
        obj = super(is_cde_ouverte_fournisseur, self).create(vals)
        self.update_partner(obj)
        return obj


    @api.multi
    def write(self,vals):
        res=super(is_cde_ouverte_fournisseur, self).write(vals)
        for obj in self:
            self.update_partner(obj)
            self.test_unique(obj.partner_id.id)
        return res


    @api.multi
    def unlink(self):
        for obj in self:
            obj.partner_id.is_type_cde_fournisseur=False
        res=super(is_cde_ouverte_fournisseur, self).unlink()


    @api.multi
    def update_partner(self, obj):
        obj.partner_id.is_type_cde_fournisseur=obj.type_commande


    @api.multi
    def test_unique(self, partner_id):
        ids=self.env['is.cde.ouverte.fournisseur'].search([ ('partner_id', '=', partner_id) ])
        if len(ids)>1:
            raise Warning(u"Une commande ouverte existe déjà pour ce fournisseur !")






    @api.multi
    def _merge_pdf(self, documents):
        """Merge PDF files into one.
        :param documents: list of path of pdf files
        :returns: path of the merged pdf
        """
        writer = PdfFileWriter()
        streams = []  # We have to close the streams *after* PdfFilWriter's call to write()
        for document in documents:
            pdfreport = file(document, 'rb')
            streams.append(pdfreport)
            reader = PdfFileReader(pdfreport)
            for page in range(0, reader.getNumPages()):
                writer.addPage(reader.getPage(page))

        merged_file_fd, merged_file_path = tempfile.mkstemp(suffix='.pdf', prefix='report.merged.tmp.')
        with closing(os.fdopen(merged_file_fd, 'w')) as merged_file:
            writer.write(merged_file)

        for stream in streams:
            stream.close()

        return merged_file_path




    @api.multi
    def create_ferme_uniquement(self,name):
        for obj in self:
            orders=[]
            nb_imprimer=0
            for line in obj.product_ids:
                if line.imprimer:
                    nb_imprimer=nb_imprimer+1
            if nb_imprimer==0:
                products=self.env['is.cde.ouverte.fournisseur.product'].search([('order_id','=',obj.id)])
            else:
                products=self.env['is.cde.ouverte.fournisseur.product'].search([('order_id','=',obj.id),('imprimer','=',True)])
            for product in products:
                #now  = datetime.date.today()                     # Date du jour
                #date_approve = now + datetime.timedelta(days=-7) # Date -7 jours
                #date_approve = date_approve.strftime('%Y-%m-%d') # Formatage
                where=[
                    ('product_id'  ,'=', product.id),
                    #('date_approve','>', date_approve),
                ]
                lines=self.env['is.cde.ouverte.fournisseur.line'].search(where)
                for line in lines:
                    if line.imprimer_commande:
                        order=line.purchase_order_id
                        if not order in orders:
                            orders.append(order)

            #if len(orders)==0:
            #    raise Warning(u"Aucune commande à imprimer")

            paths=[]
            for order in orders:
                pdfreport_id, pdfreport_path = tempfile.mkstemp(suffix='.pdf', prefix='order.tmp.')
                pdf = self.env['report'].get_pdf(order, 'is_plastigray.is_report_purchaseorder')
                f = open(pdfreport_path,'wb')
                f.write(pdf)
                f.close()
                paths.append(pdfreport_path)
            path_merged=self._merge_pdf(paths)
            pdfs = open(path_merged,'rb').read().encode('base64')

            #** Suppression des fiches temporaires *****************************
            os.unlink(path_merged)
            for path in paths:
                os.unlink(path)
            #*******************************************************************

            # ** Recherche si une pièce jointe est déja associèe ***************
            attachment_obj = self.env['ir.attachment']
            model=self._name
            #name='commandes.pdf'
            attachments = attachment_obj.search([('res_model','=',model),('res_id','=',obj.id),('name','=',name)])
            # ******************************************************************

            # ** Creation ou modification de la pièce jointe *******************
            vals = {
                'name':        name,
                'datas_fname': name,
                'type':        'binary',
                'res_model':   model,
                'res_id':      obj.id,
                'datas':       pdfs,
            }
            if attachments:
                for attachment in attachments:
                    attachment.write(vals)
                    attachment_id=attachment.id
            else:
                attachment = attachment_obj.create(vals)
                attachment_id=attachment.id
            return attachment_id
            #*******************************************************************

    @api.multi
    def print_ferme_uniquement(self):
        for obj in self:
            self.set_histo(obj.id, u'Impression commandes fermes uniquement')
            name='commandes-fermes.pdf'
            attachment_id=self.create_ferme_uniquement(name)
            return {
                'type' : 'ir.actions.act_url',
                'url': '/web/binary/saveas?model=ir.attachment&field=datas&id='+str(attachment_id)+'&filename_field=name',
                'target': 'new',
            }


    @api.multi
    def mail_ferme_uniquement(self):
        for obj in self:
            self.set_histo(obj.id, u'Envoi commandes fermes par mail à '+str(obj.contact_id.email))
            name='commandes-fermes.pdf'
            attachment_id=self.create_ferme_uniquement(name)
            subject=u"Commandes fermes Plastigray pour "+obj.partner_id.name;
            self.envoi_mail(name,subject)




    @api.multi
    def print_commande_ouverte(self):
        for obj in self:
            self.set_histo(obj.id, u'Impression commande ouverte')
        return self.env['report'].get_action(self, 'is_plastigray.report_cde_ouverte_fournisseur')



    @api.multi
    def mail_commande_ouverte(self):
        for obj in self:
            # ** Recherche si une pièce jointe est déja associèe ***************
            attachment_obj = self.env['ir.attachment']
            model=self._name
            name='commande-ouverte.pdf'
            attachments = attachment_obj.search([('res_model','=',model),('res_id','=',obj.id),('name','=',name)])
            # ******************************************************************

            # ** Creation ou modification de la pièce jointe *******************
            pdf = self.env['report'].get_pdf(obj, 'is_plastigray.report_cde_ouverte_fournisseur')
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
            subject=u"Commande ouverte Plastigray pour "+obj.partner_id.name;
            self.envoi_mail(name,subject)
            self.set_histo(obj.id, u'Envoi commande ouverte par mail à '+str(obj.contact_id.email))
            # ******************************************************************



    @api.multi
    def create_appel_de_livraison(self):
        for obj in self:
            #** Nom du document ************************************************
            if obj.type_commande=='ferme':
                name='horizon-des-besoins.pdf'
            else:
                name='appel-de-livraison.pdf'
            #*******************************************************************

            #** Génération du PDF de l'Horizon des besoins *********************
            pdf = self.env['report'].get_pdf(obj, 'is_plastigray.report_appel_de_livraison')
            #*******************************************************************

            #** Ajout des commandes fermes à l'horizon *************************
            attachment_obj = self.env['ir.attachment']
            if obj.type_commande=='ferme':
                paths=[]
                attachment_id=self.create_ferme_uniquement(name)
                attachment = attachment_obj.browse(attachment_id)
                pdfreport_id, pdfreport_path = tempfile.mkstemp(suffix='.pdf', prefix='order.tmp1.')
                f = open(pdfreport_path,'wb')
                f.write(attachment.datas.decode('base64'))
                f.close()
                paths.append(pdfreport_path)
                pdfreport_id, pdfreport_path = tempfile.mkstemp(suffix='.pdf', prefix='order.tmp2.')
                f = open(pdfreport_path,'wb')
                f.write(pdf)
                f.close()
                paths.append(pdfreport_path)
                path=self._merge_pdf(paths)
                pdf = open(path,'rb').read()
                os.unlink(path)
                for path in paths:
                    os.unlink(path)
            #*******************************************************************

            # ** Recherche si une pièce jointe est déja associèe ***************
            model=self._name
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
            return attachment_id
            #*******************************************************************


    @api.multi
    def print_appel_de_livraison(self):
        for obj in self:
            if obj.type_commande=='ferme':
                self.set_histo(obj.id, u'Impression horizon des besoins')
            else:
                self.set_histo(obj.id, u'Impression appel de livraison')
                name='appel-de-livraison.pdf'
            attachment_id=self.create_appel_de_livraison()
            return {
                'type' : 'ir.actions.act_url',
                'url': '/web/binary/saveas?model=ir.attachment&field=datas&id='+str(attachment_id)+'&filename_field=name',
                'target': 'new',
            }


    @api.multi
    def mail_appel_de_livraison(self):
        for obj in self:

            #** Nom du document et historique **********************************
            if obj.type_commande=='ferme':
                self.set_histo(obj.id, u'Envoi horizon des besoins par mail à '+str(obj.contact_id.email))
                subject=u"Horizon des besoins Plastigray pour "+obj.partner_id.name;
                name='horizon-des-besoins.pdf'
            else:
                self.set_histo(obj.id, u'Envoi appel de livraison par mail à '+str(obj.contact_id.email))
                subject=u"Appel de livraison Plastigray pour "+obj.partner_id.name;
                name='appel-de-livraison.pdf'
            #*******************************************************************

            attachment_id=self.create_appel_de_livraison()
            self.envoi_mail(name,subject)



    @api.multi
    def print_relance(self):
        for obj in self:
            self.set_histo(obj.id, u'Impression Relance fournisseur')
        return self.env['report'].get_action(self, 'is_plastigray.report_relance_fournisseur')


    @api.multi
    def mail_relance(self):
        for obj in self:
            # ** Recherche si une pièce jointe est déja associèe ***************
            attachment_obj = self.env['ir.attachment']
            model=self._name
            name='relance-fournisseur.pdf'
            attachments = attachment_obj.search([('res_model','=',model),('res_id','=',obj.id),('name','=',name)])
            # ******************************************************************

            # ** Creation ou modification de la pièce jointe *******************
            pdf = self.env['report'].get_pdf(obj, 'is_plastigray.report_relance_fournisseur')
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
            subject=u"Relance fournisseur Plastigray pour "+obj.partner_id.name;
            self.envoi_mail(name,subject)
            self.set_histo(obj.id, u'Envoi Relance fournisseur par mail à '+str(obj.contact_id.email))
            # ******************************************************************



    @api.multi
    def envoi_mail(self, name, subject):
        for obj in self:
            email_to=obj.contact_id.email
            if email_to==False:
                raise Warning(u"Mail non renseigné pour ce contact !")
            user  = self.env['res.users'].browse(self._uid)
            email = user.email
            nom   = user.name
            if email==False:
                raise Warning(u"Votre mail n'est pas renseigné !")
            if email:
                attachment_id = self.env['ir.attachment'].search([
                    ('res_model','=','is.cde.ouverte.fournisseur'),
                    ('res_id'   ,'=',obj.id),
                    ('name'     ,'=',name)
                ])
                email_vals = {}
                body_html=modele_mail.replace('[from]', nom)
                email_vals.update({
                    'subject'       : subject,
                    'email_to'      : email_to, 
                    'email_cc'      : email,
                    'email_from'    : email, 
                    'body_html'     : body_html.encode('utf-8'), 
                    'attachment_ids': [(6, 0, [attachment_id.id])] 
                })
                email_id=self.env['mail.mail'].create(email_vals)
                if email_id:
                    self.env['mail.mail'].send(email_id)


    @api.multi
    def set_histo(self, order_id, description):
        vals={
            'order_id': order_id,
            'description'  : description,
        }
        histo=self.env['is.cde.ouverte.fournisseur.histo'].create(vals)


    @api.multi
    def integrer_commandes(self):
        cr = self._cr
        for obj in self:
            self.set_histo(obj.id, u'Intégration des commandes et SA')
            for product in obj.product_ids:
                product.imprimer=False
            #** Recherche du contact logistique ********************************
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

            ##** Rechercher les tarifs *****************************************
            for tarif in obj.tarif_ids:
                tarif.unlink()
            for product in obj.product_ids:
                SQL="""
                    select ppi.sequence, ppi.min_quantity, ppi.price_surcharge
                    from product_pricelist_version ppv inner join product_pricelist_item ppi on ppv.id=ppi.price_version_id
                    where ppi.product_id="""+str(product.product_id.id)+""" 
                          and ppv.pricelist_id="""+str(obj.pricelist_id.id)+"""
                          and (ppv.date_end   is null or ppv.date_end   >= CURRENT_DATE) 
                          and (ppv.date_start is null or ppv.date_start <= CURRENT_DATE) 
                          and (ppi.date_end   is null or ppi.date_end   >= CURRENT_DATE) 
                          and (ppi.date_start is null or ppi.date_start <= CURRENT_DATE) 
                    order by ppi.sequence
                """
                cr.execute(SQL)
                result = cr.fetchall()
                for row in result:
                    vals={
                        'order_id'  : obj.id,
                        'product_id': product.product_id.id,
                        'sequence'  : row[0],
                        'minimum'   : row[1],
                        'prix_achat': row[2],
                    }
                    line=self.env['is.cde.ouverte.fournisseur.tarif'].create(vals)
            #*******************************************************************

            #** Recherche du dernier numéro de BL ******************************
            for product in obj.product_ids:
                SQL="""
                    select sp.is_num_bl, sp.is_date_reception, sm.product_uom_qty
                    from stock_picking sp inner join stock_move sm on sm.picking_id=sp.id
                    where 
                        sm.product_id="""+str(product.product_id.id)+""" and
                        sp.is_date_reception is not null and
                        sm.state='done' and
                        sp.picking_type_id=1 and 
                        sp.partner_id="""+str(obj.partner_id.id)+""" 
                    order by sp.is_date_reception desc, sm.date desc
                    limit 1
                """
                cr.execute(SQL)
                result = cr.fetchall()
                num_bl  = False
                date_bl = False
                qt_bl   = 0
                for row in result:
                    num_bl  = row[0]
                    date_bl = row[1]
                    qt_bl   = row[2]

                product.num_bl  = num_bl
                product.date_bl = date_bl
                product.qt_bl   = qt_bl
            #*******************************************************************

            for product in obj.product_ids:
                product.line_ids.unlink()

            attente_confirmation_total=0
            for product in obj.product_ids:
                if obj.type_commande!='ferme_uniquement':
                    where=[
                        ('type'      , '=' ,'sa'),
                        ('product_id', '=' ,product.product_id.id),
                        ('partner_id', '=' , obj.partner_id.id), 
                    ]
                    for row in self.env['mrp.prevision'].search(where):
                        vals={
                            'product_id'       : product.id,
                            'date'             : row.start_date_cq or row.end_date,
                            'type_cde'         : 'prev',
                            'quantite'         : row.quantity_ha,
                            'uom_id'           : row.uom_po_id.id,
                            'mrp_prevision_id' : row.id,
                        }
                        line=self.env['is.cde.ouverte.fournisseur.line'].create(vals)
                where=[
                    ('state'       ,'=', 'confirmed'),
                    ('product_id'  ,'=', product.product_id.id),
                    ('partner_id'  ,'=', obj.partner_id.id), 
                ]
                now  = datetime.date.today()                      # Date du jour
                #date_approve = now + datetime.timedelta(days=-7) # Date -7 jours
                date_approve = now + datetime.timedelta(days=-3)  # Date -3 jours : TODO Passage de 7 à 3 jours le 28/04/2017
                date_approve = date_approve.strftime('%Y-%m-%d')
                nb_ferme_imprime=0
                attente_confirmation=0
                for row in self.env['purchase.order.line'].search(where):
                    #** Test si réceptions en cours sur la ligne de cde ********
                    where=[
                        ('purchase_line_id','=', row.id),
                        ('state'           ,'not in', ('done','cancel')),
                    ]
                    moves=self.env['stock.move'].search(where)
                    #***********************************************************
                    if len(moves)>0:
                        #if row.order_id.date_approve>date_approve or obj.type_commande=='ouverte':
                        imprimer_commande=False
                        if row.order_id.date_approve>date_approve:
                            imprimer_commande=True
                            nb_ferme_imprime=nb_ferme_imprime+1

                        if row.order_id.is_date_confirmation is False:
                            attente_confirmation       = attente_confirmation+1
                            attente_confirmation_total = attente_confirmation_total+1

                        #** Recherche Qt réceptionnée sur cette commande *******
                        where=[
                            ('purchase_line_id','=', row.id),
                            ('state'           ,'=', 'done'),
                        ]
                        moves=self.env['stock.move'].search(where)
                        quantite_rcp=0
                        for move in moves:
                            quantite_rcp=quantite_rcp+move.product_uom_qty
                        #*******************************************************

                        vals={
                            'product_id'        : product.id,
                            'date'              : row.date_planned,
                            'date_approve'      : row.order_id.date_approve,
                            'type_cde'          : 'ferme',
                            'quantite'          : row.product_qty,
                            'quantite_rcp'      : quantite_rcp,
                            'uom_id'            : row.product_uom.id,
                            'purchase_order_id' : row.order_id.id,
                            'date_fournisseur'  : row.order_id.is_date_confirmation,
                            'imprimer_commande' : imprimer_commande,
                        }
                        line=self.env['is.cde.ouverte.fournisseur.line'].create(vals)
                product.nb_ferme_imprime=nb_ferme_imprime
                product.nb_commandes=len(product.line_ids)
                product.attente_confirmation=attente_confirmation
            obj.attente_confirmation=attente_confirmation_total


class is_cde_ouverte_fournisseur_product(models.Model):
    _name='is.cde.ouverte.fournisseur.product'
    _order='product_id'

    order_id             = fields.Many2one('is.cde.ouverte.fournisseur', 'Commande ouverte fournisseur', required=True, ondelete='cascade', readonly=True)
    product_id           = fields.Many2one('product.product', 'Article'  , required=True)
    num_bl               = fields.Char("Dernier BL"     , readonly=True)
    date_bl              = fields.Date("Date BL"        , readonly=True)
    qt_bl                = fields.Float("Qt reçue"      , readonly=True)
    nb_ferme_imprime     = fields.Integer("Nb fermes à imprimer", readonly=True)
    nb_commandes         = fields.Integer("Nb commandes"        , readonly=True)
    imprimer             = fields.Boolean("A imprimer", help="Si cette case n'est pas cochée, l'article ne sera pas imprimé")
    attente_confirmation = fields.Integer("Attente confirmation fournisseur", readonly=True)
    line_ids             = fields.One2many('is.cde.ouverte.fournisseur.line'   , 'product_id', u"Commandes")


    @api.multi
    def action_acces_commandes(self):
        for obj in self:
            return {
                'name': u'Commandes',
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'is.cde.ouverte.fournisseur.product',
                'res_id'   : obj.id,
                'type'     : 'ir.actions.act_window',
            }






class is_cde_ouverte_fournisseur_tarif(models.Model):
    _name='is.cde.ouverte.fournisseur.tarif'
    _order='product_id, sequence'

    order_id      = fields.Many2one('is.cde.ouverte.fournisseur', 'Commande ouverte fournisseur', required=True, ondelete='cascade', readonly=True)
    product_id    = fields.Many2one('product.product', 'Article'  , required=True)
    sequence      = fields.Integer("Séquence")
    minimum       = fields.Float("Minimum")
    prix_achat    = fields.Float("Prix d'achat")
    uom_po_id     = fields.Many2one('product.uom', "Unité d'achat", related='product_id.uom_po_id', readonly=True)


class is_cde_ouverte_fournisseur_line(models.Model):
    _name='is.cde.ouverte.fournisseur.line'
    _order='date'

    product_id        = fields.Many2one('is.cde.ouverte.fournisseur.product', 'Commande ouverte fournisseur', required=True, ondelete='cascade', readonly=True)
    date              = fields.Date("Date Commande")
    date_approve      = fields.Date("Date de confirmation")
    type_cde          = fields.Selection([('ferme', u'Ferme'),('prev', u'Prévisionnel')], u"Type de commande", select=True)
    quantite          = fields.Float("Quantité commande")
    quantite_rcp      = fields.Float("Quantité reçue")
    uom_id            = fields.Many2one('product.uom', 'Unité')
    mrp_prevision_id  = fields.Many2one('mrp.prevision' , 'SA')
    purchase_order_id = fields.Many2one('purchase.order', 'Commande')
    date_fournisseur  = fields.Date("Date confirmation fournisseur")
    imprimer_commande = fields.Boolean("Imprimer la commande", default=False)





class is_cde_ouverte_fournisseur_histo(models.Model):
    _name='is.cde.ouverte.fournisseur.histo'
    _order='name desc'

    order_id    = fields.Many2one('is.cde.ouverte.fournisseur', 'Commande ouverte fournisseur', required=True, ondelete='cascade', readonly=True)
    name        = fields.Datetime("Date")
    user_id     = fields.Many2one('res.users', 'Utilisateur')
    description = fields.Char("Opération éffectuée")

    _defaults = {
        'name'   : lambda *a: fields.datetime.now(),
        'user_id': lambda obj, cr, uid, context: uid,
    }


