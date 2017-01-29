# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning
import datetime
import time

import base64
import tempfile
import os
from pyPdf import PdfFileWriter, PdfFileReader
from contextlib import closing



# TODO
# Ajouter la catégorie, le gestionnaire, le moule, l'unité et le lot d'appro
# Calculer les gammes MO et Mach en même temps que les nomenclatures
# Voir pour optiiser le temps de traitement et afficher des informations de temps (en console)
# Voir pour mettre des liens vers les artciles dans la liste des composants (et vers les nomenclatures)
# Voir pour mettre la liste des articles dans l'ordre des codes et non pas des intitulés
# Pour le prix d'achat, il faudrait récupérer le prix correspond au lot et non pas le premier trouvé
# Ajouter un champ pour mettre le temps de calcul
# Voir pour lancer le calcul en tache de fond et envoyer un mail quand c'est terminé
# Il manque le total du conditionnement dans la nomenclature valorisée


class is_cout_calcul(models.Model):
    _name='is.cout.calcul'
    _order='name desc'

    name               = fields.Datetime('Date', required=True     , readonly=True)
    user_id            = fields.Many2one('res.users', 'Responsable', readonly=True)
    product_id         = fields.Many2one('product.product', 'Article')
    segment_id         = fields.Many2one('is.product.segment', 'Segment')
    is_category_id     = fields.Many2one('is.category', 'Catégorie')
    is_gestionnaire_id = fields.Many2one('is.gestionnaire', 'Gestionnaire')
    multiniveaux       = fields.Boolean('Calcul des coûts multi-niveaux')
    cout_actualise_ids = fields.One2many('is.cout.calcul.actualise', 'cout_calcul_id', u"Historique des côuts actualisés")
    state              = fields.Selection([('creation',u'Création'), ('prix_achat', u"Calcul des prix d'achat"),('termine', u"Terminé")], u"État", readonly=True, select=True)

    _defaults = {
        'name': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'user_id': lambda self, cr, uid, c: uid,
        'multiniveaux': True,
        'state': 'creation',
    }

    detail_nomenclature=[]
    detail_gamme_ma=[]
    detail_gamme_mo=[]

    @api.multi
    @api.multi
    def nomenclature(self, cout_calcul_obj, product, niveau, multiniveaux=True):
        cr = self._cr
        type_article=self.type_article(product)
        cout=self.creation_cout(cout_calcul_obj, product, type_article)
        if type_article!='A' and multiniveaux==True:
            SQL="""
                select mbl.product_id, mbl.id, mbl.sequence, mb.id
                from mrp_bom mb inner join mrp_bom_line mbl on mbl.bom_id=mb.id
                                inner join product_product pp on pp.product_tmpl_id=mb.product_tmpl_id
                where pp.id="""+str(product.id)+ """ 
                order by mbl.sequence, mbl.id
            """
            #TODO : Voir si ce filtre est necessaire : and (mb.is_sous_traitance='f' or mb.is_sous_traitance is null)
            cr.execute(SQL)
            result = cr.fetchall()
            niv=niveau+1
            for row2 in result:
                composant=self.env['product.product'].browse(row2[0])
                self.nomenclature(cout_calcul_obj, composant, niv)


    @api.multi
    def type_article(self, product):
        type_article=""
        for route in product.route_ids:
            if type_article=='F' and route.name=='Buy':
                type_article='ST'
            if type_article=='A' and route.name=='Manufacture':
                type_article='ST'
            if type_article=='' and route.name=='Manufacture':
                type_article='F'
            if type_article=='' and route.name=='Buy':
                type_article='A'
        return type_article


    @api.multi
    def creation_cout(self, cout_calcul_obj, product, type_article):
        cout_obj = self.env['is.cout']
        couts=cout_obj.search([('name', '=', product.id)])
        if len(couts):
            cout=couts[0]
        else:
            vals={
                'name': product.id,
            }
            cout=cout_obj.create(vals)
        cout.cout_calcul_id=cout_calcul_obj.id
        cout.type_article=type_article
        return cout



