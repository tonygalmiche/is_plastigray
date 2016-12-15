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

#TODO : 
# - Ajouter le bouton pour envouer par mail
# - Ajouter un tableau pour avoir l'historique des actions
# - Pour les commandes fermes, tenir compte de la date de validation => Ne pas envoyer les commandes validées de plus de 7 jours


type_commande_list=[
    ('ouverte'         , 'Commande ouverte'),
    ('ferme'           , 'Commande ferme avec horizon'),
    ('ferme_uniquement', 'Commande ferme uniquement')
]

class is_cde_ouverte_fournisseur(models.Model):
    _name='is.cde.ouverte.fournisseur'
    _order='partner_id'

    name          = fields.Char("N°", readonly=True)
    partner_id    = fields.Many2one('res.partner', 'Fournisseur'        , required=True)
    pricelist_id  = fields.Many2one('product.pricelist', 'Liste de prix', related='partner_id.property_product_pricelist_purchase', readonly=True)
    type_commande = fields.Selection(type_commande_list, "Type de commande", required=True)
    sans_commande = fields.Selection([('oui', 'Oui'),('non', 'Non')], "Articles sans commandes", help="Imprimer dans les documents les articles sans commandes")
    commentaire   = fields.Text("Commentaire")
    product_ids   = fields.One2many('is.cde.ouverte.fournisseur.product', 'order_id', u"Articles")
    tarif_ids     = fields.One2many('is.cde.ouverte.fournisseur.tarif'  , 'order_id', u"Tarifs")

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
    def print_commande_ouverte(self):
        return self.env['report'].get_action(self, 'is_plastigray.report_cde_ouverte_fournisseur')


    @api.multi
    def print_appel_de_livraison(self):
        return self.env['report'].get_action(self, 'is_plastigray.report_appel_de_livraison')


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
    def print_ferme_uniquement(self):
        for obj in self:
            orders=[]
            for product in self.env['is.cde.ouverte.fournisseur.product'].search([('order_id','=',obj.id)]):
                for line in self.env['is.cde.ouverte.fournisseur.line'].search([('product_id','=',product.id)]):
                    order=line.purchase_order_id
                    if not order in orders:
                        orders.append(order)
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
            name='commandes.pdf'
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
            #*******************************************************************

            return {
                'type' : 'ir.actions.act_url',
                'url': '/web/binary/saveas?model=ir.attachment&field=datas&id='+str(attachment_id)+'&filename_field=name',
                'target': 'self',
            }






    @api.multi
    def integrer_commandes(self):
        cr = self._cr
        for obj in self:



            for product in obj.product_ids:
                product.imprimer=False

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
                    where sm.product_id="""+str(product.product_id.id)+""" 
                          and sp.is_date_reception is not null
                          and sm.state='done' 
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
            for product in obj.product_ids:


                if obj.type_commande!='ferme_uniquement':
                    for row in self.env['mrp.prevision'].search([('type','=','sa'),('product_id','=',product.product_id.id)]):
                        vals={
                            'product_id'       : product.id,
                            'date'             : row.end_date,
                            'type_cde'         : 'prev',
                            'quantite'         : row.quantity,
                            'mrp_prevision_id' : row.id,
                        }
                        line=self.env['is.cde.ouverte.fournisseur.line'].create(vals)


                now  = datetime.date.today()                     # Date du jour
                date_approve = now + datetime.timedelta(days=-7) # Date -7 jours
                date_approve = date_approve.strftime('%Y-%m-%d')   # Formatage


                where=[
                    ('state'       ,'=', 'confirmed'),
                    ('product_id'  ,'=', product.product_id.id),
                    ('order_id.date_approve','>', date_approve)
                ]
                print where
                for row in self.env['purchase.order.line'].search(where):
                    vals={
                        'product_id'        : product.id,
                        'date'              : row.date_planned,
                        'type_cde'          : 'ferme',
                        'quantite'          : row.product_qty,
                        'purchase_order_id' : row.order_id.id,
                    }
                    line=self.env['is.cde.ouverte.fournisseur.line'].create(vals)



class is_cde_ouverte_fournisseur_product(models.Model):
    _name='is.cde.ouverte.fournisseur.product'
    _order='product_id'

    order_id      = fields.Many2one('is.cde.ouverte.fournisseur', 'Commande ouverte fournisseur', required=True, ondelete='cascade', readonly=True)
    product_id    = fields.Many2one('product.product', 'Article'  , required=True)
    num_bl        = fields.Char("Dernier BL", readonly=True)
    date_bl       = fields.Date("Date BL"   , readonly=True)
    qt_bl         = fields.Float("Qt reçue" , readonly=True)
    imprimer      = fields.Boolean("A imprimer", help="Si cette case n'est pas cochée, l'article ne sera pas imprimé")
    line_ids      = fields.One2many('is.cde.ouverte.fournisseur.line'   , 'product_id', u"Commandes")


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
    type_cde          = fields.Selection([('ferme', u'Ferme'),('prev', u'Prévisionnel')], u"Type de commande", select=True)
    quantite          = fields.Float("Quantité")
    mrp_prevision_id  = fields.Many2one('mrp.prevision' , 'SA')
    purchase_order_id = fields.Many2one('purchase.order', 'Commande')




