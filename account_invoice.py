# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp import SUPERUSER_ID
from openerp.tools.translate import _
from openerp.exceptions import Warning
import time
from datetime import date, datetime
from ftplib import FTP
import os
import tempfile
from pyPdf import PdfFileWriter, PdfFileReader
from contextlib import closing
import logging
_logger = logging.getLogger(__name__)


modele_mail=u"""
<html>
    <head>
        <meta content="text/html; charset=UTF-8" http-equiv="Content-Type">
    </head>
    <body>
        <font>Bonjour, </font>
        <br><br>
        <font> Veuillez trouver ci-joint notre facture.</font>
        <br><br>
        Cordialement <br><br>
        [from]<br>
    </body>
</html>
"""


class is_account_folio(models.Model):
    _name  = 'is.account.folio'
    _order = 'name desc'

    name          = fields.Char('N° de Folio'              , readonly=True)
    date_creation = fields.Date("Date de création"         , readonly=True)
    createur_id   = fields.Many2one('res.users', 'Créé par', readonly=True)
    invoice_ids   = fields.One2many('account.invoice', 'is_folio_id', 'Factures', readonly=True)

    def _date_creation():
        return date.today() # Date du jour

    _defaults = {
        'date_creation': _date_creation(),
        'createur_id': lambda obj, cr, uid, ctx=None: uid,
    }


    @api.model
    def create(self, vals):
        data_obj = self.env['ir.model.data']
        sequence_ids = data_obj.search([('name','=','seq_is_account_folio')])
        if len(sequence_ids)>0:
            sequence_id = sequence_ids[0].res_id
            vals['name'] = self.env['ir.sequence'].get_id(sequence_id, 'id')
        res = super(is_account_folio, self).create(vals)
        return res


class account_move_line(models.Model):
    _inherit = "account.move.line"
    is_account_invoice_line_id = fields.Many2one('account.invoice.line', 'Ligne de facture')