#    @api.multi
#    def _merge_pdf(self, documents):
#        """Merge PDF files into one.
#        :param documents: list of path of pdf files
#        :returns: path of the merged pdf
#        """
#        writer = PdfFileWriter()
#        streams = []  # We have to close the streams *after* PdfFilWriter's call to write()
#        ct=1
#        nb=len(documents)
#        for document in documents:
#            print ct, nb, document
#            ct=ct+1
#            pdfreport = file(document, 'rb')
#            streams.append(pdfreport)
#            reader = PdfFileReader(pdfreport)
#            for page in range(0, reader.getNumPages()):
#                writer.addPage(reader.getPage(page))
#        merged_file_fd, merged_file_path = tempfile.mkstemp(suffix='.pdf', prefix='report.merged.tmp.')
#        with closing(os.fdopen(merged_file_fd, 'w')) as merged_file:
#            writer.write(merged_file)

#        for stream in streams:
#            stream.close()
#        return merged_file_path


    @api.multi
    def action_imprimer_couts(self):
        for obj in self:
            tmp=tempfile.mkdtemp()
            os.system('mkdir '+tmp)
            ct=1
            nb=len(obj.cout_actualise_ids)
            for line in obj.cout_actualise_ids:
                couts=self.env['is.cout'].search([('name', '=', line.product_id.id)])
                for cout in couts:
                    print ct, nb, line.product_id
                    path=tmp+"/"+str(ct)+".pdf"
                    ct=ct+1
                    pdf = self.env['report'].get_pdf(cout, 'is_plastigray.report_is_cout')
                    f = open(path,'wb')
                    f.write(pdf)
                    f.close()

            os.system('pdfjoin -o '+tmp+'/merged.pdf '+tmp+'/*.pdf')
            pdf = open(tmp+'/merged.pdf','rb').read()
            os.system('rm '+tmp+'/*.pdf')
            os.system('rmdir '+tmp)

            # ** Recherche si une pièce jointe est déja associèe ***************
            model=self._name
            name='Couts.pdf'
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
            return {
                'type' : 'ir.actions.act_url',
                'url': '/web/binary/saveas?model=ir.attachment&field=datas&id='+str(attachment_id)+'&filename_field=name',
                'target': 'self',
            }
            #*******************************************************************




    @api.multi
    def action_calcul_prix_achat(self):
        cr = self._cr
        for obj in self:
            for row in obj.cout_actualise_ids:
                row.unlink()
            calcul_actualise_obj = self.env['is.cout.calcul.actualise']
            products=self.get_products(obj)
            for product in products:
                self.nomenclature(obj,product,0, obj.multiniveaux)
            couts=self.env['is.cout'].search([('cout_calcul_id', '=', obj.id)])
            product_uom_obj = self.env['product.uom']
            for cout in couts:
                product=cout.name
                prix_tarif    = 0
                prix_commande = 0
                prix_facture  = 0
                prix_calcule  = 0
                ecart_calcule_matiere = 0
                vals={
                    'cout_calcul_id': obj.id,
                    'product_id': product.id,
                }
                res=calcul_actualise_obj.create(vals)
                type_article=cout.type_article

                if type_article!='F':
                    #** Recherche du fournisseur par défaut ********************
                    seller=False
                    if len(product.seller_ids)>0:
                        seller=product.seller_ids[0]
                    pricelist=False
                    if seller:
                        partner=seller.name
                        pricelist=partner.property_product_pricelist_purchase
                    #***********************************************************


                    #** Recherche du prix d'achat ******************************

                    date=time.strftime('%Y-%m-%d') # Date du jour


                    if pricelist:
                        #Convertion du lot_mini de US vers UA
                        min_quantity = product_uom_obj._compute_qty(cout.name.uom_id.id, cout.name.lot_mini, cout.name.uom_po_id.id)

                        


                        SQL="""
                            select ppi.price_surcharge
                            from product_pricelist_version ppv inner join product_pricelist_item ppi on ppv.id=ppi.price_version_id
                            where ppv.pricelist_id="""+str(pricelist.id)+ """ 
                                  and min_quantity<="""+str(min_quantity)+"""
                                  and (ppv.date_start <= '"""+date+"""' or ppv.date_start is null)
                                  and (ppv.date_end   >= '"""+date+"""' or ppv.date_end   is null)

                                  and ppi.product_id="""+str(product.id)+ """ 
                                  and (ppi.date_start <= '"""+date+"""' or ppi.date_start is null)
                                  and (ppi.date_end   >= '"""+date+"""' or ppi.date_end   is null)
                            order by ppi.sequence
                            limit 1
                        """
                        cr.execute(SQL)
                        result = cr.fetchall()
                        for row in result:
                            #coef=product.uom_po_id.factor_inv
                            coef=1
                            if min_quantity:
                                coef=cout.name.lot_mini/min_quantity
                            prix_tarif=row[0]/coef
                    #***********************************************************


                    #** Recherche prix dernière commande ***********************
                    SQL="""
                        select pol.price_unit*pu.factor
                        from purchase_order_line pol inner join product_uom pu on pol.product_uom=pu.id
                        where pol.product_id="""+str(product.id)+ """ 
                              and state in('confirmed','done')
                        order by pol.id desc limit 1
                    """
                    cr.execute(SQL)
                    result = cr.fetchall()
                    for row in result:
                        prix_commande=row[0]
                    #***********************************************************

                    #** Recherche prix dernière facture ************************
                    SQL="""
                        select ail.price_unit*pu.factor
                        from account_invoice_line ail inner join product_uom pu on ail.uos_id=pu.id
                                                      inner join account_invoice ai on ail.invoice_id=ai.id
                        where ail.product_id="""+str(product.id)+ """ 
                              and ai.state in('open','paid') and ai.type='in_invoice'
                        order by ail.id desc limit 1
                    """
                    cr.execute(SQL)
                    result = cr.fetchall()
                    for row in result:
                        prix_facture=row[0]
                    #***********************************************************


                    if cout.prix_force:
                        prix_calcule=cout.prix_force
                    else:
                        if prix_facture:
                            prix_calcule=prix_facture
                        else:
                            if prix_commande:
                                prix_calcule=prix_commande
                            else:
                                if prix_tarif:
                                    prix_calcule=prix_tarif



                    if type_article=='A':
                        if prix_calcule==0:
                            prix_calcule=cout.cout_act_matiere
                        ecart_calcule_matiere  = prix_calcule - cout.cout_act_matiere
                    if type_article=='ST':
                        if prix_calcule==0:
                            prix_calcule=cout.cout_act_st
                        ecart_calcule_matiere  = prix_calcule - cout.cout_act_st

                if prix_tarif:
                    cout.prix_tarif=prix_tarif


                cout.type_article  = type_article

                cout.prix_commande = prix_commande
                cout.prix_facture  = prix_facture
                cout.prix_calcule  = prix_calcule
                cout.ecart_calcule_matiere = ecart_calcule_matiere


            obj.state="prix_achat"


    @api.multi
    def get_products(self,obj):
        cats=self.env['is.category']._calcul_cout()
        products={}
        if obj.product_id:
            products=self.env['product.product'].search([('id', '=', obj.product_id.id), ('is_category_id', 'in', cats)])
        else:
            if obj.segment_id:
                products=self.env['product.product'].search([('segment_id', '=', obj.segment_id.id), ('is_category_id', 'in', cats)], limit=10000)
            else:
                if obj.is_category_id:
                    products=self.env['product.product'].search([('is_category_id', '=', obj.is_category_id.id)], limit=10000)
                else:
                    if obj.is_gestionnaire_id:
                        products=self.env['product.product'].search([('is_gestionnaire_id', '=', obj.is_gestionnaire_id.id), ('is_category_id', 'in', cats)], limit=10000)
                    else:
                        products=self.env['product.product'].search([('is_category_id', 'in', cats)])
        return products



    @api.multi
    def nomenclature_prix_revient(self, cout_calcul_obj, niveau, product, unite=False, quantite_unitaire=1, quantite_total=1, prix_calcule=0):
        cr = self._cr
        type_article=self.type_article(product)
        cout_mat = 0
        cout_st  = 0
        if type_article=='A':
            cout_mat = prix_calcule
        if type_article=='ST':
            cout_st  = prix_calcule
        cout=self.creation_cout(cout_calcul_obj, product, type_article)
        self.detail_nomenclature.append({
            'product_id'  : product.id,
            'is_code'     : product.is_code,
            'composant'   : '----------'[:niveau]+str(product.is_code),
            'designation' : product.name,
            'unite'       : unite,
            'quantite'    : quantite_unitaire, 
            'cout_mat'    : cout_mat, 
            'total_mat'   : quantite_total*cout_mat,
            'cout_st'     : cout_st, 
            'total_st'    : quantite_total*cout_st,
        })

        if type_article!='A':
            lot_mini=product.lot_mini
            if lot_mini==0:
                lot_mini=1

            #** Recherche de la gamme ******************************************
            SQL="""
                select mb.routing_id
                from mrp_bom mb inner join product_product pp on pp.product_tmpl_id=mb.product_tmpl_id
                where pp.id="""+str(product.id)+ """ 
                      and (mb.is_sous_traitance='f' or mb.is_sous_traitance is null)
                order by mb.id
            """
            cr.execute(SQL)
            result = cr.fetchall()
            for row2 in result:
                routing_id = row2[0]
                if routing_id:
                    routing = self.env['mrp.routing'].browse(routing_id)
                    for line in routing.workcenter_lines:
                        # Ne pas tenir compte du temps préparation
                        # cout_total=quantite_unitaire*(\
                        #    line.workcenter_id.costs_hour*line.workcenter_id.time_start/lot_mini+\
                        #    line.is_nb_secondes*line.workcenter_id.costs_hour/3600)
                        cout_total=quantite_unitaire*line.workcenter_id.costs_hour*round(line.is_nb_secondes/3600,4)
                        vals={
                            'composant'     : '----------'[:niveau]+product.is_code,
                            'sequence'      : line.sequence,
                            'workcenter_id' : line.workcenter_id.id,
                            'quantite'      : quantite_unitaire,
                            'cout_prepa'    : line.workcenter_id.costs_hour,
                            'tps_prepa'     : line.workcenter_id.time_start, 
                            'cout_fab'      : line.workcenter_id.costs_hour, 
                            'tps_fab'       : line.is_nb_secondes,
                            'cout_total'    : cout_total, 
                        }
                        if line.workcenter_id.resource_type=='material':
                            self.detail_gamme_ma.append(vals)
                        else:
                            self.detail_gamme_mo.append(vals)
            #*******************************************************************

            #** Composants de la nomenclature **********************************
            SQL="""
                select mbl.product_id, mbl.product_uom, mbl.product_qty, ic.prix_calcule
                from mrp_bom mb inner join mrp_bom_line mbl on mbl.bom_id=mb.id
                                inner join product_product pp on pp.product_tmpl_id=mb.product_tmpl_id
                                inner join is_cout ic on ic.name=mbl.product_id
                where pp.id="""+str(product.id)+ """ 
                order by mbl.sequence, mbl.id
            """
            # TODO : Filtre sur ce critère ? => and (mb.is_sous_traitance='f' or mb.is_sous_traitance is null)
            cr.execute(SQL)
            result = cr.fetchall()
            niv=niveau+1
            for row2 in result:
                composant    = self.env['product.product'].browse(row2[0])
                unite        = row2[1]
                qt_unitaire  = row2[2]
                qt_total     = qt_unitaire*quantite_total
                prix_calcule = row2[3]
                self.nomenclature_prix_revient(cout_calcul_obj, niv, composant, unite, qt_unitaire, qt_total, prix_calcule)
            #*******************************************************************

    @api.multi
    def action_calcul_prix_revient(self):
        for obj in self:
            cout_obj = self.env['is.cout']
            for row in obj.cout_actualise_ids:
                product=row.product_id
                couts=cout_obj.search([('name', '=', product.id)])
                if len(couts):
                    for cout in couts:
                        cout_act_matiere   = 0
                        cout_act_st        = 0
                        cout_act_condition = 0
                        cout_act_machine   = 0
                        cout_act_mo        = 0
                        cout_act_total     = 0

                        for row2 in cout.nomenclature_ids:
                            row2.unlink()
                        for row2 in cout.gamme_ma_ids:
                            row2.unlink()
                        for row2 in cout.gamme_mo_ids:
                            row2.unlink()
                        if cout.type_article=='A':
                            cout_act_matiere = cout.prix_calcule
                            cout_act_st      = 0
                        if cout.type_article=='ST':
                            cout_act_matiere = 0
                            cout_act_st      = 0
                        if cout.type_article!='A':
                            self.detail_nomenclature=[]
                            self.detail_gamme_ma=[]
                            self.detail_gamme_mo=[]
                            self.nomenclature_prix_revient(obj, 0, product, False, 1, 1, cout.prix_calcule)
                            for vals in self.detail_nomenclature:
                                is_code=vals['is_code']
                                if is_code[:1]=="7":
                                    cout_act_condition=cout_act_condition+vals['total_mat']
                                del vals['is_code']
                                vals['cout_id']=cout.id
                                cout_act_matiere = cout_act_matiere+vals['total_mat']
                                cout_act_st      = cout_act_st+vals['total_st']
                                res=self.env['is.cout.nomenclature'].create(vals)
                            vals={
                                'cout_id'     : cout.id,
                                'designation' : 'TOTAL  : ',
                                'total_mat'   : cout_act_matiere,
                                'total_st'    : cout_act_st,
                            }
                            res=self.env['is.cout.nomenclature'].create(vals)
                            vals={
                                'cout_id'     : cout.id,
                                'designation' : 'Conditionnement  : ',
                                'total_mat'   : cout_act_condition,
                            }
                            res=self.env['is.cout.nomenclature'].create(vals)

                            for vals in self.detail_gamme_ma:
                                vals['cout_id']=cout.id
                                res=self.env['is.cout.gamme.ma'].create(vals)
                                cout_act_machine = cout_act_machine+vals['cout_total']
                            for vals in self.detail_gamme_mo:
                                vals['cout_id']=cout.id
                                res=self.env['is.cout.gamme.mo'].create(vals)
                                cout_act_mo = cout_act_mo+vals['cout_total']

                        cout_act_total=cout_act_matiere+cout_act_machine+cout_act_mo+cout_act_st




                        cout.cout_act_matiere   = cout_act_matiere
                        cout.cout_act_condition = cout_act_condition
                        cout.cout_act_machine   = cout_act_machine
                        cout.cout_act_mo        = cout_act_mo
                        cout.cout_act_st        = cout_act_st
                        cout.cout_act_total     = cout_act_total
                        cout.is_category_id     = row.product_id.is_category_id
                        cout.is_gestionnaire_id = row.product_id.is_gestionnaire_id
                        cout.is_mold_id         = row.product_id.is_mold_id
                        cout.uom_id             = row.product_id.uom_id
                        cout.lot_mini           = row.product_id.lot_mini

                        row.cout_act_matiere    = cout_act_matiere
                        row.cout_act_machine    = cout_act_machine
                        row.cout_act_mo         = cout_act_mo
                        row.cout_act_st         = cout_act_st
                        row.cout_act_total      = cout_act_total

            obj.state="termine"