class account_invoice(models.Model):
    _inherit = 'account.invoice'
    _order   = 'id desc'

    is_document        = fields.Char('Document'     , help="Ce champ est utilisé dans les factures diverses pour saisir le moule ou le n° d'investissement")
    is_num_cde_client  = fields.Char('N° Cde Client', help="Ce champ est utilisé dans les factures diverses sans commande client dans Odoo")
    is_num_bl_manuel   = fields.Char('N° BL manuel' , help="Ce champ est utilisé dans les factures diverses sans bon de livraison dans Odoo")
    is_escompte        = fields.Float("Escompte", compute='_compute')
    is_tva             = fields.Float("TVA"     , compute='_compute', help="Taxes sans l'escompte")
    is_folio_id        = fields.Many2one('is.account.folio', 'Folio')
    is_export_cegid_id = fields.Many2one('is.export.cegid' , 'Folio Cegid')
    is_bon_a_payer     = fields.Boolean("Bon à payer", default=True)
    is_type_facture    = fields.Selection([
            ('standard'  , u'Standard'),
            ('diverse'   , u'Diverse'),
            ('avoir-qt'  , u'Avoir quantité'),
            ('avoir-prix', u'Avoir prix'),
        ], u"Type de facture", default='standard', select=True)
    is_origine_id     = fields.Many2one('account.invoice', "Facture d'origine")
    is_mode_envoi_facture = fields.Selection([
        ('courrier'        , 'Envoi par courrier'),
        ('courrier2'       , 'Envoi par courrier en double exemplaire'),
        ('mail'            , 'Envoi par mail (1 mail par facture)'),
        ('mail2'           , 'Envoi par mail (1 mail par facture en double exemplaire)'),
        ('mail_client'     , 'Envoi par mail (1 mail par client)'),
        ('mail_client_bl'  , 'Envoi par mail avec BL (1 mail par client)'),
        ('mail_regroupe_bl', 'Regroupement des BL sur une même facture et envoi par mail'),
    ], "Mode d'envoi de la facture")
    is_date_envoi_mail = fields.Datetime("Mail envoyé le", readonly=False)
    is_masse_nette     = fields.Float("Masse nette (Kg)")

    def _compute(self):
        for obj in self:
            escompte = tva = 0
            for tax in obj.tax_line:
                if tax.account_id.code=='665000':
                    escompte=escompte+tax.amount
                else:
                    tva=tva++tax.amount
            obj.is_escompte = escompte
            obj.is_tva      = tva


    @api.multi
    def copy(self,vals):
        vals['is_folio_id'] = False
        vals['is_export_cegid_id'] = False
        res=super(account_invoice, self).copy(vals)
        return res


    @api.multi
    def voir_facture_client_action(self):
        for obj in self:
            view_id=self.env.ref('is_plastigray.is_invoice_form')
            res= {
                'name': 'Facture Client',
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'account.invoice',
                'res_id': obj.id,
                'view_id': view_id.id,
                'type': 'ir.actions.act_window',
                'context': {'default_type':'out_invoice', 'type':'out_invoice', 'journal_type': 'sale'},
                'domain': [('type','=','out_invoice'),('journal_type','=','sale')],
            }
            return res


    @api.multi
    def voir_facture_fournisseur_action(self):
        for obj in self:
            view_id=self.env.ref('is_plastigray.is_invoice_supplier_form')
            res= {
                'name': 'Facture Client',
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'account.invoice',
                'res_id': obj.id,
                'view_id': view_id.id,
                'type': 'ir.actions.act_window',
                'context': {'default_type':'in_invoice', 'type':'in_invoice'},
                'domain': [('type','=','in_invoice')],
            }
            return res


    @api.multi
    def invoice_print(self):
        assert len(self) == 1, 'This option should only be used for a single id at a time.'
        self.sent = True
        res = self.env['report'].get_action(self, 'is_plastigray.is_report_invoice')
        return res


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
    def imprimer_simple_double(self):
        """Imprimer en simple ou double exemplaire"""
        cr , uid, context = self.env.args
        db = self._cr.dbname
        path="/tmp/factures-" + db + '-'+str(uid)
        cde="rm -Rf " + path
        os.popen(cde).readlines()
        if not os.path.exists(path):
            os.makedirs(path)

        nb=len(self)
        ct=1
        paths=[]
        for obj in self:
            msg = str(ct)+'/'+str(nb)+' - Imprimer en simple ou double exemplaire : '+str(obj.number)
            _logger.info(msg)
            ct+=1
            result = self.env['report'].get_pdf(obj, 'is_plastigray.is_report_invoice')
            r = range(1, 2)
            if obj.is_mode_envoi_facture=='courrier2':
                r = range(1, 3)
            for x in r:
                file_name = path + '/'+str(obj.number) + '-' + str(x) + '.pdf'
                fd = os.open(file_name,os.O_RDWR|os.O_CREAT)
                try:
                    os.write(fd, result)
                finally:
                    os.close(fd)
                paths.append(file_name)


        # ** Merge des PDF *****************************************************
        path_merged=self._merge_pdf(paths)
        pdfs = open(path_merged,'rb').read().encode('base64')
        # **********************************************************************


        # ** Recherche si une pièce jointe est déja associèe *******************
        attachment_obj = self.env['ir.attachment']
        name = 'factures-' + db + '-' + str(uid) + '.pdf'
        attachments = attachment_obj.search([('name','=',name)],limit=1)
        # **********************************************************************


        # ** Creation ou modification de la pièce jointe ***********************
        vals = {
            'name':        name,
            'datas_fname': name,
            'type':        'binary',
            'datas':       pdfs,
        }
        if attachments:
            for attachment in attachments:
                attachment.write(vals)
                attachment_id=attachment.id
        else:
            attachment = attachment_obj.create(vals)
            attachment_id=attachment.id
        #***********************************************************************

        #** Envoi du PDF mergé dans le navigateur ******************************
        if attachment_id:
            return {
                'type' : 'ir.actions.act_url',
                'url': '/web/binary/saveas?model=ir.attachment&field=datas&id='+str(attachment_id)+'&filename_field=name',
                'target': 'new',
            }
        #***********************************************************************


    @api.multi
    def envoi_par_mail(self):
        """Envoi du mail directement sans passer par le wizard"""
        cr , uid, context = self.env.args
        if not self.pool['res.users'].has_group(cr, uid, 'is_plastigray.is_comptable_group'):
            raise Warning(u"Accès non autorisé !")
        ids=[]
        for obj in self:
            ids.append(str(obj.id))
        if len(ids)>0:
            SQL="""
                select ai.is_mode_envoi_facture, ai.partner_id, ai.name, ai.id
                from account_invoice ai
                where 
                    ai.id in("""+','.join(ids)+""")  and 
                    ai.is_date_envoi_mail is null and 
                    ai.is_mode_envoi_facture like 'mail%'
                order by ai.is_mode_envoi_facture, ai.partner_id, ai.name
            """
            cr.execute(SQL)
            result = cr.fetchall()

            # ** Un mail par client*********************************************
            partners={}
            for row in result:
                if row[0]=='mail_client':
                    partner_id = row[1]
                    id         = row[3]
                    if not partner_id in partners:
                        partners[partner_id]=[]
                    partners[partner_id].append(id)
            #*******************************************************************


            # ** Un mail+BL par client******************************************
            for row in result:
                if row[0]=='mail_client_bl':
                    partner_id = row[1]
                    id         = row[3]
                    if not partner_id in partners:
                        partners[partner_id]=[]
                    partners[partner_id].append(id)
            #*******************************************************************


            #** Envoi des mails par partner ************************************
            for partner_id in partners:
                ids=partners[partner_id]
                self._envoi_par_mail(partner_id, ids)
            #*******************************************************************


            # ** Un mail par facture *******************************************
            for row in result:
                if row[0] in ['mail', 'mail_regroupe_bl']:
                    partner_id = row[1]
                    id         = row[3]
                    self._envoi_par_mail(partner_id, [id])
            #*******************************************************************


            # ** Un mail par facture en double exemplaire **********************
            for row in result:
                if row[0]=='mail2':
                    partner_id = row[1]
                    id         = row[3]
                    self._envoi_par_mail(partner_id, [id])
            #*******************************************************************




    @api.multi
    def _envoi_par_mail(self, partner_id, ids):
        cr , uid, context = self.env.args
        user = self.env['res.users'].browse(self._uid)
        if user.email==False:
            raise Warning(u"Votre mail n'est pas renseigné !")
        attachment_ids=[]
        for id in ids:
            invoice = self.env['account.invoice'].browse(id)
            attachments = self.env['ir.attachment'].search([
                ('res_model','=','account.invoice'),
                ('res_id'   ,'=',id),
            ], order='id desc', limit=1)
            if len(attachments)==0:
                raise Warning(u"Facture "+invoice.number+" non générée (non imprimée) !")

            for attachment in attachments:
                if invoice.is_mode_envoi_facture=='mail2':
                    # ** Duplication de la facture + fusion ********************
                    db = self._cr.dbname
                    path="/tmp/factures-" + db + '-'+str(uid)
                    cde="rm -Rf " + path
                    os.popen(cde).readlines()
                    if not os.path.exists(path):
                        os.makedirs(path)
                    paths=[]
                    for x in range(1, 3):
                        file_name = path + '/'+str(invoice.number) + '-' + str(x) + '.pdf'
                        fd = os.open(file_name,os.O_RDWR|os.O_CREAT)
                        try:
                            os.write(fd, attachment.datas.decode('base64'))
                        finally:
                            os.close(fd)
                        paths.append(file_name)
                    # ** Merge des PDF *****************************************
                    path_merged=self._merge_pdf(paths)
                    pdfs = open(path_merged,'rb').read().encode('base64')
                    # **********************************************************


                    # ** Création d'une piece jointe fusionnée *****************
                    name = 'facture-' + str(invoice.number) + '-' + str(uid) + '.pdf'
                    vals = {
                        'name':        name,
                        'datas_fname': name,
                        'type':        'binary',
                        'datas':       pdfs,
                    }
                    new = self.env['ir.attachment'].create(vals)
                    attachment_id=new.id
                    #***********************************************************
                else:
                    attachment_id=attachment.id

                attachment_ids.append(attachment_id)


        partner = self.env['res.partner'].browse(partner_id)
        if partner.is_mode_envoi_facture=='mail_client_bl':
            attachment_obj = self.env['ir.attachment']
            for id in ids:
                invoice = self.env['account.invoice'].browse(id)
                for line in invoice.invoice_line:
                    picking=line.is_move_id.picking_id

                    # ** Recherche si une pièce jointe est déja associèe au bl *
                    model='stock.picking'
                    name='BL-'+picking.name+u'.pdf'
                    attachments = attachment_obj.search([('res_model','=',model),('res_id','=',picking.id),('name','=',name)])
                    # **********************************************************

                    # ** Creation ou modification de la pièce jointe *******************
                    pdf = self.env['report'].get_pdf(picking, 'stock.report_picking')
                    vals = {
                        'name':        name,
                        'datas_fname': name,
                        'type':        'binary',
                        'res_model':   model,
                        'res_id':      picking.id,
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

                    if attachment_id not in attachment_ids:
                        attachment_ids.append(attachment_id)


        #** Recherche du contact Facturation *******************************
        SQL="""
            select rp.name, rp.email, rp.active
            from res_partner rp inner join is_type_contact itc on rp.is_type_contact=itc.id
            where 
                rp.parent_id="""+str(partner_id)+""" and 
                itc.name='Facturation' and
                rp.active='t'
        """
        cr.execute(SQL)
        result = cr.fetchall()
        emails_to=[]
        for row in result:
            email_to = str(row[1])
            if email_to=='None':
                raise Warning(u"Mail du contact de facturation non renseigné pour le client "+partner.is_code+u'/'+partner.is_adr_code+" !")
            emails_to.append(row[0]+u' <'+email_to+u'>')
        if len(emails_to)==0:
            raise Warning(u"Aucun contact de type 'Facturation' trouvé pour le client "+partner.is_code+u'/'+partner.is_adr_code+" !")
        #*******************************************************************

        email_cc   = user.name+u' <'+user.email+u'>'
        email_to   = u','.join(emails_to)
        #email_to   = email_cc
        email_from = email_cc
        subject    = u'Facture Plastigray pour '+partner.name
        #subject    = u'Facture Plastigray pour '+partner.name+u' ('+u','.join(emails_to)+u')'
        email_vals = {}
        body_html=modele_mail.replace('[from]', user.name)
        email_vals.update({
            'subject'       : subject,
            'email_to'      : email_to,
            'email_cc'      : email_cc,
            'email_from'    : email_from, 
            'body_html'     : body_html.encode('utf-8'), 
            'attachment_ids': [(6, 0, [attachment_ids])] 
        })
        email_id=self.env['mail.mail'].create(email_vals)
        if email_id:
            self.env['mail.mail'].send(email_id)
        email_to   = u','.join(emails_to)
        for id in ids:
            invoice = self.env['account.invoice'].browse(id)
            invoice.message_post(body=subject+u' envoyée par mail à '+u','.join(emails_to))
            invoice.is_date_envoi_mail=datetime.now()


    @api.multi
    def action_move_create(self):
        for obj in self:
            if obj.is_mode_envoi_facture==False:
                obj.is_mode_envoi_facture=obj.partner_id.is_mode_envoi_facture
        super(account_invoice, self).action_move_create()
        self.escompte()


    @api.multi
    def action_cancel(self):
        for obj in self:
            if obj.type=='in_invoice':
                for line in obj.invoice_line:
                    if line.is_move_id:
                        line.is_move_id.invoice_state='none'
                    line.is_move_id=False
        super(account_invoice, self).action_cancel()


    @api.multi
    def button_reset_taxes(self):
        res=super(account_invoice, self).button_reset_taxes()
        self.escompte()
        return res


    @api.multi
    def escompte(self):
        for obj in self:
            #Suppression des lignes d'escomptes
            for l in obj.tax_line:
                if l.name=='Escompte' or l.name=='TVA sur escompte':
                    l.unlink()
            if obj.partner_id.is_escompte:
                #Recherche du total HT
                ht=0.0
                tax_id=False
                for l in obj.invoice_line:
                    ht=ht+l.price_subtotal
                    if l.invoice_line_tax_id:
                        tax_id=l.invoice_line_tax_id[0]
                #Escompte
                tax_obj = self.env['account.invoice.tax']
                taux=obj.partner_id.is_escompte.taux/100
                tax_vals={
                    'invoice_id': obj.id,
                    'name': 'Escompte',
                    'account_id': obj.partner_id.is_escompte.compte.id,
                    'base': ht,
                    'amount': -ht*taux
                }
                tax_obj.create(tax_vals)
                #TVA sur Escompte
                if tax_id:
                    tax_vals={
                        'invoice_id': obj.id,
                        'name': 'TVA sur escompte',
                        'account_id': tax_id.account_collected_id.id,
                        'base': ht*taux,
                        'amount': -ht*taux*tax_id.amount
                    }
                    tax_obj.create(tax_vals)


    @api.model
    def line_get_convert(self, line, part, date):
        '''
        Permet d'ajouter dans la table account_move_line le lien vers la ligne de facture,
        pour récupérer en particulier la section analytique
        '''
        res=super(account_invoice, self).line_get_convert(line, part, date)
        res['is_account_invoice_line_id']=line.get('invl_id', False)
        return res


    @api.model
    def _prepare_refund(self, invoice, date=None, period_id=None, description=None, journal_id=None):
        """
        Permet d'ajouter les champs personnalisés de la facture sur l'avoir
        """
        res=super(account_invoice, self)._prepare_refund(invoice, date, period_id, description, journal_id)
        res['is_document']=invoice.is_document
        res['is_num_cde_client']=invoice.is_num_cde_client
        res['is_num_bl_manuel']=invoice.is_num_bl_manuel
        res['supplier_invoice_number']=invoice.supplier_invoice_number
        return res


class account_invoice_line(models.Model):
    _inherit = "account.invoice.line"

    is_section_analytique_id = fields.Many2one('is.section.analytique', 'Section analytique')
    is_move_id               = fields.Many2one('stock.move', 'Mouvement de stock', select=True)
    is_document              = fields.Char("N° du chantier")



    @api.depends('invoice_id.state')
    def _compute_amortissement_moule(self):
        cr = self._cr
        for obj in self:
            amortissement_moule = 0
            amt_interne = 0
            cagnotage = 0
            montant_amt_moule = 0
            montant_amt_interne = 0
            montant_cagnotage = 0
            montant_matiere = 0
            if obj.product_id and obj.quantity and obj.invoice_id and obj.invoice_id.partner_id and obj.invoice_id.date_invoice:
                SQL="""
                    SELECT
                        get_amortissement_moule_a_date(rp.is_code, pt.id, ai.date_invoice) as amortissement_moule,
                        get_amt_interne_a_date(rp.is_code, pt.id, ai.date_invoice) as amt_interne,
                        get_cagnotage_a_date(rp.is_code, pt.id, ai.date_invoice) as cagnotage,
                        fsens(ai.type)*get_amortissement_moule_a_date(rp.is_code, pt.id, ai.date_invoice)*ail.quantity as montant_amt_moule,
                        fsens(ai.type)*get_amt_interne_a_date(rp.is_code, pt.id, ai.date_invoice)*ail.quantity as montant_amt_interne,
                        fsens(ai.type)*get_cagnotage_a_date(rp.is_code, pt.id, ai.date_invoice)*ail.quantity as montant_cagnotage,
                        fsens(ai.type)*get_cout_act_matiere_st(pp.id)*ail.quantity as montant_matiere,
                        ai.date_invoice,
                        ai.state
                    from account_invoice ai inner join account_invoice_line ail on ai.id=ail.invoice_id
                                            inner join product_product       pp on ail.product_id=pp.id
                                            inner join product_template      pt on pp.product_tmpl_id=pt.id
                                            inner join res_partner           rp on ai.partner_id=rp.id
                    where ail.id=%s
                """
                cr.execute(SQL,[obj.id])
                res_ids = cr.fetchall()
                for res in res_ids:
                    amortissement_moule = res[0]
                    amt_interne         = res[1]
                    cagnotage           = res[2]
                    montant_amt_moule   = res[3]
                    montant_amt_interne = res[4]
                    montant_cagnotage   = res[5]
                    montant_matiere     = res[6]
            obj.is_amortissement_moule = amortissement_moule
            obj.is_amt_interne         = amt_interne
            obj.is_cagnotage           = cagnotage
            obj.is_montant_amt_moule   = montant_amt_moule
            obj.is_montant_amt_interne = montant_amt_interne
            obj.is_montant_cagnotage   = montant_cagnotage
            obj.is_montant_matiere     = montant_matiere


    is_amortissement_moule = fields.Float('Amt client négocié'        , digits=(14,4), store=True, compute='_compute_amortissement_moule')
    is_amt_interne         = fields.Float('Amt interne'               , digits=(14,4), store=True, compute='_compute_amortissement_moule')
    is_cagnotage           = fields.Float('Cagnotage'                 , digits=(14,4), store=True, compute='_compute_amortissement_moule')
    is_montant_amt_moule   = fields.Float('Montant amt client négocié', digits=(14,2), store=True, compute='_compute_amortissement_moule')
    is_montant_amt_interne = fields.Float('Montant amt interne'       , digits=(14,2), store=True, compute='_compute_amortissement_moule')
    is_montant_cagnotage   = fields.Float('Montant cagnotage'         , digits=(14,2), store=True, compute='_compute_amortissement_moule')
    is_montant_matiere     = fields.Float('Montant matière livrée'    , digits=(14,2), store=True, compute='_compute_amortissement_moule')


    @api.multi
    def product_id_change(self, product_id, uom_id, qty=0, name='', type='out_invoice',
            partner_id=False, fposition_id=False, price_unit=False, currency_id=False,
            company_id=None):

        #** Recherche lot pour retrouver le prix *******************************
        partner = self.env['res.partner'].browse(partner_id)
        lot_livraison=0
        is_section_analytique_id=False
        if product_id:
            product = self.env['product.product'].browse(product_id)
            lot_livraison=self.env['product.template'].get_lot_livraison(product.product_tmpl_id,partner)
            is_section_analytique_id=product.is_section_analytique_id.id
            if type=='in_invoice':
                is_section_analytique_id=product.is_section_analytique_ha_id.id
        #***********************************************************************

        res=super(account_invoice_line, self).product_id_change(product_id, uom_id, lot_livraison, name, type,
            partner_id, fposition_id, price_unit, currency_id,company_id)
        res['value']['is_section_analytique_id']=is_section_analytique_id

        #** Recherche prix dans liste de prix pour la date et qt ***************
        pricelist = partner.property_product_pricelist.id
        if product_id:
            date = time.strftime('%Y-%m-%d',time.gmtime()) # Date du jour
            if pricelist:
                ctx = dict(
                    self._context,
                    uom=uom_id,
                    date=date,
                )
                price_unit = self.pool.get('product.pricelist').price_get(self._cr, self._uid, [pricelist],
                        product_id, lot_livraison or 1.0, partner_id, ctx)[pricelist]
            res['value']['price_unit']=price_unit
        #***********************************************************************

        #** Ajout du code_pg dans la description *******************************
        if product_id:
            product = self.env['product.product'].browse(product_id)
            res['value']['name']=product.is_code+u' '+product.name

        return res