class is_cout_calcul_actualise(models.Model):
    _name='is.cout.calcul.actualise'

    cout_calcul_id   = fields.Many2one('is.cout.calcul'  , 'Coût Calcul', required=True, ondelete='cascade')
    product_id       = fields.Many2one('product.product', 'Article'    , required=True, readonly=False)
    cout_act_matiere = fields.Float("Coût act matière"       , digits=(12, 4))
    cout_act_machine = fields.Float("Coût act machine"       , digits=(12, 4))
    cout_act_mo      = fields.Float("Coût act main d'oeuvre" , digits=(12, 4))
    cout_act_st      = fields.Float("Coût act sous-traitance", digits=(12, 4))
    cout_act_total   = fields.Float("Coût act Total"         , digits=(12, 4))



    @api.multi
    def action_acces_cout(self):
        for obj in self:
            product_id=obj.product_id.id
            couts=self.env['is.cout'].search([['name', '=', product_id]])
            if len(couts)>0:
                res_id=couts[0].id
                return {
                    'name': obj.product_id.name,
                    'view_mode': 'form',
                    'view_type': 'form',
                    'res_model': 'is.cout',
                    'type': 'ir.actions.act_window',
                    'res_id': res_id,
                }




class is_cout(models.Model):
    _name='is.cout'
    _order='name'

    name                   = fields.Many2one('product.product', 'Article', required=True, readonly=False, select=True)
    cout_calcul_id         = fields.Many2one('is.cout.calcul', 'Calcul des coût')
    is_category_id         = fields.Many2one('is.category', 'Catégorie')
    is_gestionnaire_id     = fields.Many2one('is.gestionnaire', 'Gestionnaire')
    is_mold_id             = fields.Many2one('is.mold', 'Moule')
    type_article           = fields.Selection([('A', u'Acheté'),('F', u'Fabriqué'),('ST', u'Sous-traité')], "Type d'article")
    uom_id                 = fields.Many2one('product.uom', 'Unité')
    lot_mini               = fields.Float("Lot d'appro.")

    prix_tarif             = fields.Float("Prix tarif"                  , digits=(12, 4))
    prix_commande          = fields.Float("Prix dernière commande"      , digits=(12, 4))
    prix_facture           = fields.Float("Prix dernière facture"       , digits=(12, 4))
    prix_force             = fields.Float("Prix forcé (saisie manuelle)", digits=(12, 4))
    prix_force_commentaire = fields.Char("Commentaire")
    prix_calcule           = fields.Float("Prix calculé"                , digits=(12, 4))
    prix_sous_traitance    = fields.Float("Prix sous-traitance"         , digits=(12, 4))

    ecart_calcule_matiere  = fields.Float("Ecart Calculé/Matière"       , digits=(12, 4))

    cout_std_matiere       = fields.Float("Coût std matière"         , digits=(12, 4))
    cout_std_condition     = fields.Float("Coût std conditionnement" , digits=(12, 4))
    cout_std_machine       = fields.Float("Coût std machine"         , digits=(12, 4))
    cout_std_mo            = fields.Float("Coût std main d'oeuvre"   , digits=(12, 4))
    cout_std_st            = fields.Float("Coût std sous-traitance"  , digits=(12, 4))
    cout_std_total         = fields.Float("Coût std Total"           , digits=(12, 4))
    cout_std_prix_vente    = fields.Float("Prix de vente standard"   , digits=(12, 4))
    cout_std_preserie      = fields.Float("Surcout Présérie"         , digits=(12, 4))
    cout_std_amtmoule      = fields.Float("Amortissement moule"      , digits=(12, 4))
    cout_prix_vente        = fields.Float("Prix de vente tarif commercial", digits=(12, 4))

    cout_act_matiere       = fields.Float("Coût act matière"        , digits=(12, 4))
    cout_act_condition     = fields.Float("Coût act conditionnement", digits=(12, 4))
    cout_act_machine       = fields.Float("Coût act machine"        , digits=(12, 4))
    cout_act_mo            = fields.Float("Coût act main d'oeuvre"  , digits=(12, 4))
    cout_act_st            = fields.Float("Coût act sous-traitance" , digits=(12, 4))
    cout_act_total         = fields.Float("Coût act Total"          , digits=(12, 4))

    amortissement_moule    = fields.Float("Amortissement Moule"     , digits=(12, 4), compute='_compute')
    surcout_pre_serie      = fields.Float("Surcôut pré-série"       , digits=(12, 4), compute='_compute')
    prix_vente             = fields.Float("Prix de Vente"           , digits=(12, 4), compute='_compute')

    nomenclature_ids       = fields.One2many('is.cout.nomenclature', 'cout_id', u"Lignes de la nomenclature")
    gamme_ma_ids           = fields.One2many('is.cout.gamme.ma'    , 'cout_id', u"Lignes gamme machine")
    gamme_mo_ids           = fields.One2many('is.cout.gamme.mo'    , 'cout_id', u"Lignes gamme MO")


    @api.depends('name')
    def _compute(self):
        for obj in self:
            tarifs=self.env['is.tarif.cial'].search([('product_id', '=', obj.name.product_tmpl_id.id),('indice_prix', '=', 999)])
            for tarif in tarifs:
                obj.amortissement_moule = tarif.amortissement_moule
                obj.surcout_pre_serie   = tarif.surcout_pre_serie
                obj.prix_vente          = tarif.prix_vente


    @api.multi
    def action_calcul_cout(self):
        for obj in self:

            vals={
                'product_id'   : obj.name.id,
                'multiniveaux' : False,
            }
            cout_calcul=self.env['is.cout.calcul'].create(vals)
            cout_calcul.action_calcul_prix_achat()
            cout_calcul.action_calcul_prix_revient()
            
            return {
                'name': obj.name.name,
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'is.cout',
                'type': 'ir.actions.act_window',
                'res_id': obj.id,
            }


    @api.multi
    def copie_cout_actualise_dans_cout_standard(self):
        for obj in self:
            obj.cout_std_matiere   = obj.cout_act_matiere
            obj.cout_std_condition = obj.cout_act_condition
            obj.cout_std_machine   = obj.cout_act_machine
            obj.cout_std_mo        = obj.cout_act_mo
            obj.cout_std_st        = obj.cout_act_st
            obj.cout_std_total     = obj.cout_act_total


class is_cout_nomenclature(models.Model):
    _name='is.cout.nomenclature'

    cout_id          = fields.Many2one('is.cout', 'Coût article', required=True, ondelete='cascade')
    product_id       = fields.Many2one('product.product', 'Article')
    composant        = fields.Char('Composant')
    designation      = fields.Char('Désignation')
    unite            = fields.Many2one('product.uom', 'Unité')
    quantite         = fields.Float('Quantité'  , digits=(12, 4))
    cout_mat         = fields.Float('Coût Mat'  , digits=(12, 4))
    total_mat        = fields.Float('Total Mat' , digits=(12, 4))
    cout_st          = fields.Float('Coût ST'   , digits=(12, 4))
    total_st         = fields.Float('Total ST'  , digits=(12, 4))


class is_cout_gamme_ma(models.Model):
    _name='is.cout.gamme.ma'

    cout_id       = fields.Many2one('is.cout', 'Coût article', required=True, ondelete='cascade')
    composant     = fields.Char('Composant')
    sequence      = fields.Integer('N°')
    workcenter_id = fields.Many2one('mrp.workcenter', 'Poste de charges')
    quantite      = fields.Float('Quantité')
    cout_prepa    = fields.Float('Coût Préparation'      , digits=(12, 4))
    tps_prepa     = fields.Float('Tps Préparation (H)')
    cout_fab      = fields.Float('Coût Fabrication'      , digits=(12, 4))
    tps_fab       = fields.Float('Tps Fabrication (s)')
    cout_total    = fields.Float('Coût Total'            , digits=(12, 4))


class is_cout_gamme_mo(models.Model):
    _name='is.cout.gamme.mo'

    cout_id       = fields.Many2one('is.cout', 'Coût article', required=True, ondelete='cascade')
    composant     = fields.Char('Composant')
    sequence      = fields.Integer('N°')
    workcenter_id = fields.Many2one('mrp.workcenter', 'Poste de charges')
    quantite      = fields.Float('Quantité')
    cout_prepa    = fields.Float('Coût Préparation'      , digits=(12, 4))
    tps_prepa     = fields.Float('Tps Préparation (H)')
    cout_fab      = fields.Float('Coût Fabrication'      , digits=(12, 4))
    tps_fab       = fields.Float('Tps Fabrication (s)')
    cout_total    = fields.Float('Coût Total'            , digits=(12, 4))


