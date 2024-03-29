# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning
import datetime
import time
import pytz
import base64
import tempfile
import os
from pyPdf import PdfFileWriter, PdfFileReader
from contextlib import closing
import threading
from decimal import Decimal
import logging
_logger = logging.getLogger(__name__)
#import cProfile


def duree(debut):
    dt = datetime.datetime.now() - debut
    ms = (dt.days * 24 * 60 * 60 + dt.seconds) * 1000 + dt.microseconds / 1000.0
    ms=int(ms)
    return ms


def _now(debut):
    return datetime.datetime.now(pytz.timezone('Europe/Paris')).strftime('%H:%M:%S') + ' : '+ str(int(duree(debut)/100.0)/10.0)+"s"




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
    niveau_ids         = fields.One2many('is.cout.calcul.niveau'   , 'cout_calcul_id', u"Niveau des articles dans la nomenclature")
    log_ids            = fields.One2many('is.cout.calcul.log', 'cout_calcul_id', u"Logs")
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

    detail_gamme_ma_pk=[]
    detail_gamme_mo_pk=[]

    mem_couts={}

    @api.multi
    @api.multi
    def nomenclature(self, cout_calcul_obj, product, niveau, multiniveaux=True):
        cr = self._cr
        type_article=self.type_article(product)
        cout=self.creation_cout(cout_calcul_obj, product, type_article)
        if type_article!='A' and multiniveaux==True:
            if niveau>10:
                raise Warning(u"Trop de niveaux (>10) dans la nomenclature du "+product.is_code)
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
    def creation_cout(self, cout_calcul_obj, product, type_article, niveau=0):
        product_id=product.id
        #_logger.info('creation_cout : len(mem_couts)='+str(len(self.mem_couts)))
        if product_id in self.mem_couts:
            action='trouvé'
            cout=self.mem_couts[product_id]
        else:
            cout_obj = self.env['is.cout']
            couts=cout_obj.search([('name', '=', product_id)])
            vals={
                'cout_calcul_id': cout_calcul_obj.id,
                'type_article'  : type_article,
                'niveau'        : niveau,
            }
            if len(couts):
                action='write'
                cout=couts[0]
                cout.write(vals)
            else:
                action='create'
                vals['name'] = product_id
                cout=cout_obj.create(vals)
            self.mem_couts[product_id]=cout
        return cout


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
    def _log(self,operation):
        _logger.info(operation)
        for obj in self:
            vals={
                'cout_calcul_id': obj.id,
                'date'          : datetime.datetime.now(),
                'operation'     : operation,
            }
            res=self.env['is.cout.calcul.log'].create(vals)




#    @api.multi
#    def action_calcul_prix_achat(self):
#        cr = self._cr
#        debut=datetime.datetime.now()
#        for obj in self:
#            #obj.log_ids.unlink()
#            self._log("## DEBUT Calcul des prix d'achat")
#            _logger.info('début unlink')
#            for row in obj.cout_actualise_ids:
#                row.unlink()
#            _logger.info('fin unlink')
#            calcul_actualise_obj = self.env['is.cout.calcul.actualise']
#            _logger.info("début get_products")
#            products=self.get_products(obj)
#            _logger.info("fin get_products : nb="+str(len(products)))



#            #TODO : 0.07s par article (88s pour 1233 articles)
#            ct=1
#            nb=len(products)
#            #print _now(debut), "## début boucle products : nb=",nb

#            _logger.info("début boucle products : nb="+str(nb))

#            for product in products:
#                _logger.info(str(ct)+'/'+str(nb)+' : boucle products : '+product.is_code)
#                #print _now(debut), product,ct,'/',nb
#                ct+=1
#                self.nomenclature(obj,product,0, obj.multiniveaux)
#            couts=self.env['is.cout'].search([('cout_calcul_id', '=', obj.id)])
#            product_uom_obj = self.env['product.uom']
#            #print _now(debut), "## fin boucle products"
#            _logger.info("fin boucle products")




#            ct=1
#            nb=len(couts)
#            #print _now(debut), "## début boucle couts : nb=",nb
#            _logger.info("début boucle couts : nb="+str(nb))
#            for cout in couts:
#                product=cout.name

#                _logger.info(str(ct)+'/'+str(nb)+' : boucle couts : '+product.is_code)

#                #print _now(debut), product.is_code,ct,'/',nb
#                ct+=1


#                prix_tarif    = 0
#                prix_commande = 0
#                prix_facture  = 0
#                prix_calcule  = 0
#                ecart_calcule_matiere = 0
#                vals={
#                    'cout_calcul_id': obj.id,
#                    'product_id': product.id,
#                }
#                res=calcul_actualise_obj.create(vals)
#                type_article=cout.type_article

#                if type_article!='F':
#                    #** Recherche du fournisseur par défaut ********************
#                    seller=False
#                    if len(product.seller_ids)>0:
#                        seller=product.seller_ids[0]
#                    pricelist=False
#                    if seller:
#                        partner=seller.name
#                        pricelist=partner.property_product_pricelist_purchase
#                    #***********************************************************


#                    #** Recherche du prix d'achat ******************************
#                    date=time.strftime('%Y-%m-%d') # Date du jour

#                    if pricelist:
#                        #Convertion du lot_mini de US vers UA
#                        min_quantity = product_uom_obj._compute_qty(cout.name.uom_id.id, cout.name.lot_mini, cout.name.uom_po_id.id)

#                        #TODO : Pour contourner un bug d'arrondi (le 31/01/2017)
#                        min_quantity=min_quantity+0.00000000001
#                        #TODO en utilisant la fonction repr à la place de str, cela ne tronque pas les décimales

#                        SQL="""
#                            select ppi.price_surcharge
#                            from product_pricelist_version ppv inner join product_pricelist_item ppi on ppv.id=ppi.price_version_id
#                            where ppv.pricelist_id="""+str(pricelist.id)+ """ 
#                                  and min_quantity<="""+repr(min_quantity)+"""
#                                  and (ppv.date_start <= '"""+date+"""' or ppv.date_start is null)
#                                  and (ppv.date_end   >= '"""+date+"""' or ppv.date_end   is null)

#                                  and ppi.product_id="""+str(product.id)+ """ 
#                                  and (ppi.date_start <= '"""+date+"""' or ppi.date_start is null)
#                                  and (ppi.date_end   >= '"""+date+"""' or ppi.date_end   is null)
#                            order by ppi.sequence
#                            limit 1
#                        """
#                        cr.execute(SQL)
#                        result = cr.fetchall()
#                        for row in result:
#                            #coef=product.uom_po_id.factor_inv
#                            coef=1
#                            if min_quantity:
#                                coef=cout.name.lot_mini/min_quantity
#                            prix_tarif=row[0]/coef
#                    #***********************************************************


#                    #** Recherche prix dernière commande ***********************
#                    SQL="""
#                        select pol.price_unit*pu.factor
#                        from purchase_order_line pol inner join product_uom pu on pol.product_uom=pu.id
#                        where pol.product_id="""+str(product.id)+ """ 
#                              and state in('confirmed','done')
#                        order by pol.id desc limit 1
#                    """
#                    cr.execute(SQL)
#                    result = cr.fetchall()
#                    for row in result:
#                        prix_commande=row[0]
#                    #***********************************************************

#                    #** Recherche prix dernière facture ************************
#                    SQL="""
#                        select ail.price_unit*pu.factor
#                        from account_invoice_line ail inner join product_uom pu on ail.uos_id=pu.id
#                                                      inner join account_invoice ai on ail.invoice_id=ai.id
#                        where ail.product_id="""+str(product.id)+ """ 
#                              and ai.state in('open','paid') and ai.type='in_invoice'
#                        order by ail.id desc limit 1
#                    """
#                    cr.execute(SQL)
#                    result = cr.fetchall()
#                    for row in result:
#                        prix_facture=row[0]
#                    #***********************************************************


#                    if cout.prix_force:
#                        prix_calcule=cout.prix_force
#                    else:
#                        if prix_facture:
#                            prix_calcule=prix_facture
#                        else:
#                            if prix_commande:
#                                prix_calcule=prix_commande
#                            else:
#                                if prix_tarif:
#                                    prix_calcule=prix_tarif



#                    if type_article=='A':
#                        if prix_calcule==0:
#                            prix_calcule=cout.cout_act_matiere
#                        ecart_calcule_matiere  = prix_calcule - cout.cout_act_matiere
#                    if type_article=='ST':
#                        if prix_calcule==0:
#                            prix_calcule=cout.cout_act_st
#                        ecart_calcule_matiere  = prix_calcule - cout.cout_act_st

#                if prix_tarif:
#                    cout.prix_tarif=prix_tarif


#                cout.type_article  = type_article

#                cout.prix_commande = prix_commande
#                cout.prix_facture  = prix_facture
#                cout.prix_calcule  = prix_calcule
#                cout.ecart_calcule_matiere = ecart_calcule_matiere


#            obj.state="prix_achat"

#        self._log("## FIN Calcul des prix d'achat"+_now(debut))

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
        msg_err=''
        if product.is_category_id.name!='80':
            if type_article=='A':
                cout_mat = prix_calcule
                if prix_calcule==0:
                    msg_err=u'Err Coût Mat'
            if type_article=='ST':
                cout_st  = prix_calcule
                if prix_calcule==0:
                    msg_err=u'Err Coût ST'

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
            'msg_err'     : msg_err,
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




            #** Recherche de la gamme générique pour Cout Plasti-ka ************
            SQL="""
                select mb.is_gamme_generique_id
                from mrp_bom mb inner join product_product pp on pp.product_tmpl_id=mb.product_tmpl_id
                where pp.id="""+str(product.id)+ """ 
                order by mb.id
            """
            cr.execute(SQL)
            result = cr.fetchall()
            for row2 in result:
                routing_id = row2[0]
                if routing_id:
                    routing = self.env['mrp.routing'].browse(routing_id)
                    for line in routing.workcenter_lines:
                        cout_total=quantite_unitaire*line.workcenter_id.is_cout_pk*round(line.is_nb_secondes/3600,4)
                        vals={
                            'composant'     : '----------'[:niveau]+product.is_code,
                            'sequence'      : line.sequence,
                            'workcenter_id' : line.workcenter_id.id,
                            'quantite'      : quantite_unitaire,
                            'cout_prepa'    : line.workcenter_id.is_cout_pk,
                            'tps_prepa'     : line.workcenter_id.time_start, 
                            'cout_fab'      : line.workcenter_id.is_cout_pk, 
                            'tps_fab'       : line.is_nb_secondes,
                            'cout_total'    : cout_total, 
                        }
                        if line.workcenter_id.resource_type=='material':
                            self.detail_gamme_ma_pk.append(vals)
                        else:
                            self.detail_gamme_mo_pk.append(vals)
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
    def _productid2cout(self,product_id):
        cout_obj = self.env['is.cout']
        couts=cout_obj.search([('name', '=', product_id)])
        return couts


    @api.multi
    def _get_couts(self):
        couts=[]
        for obj in self:
            for row in obj.cout_actualise_ids:
                product=row.product_id
                res=self._productid2cout(product.id)
                for r in res:
                    couts.append(r)
        return couts


    @api.multi
    def _unlink_detail_cout(self,couts):
        """En regroupant la suppression de toutes les lignes, cela permet de gagner beaucoup de temps"""
        cr = self._cr
        if couts:
            ids = self._get_couts_ids(couts)
            if ids:
                ids=','.join(ids)
                SQL=''
                SQL+='DELETE FROM is_cout_nomenclature WHERE cout_id in('+ids+'); '
                SQL+='DELETE FROM is_cout_gamme_ma     WHERE cout_id in('+ids+'); '
                SQL+='DELETE FROM is_cout_gamme_mo     WHERE cout_id in('+ids+'); '
                SQL+='DELETE FROM is_cout_gamme_ma_pk  WHERE cout_id in('+ids+'); '
                SQL+='DELETE FROM is_cout_gamme_mo_pk  WHERE cout_id in('+ids+'); '
                cr.execute(SQL)


    @api.multi
    def _get_couts_ids(self,couts):
        """Retourne la liste des id des couts à partir des couts"""
        ids=[]
        for cout in couts:
            ids.append(str(cout.id))
        return ids


    @api.multi
    def _write_resultats(self):
        "Ecrit les résultats des calculs dans la page récapitulative"
        for obj in self:
            for row in obj.cout_actualise_ids:
                product=row.product_id
                couts=self._productid2cout(product.id)
                for cout in couts:
                    vals={}
                    vals['cout_act_matiere']     = cout.cout_act_matiere
                    vals['cout_act_machine']     = cout.cout_act_machine
                    vals['cout_act_mo']          = cout.cout_act_mo
                    vals['cout_act_st']          = cout.cout_act_st
                    vals['cout_act_total']       = cout.cout_act_total
                    row.write(vals)


    @api.multi
    def action_calcul_prix_revient(self):
        #pr=cProfile.Profile()
        #pr.enable()
        for obj in self:
            self._log("## DEBUT Calcul des prix de revient")
            nb=len(obj.cout_actualise_ids)
            ct=0
            couts = self._get_couts()
            self._unlink_detail_cout(couts)
            for cout in couts:



                product=cout.name
                ct=ct+1
                _logger.info(str(ct)+'/'+str(nb)+' : '+str(product.is_code))

                cout_act_matiere    = 0
                cout_act_st         = 0
                cout_act_condition  = 0
                cout_act_machine    = 0
                cout_act_machine_pk = 0
                cout_act_mo         = 0
                cout_act_mo_pk      = 0
                cout_act_total      = 0

                if cout.type_article=='A':
                    cout_act_matiere = cout.prix_calcule
                    cout_act_st      = 0
                if cout.type_article=='ST':
                    cout_act_matiere = 0
                    cout_act_st      = 0

                nb_err=0
                if cout.type_article!='A':
                    self.detail_nomenclature=[]
                    self.detail_gamme_ma=[]
                    self.detail_gamme_mo=[]
                    self.detail_gamme_ma_pk=[]
                    self.detail_gamme_mo_pk=[]

                    self.nomenclature_prix_revient(obj, 0, product, False, 1, 1, cout.prix_calcule)
                    for vals in self.detail_nomenclature:
                        if vals['msg_err']!='':
                            nb_err=nb_err+1
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

                    for vals in self.detail_gamme_ma_pk:
                        vals['cout_id']=cout.id
                        res=self.env['is.cout.gamme.ma.pk'].create(vals)
                        cout_act_machine_pk = cout_act_machine_pk+vals['cout_total']
                    for vals in self.detail_gamme_mo_pk:
                        vals['cout_id']=cout.id
                        res=self.env['is.cout.gamme.mo.pk'].create(vals)
                        cout_act_mo_pk = cout_act_mo_pk+vals['cout_total']

                vals={}
                #Client par défaut
                for row in product.is_client_ids:
                    if row.client_defaut:
                        vals['partner_id']=row.client_id.id
                vals['nb_err'] = nb_err
                if nb_err>0:
                    cout_act_matiere=0
                cout_act_total=cout_act_matiere+cout_act_machine+cout_act_mo+cout_act_st
                vals['cout_act_matiere']    = cout_act_matiere
                vals['cout_act_condition']  = cout_act_condition
                vals['cout_act_machine']    = cout_act_machine
                vals['cout_act_mo']         = cout_act_mo
                vals['cout_act_machine_pk'] = cout_act_machine_pk
                vals['cout_act_mo_pk']      = cout_act_mo_pk
                vals['cout_act_st']         = cout_act_st
                vals['cout_act_total']      = cout_act_total
                vals['is_category_id']      = product.is_category_id.id
                vals['is_gestionnaire_id']  = product.is_gestionnaire_id.id
                vals['is_mold_id']          = product.is_mold_id.id
                vals['is_mold_dossierf']    = product.is_mold_dossierf
                vals['uom_id']              = product.uom_id.id
                vals['lot_mini']            = product.lot_mini
                vals['cout_act_prix_vente'] = cout.prix_vente-cout.amortissement_moule-cout.surcout_pre_serie
                cout.write(vals)
            self._write_resultats()
            obj.state="termine"
            self._log("## FIN Calcul des prix de revient")

        #pr.disable()
        #pr.dump_stats('/tmp/analyse.cProfile')





class is_cout_calcul_log(models.Model):
    _name='is.cout.calcul.log'
    _order='date'

    cout_calcul_id = fields.Many2one('is.cout.calcul'  , 'Coût Calcul', required=True, ondelete='cascade')
    date           = fields.Datetime('Date', required=True)
    operation      = fields.Char('Opération')


class is_cout_calcul_niveau(models.Model):
    """Contient le niveau de chaque article dans la nomenclature pour pouvoir lancer les calculs par niveau"""
    _name='is.cout.calcul.niveau'

    cout_calcul_id = fields.Many2one('is.cout.calcul' , 'Coût Calcul', required=True, ondelete='cascade')
    product_id     = fields.Many2one('product.product', 'Article'    , select=True)
    niveau         = fields.Integer('Niveau dans la nomenclature'    , select=True)


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
    _sql_constraints = [('name_uniq', 'unique(name)', u"Ce code existe déja !")]

    name                   = fields.Many2one('product.product', 'Article', required=True, readonly=False, select=True)
    code_pg                = fields.Char('Code PG'    , related='name.product_tmpl_id.is_code', readonly=True)
    designation            = fields.Char('Désignation', related='name.product_tmpl_id.name'   , readonly=True)
    cout_calcul_id         = fields.Many2one('is.cout.calcul', 'Calcul des coût')
    is_category_id         = fields.Many2one('is.category', 'Catégorie')
    is_gestionnaire_id     = fields.Many2one('is.gestionnaire', 'Gestionnaire')
    is_mold_id             = fields.Many2one('is.mold', 'Moule')
    is_mold_dossierf       = fields.Char('Moule ou Dossier F')
    partner_id             = fields.Many2one('res.partner', 'Client par défaut')
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

    cout_act_matiere       = fields.Float("Coût act matière"        , digits=(12, 4))
    cout_act_condition     = fields.Float("Coût act conditionnement", digits=(12, 4))
    cout_act_machine       = fields.Float("Coût act machine"        , digits=(12, 4))
    cout_act_mo            = fields.Float("Coût act main d'oeuvre"  , digits=(12, 4))
    cout_act_machine_pk    = fields.Float("Coût act machine PK"      , digits=(12, 4))
    cout_act_mo_pk         = fields.Float("Coût act main d'oeuvre PK", digits=(12, 4))
    cout_act_st            = fields.Float("Coût act sous-traitance" , digits=(12, 4))
    cout_act_total         = fields.Float("Coût act Total"          , digits=(12, 4))
    cout_act_prix_vente    = fields.Float("Prix de vente actualisé" , digits=(12, 4))

    cout_std_matiere       = fields.Float("Coût std matière"         , digits=(12, 4))
    cout_std_condition     = fields.Float("Coût std conditionnement" , digits=(12, 4))
    cout_std_machine       = fields.Float("Coût std machine"         , digits=(12, 4))
    cout_std_mo            = fields.Float("Coût std main d'oeuvre"   , digits=(12, 4))
    cout_std_st            = fields.Float("Coût std sous-traitance"  , digits=(12, 4))
    cout_std_total         = fields.Float("Coût std Total"           , digits=(12, 4))
    cout_std_prix_vente    = fields.Float("Prix de vente standard"   , digits=(12, 4))

    cout_budget_matiere       = fields.Float("Coût budget matière"         , digits=(12, 4))
    cout_budget_condition     = fields.Float("Coût budget conditionnement" , digits=(12, 4))
    cout_budget_machine       = fields.Float("Coût budget machine"         , digits=(12, 4))
    cout_budget_mo            = fields.Float("Coût budget main d'oeuvre"   , digits=(12, 4))
    cout_budget_st            = fields.Float("Coût budget sous-traitance"  , digits=(12, 4))
    cout_budget_total         = fields.Float("Coût budget Total"           , digits=(12, 4))
    cout_budget_prix_vente    = fields.Float("Prix de vente budget"        , digits=(12, 4))

    amortissement_moule    = fields.Float("Amortissement Moule"     , digits=(12, 4), compute='_compute')
    surcout_pre_serie      = fields.Float("Surcôut pré-série"       , digits=(12, 4), compute='_compute')
    prix_vente             = fields.Float("Prix de Vente"           , digits=(12, 4), compute='_compute')
    nomenclature_ids       = fields.One2many('is.cout.nomenclature', 'cout_id', u"Lignes de la nomenclature")
    gamme_ma_ids           = fields.One2many('is.cout.gamme.ma'    , 'cout_id', u"Lignes gamme machine")
    gamme_mo_ids           = fields.One2many('is.cout.gamme.mo'    , 'cout_id', u"Lignes gamme MO")
    gamme_ma_pk_ids        = fields.One2many('is.cout.gamme.ma.pk' , 'cout_id', u"Lignes gamme machine PK")
    gamme_mo_pk_ids        = fields.One2many('is.cout.gamme.mo.pk' , 'cout_id', u"Lignes gamme MO PK")
    niveau                 = fields.Integer('Niveau le plus bas dans la nomenclature')
    nb_err                 = fields.Integer('Nb Err', help=u"Nombre d'erreures détectées lors du calcul de coûts")


    @api.depends('name')
    def _compute(self):
        for obj in self:
            #** Recherche du tarif commercial pour le client par défaut ********
            code_client=mem_code_client=False
            for client in obj.name.product_tmpl_id.is_client_ids:
                mem_code_client=client.client_id.is_code
                if client.client_defaut:
                    code_client=mem_code_client
            if code_client==False:
                code_client=mem_code_client
            tarifs=self.env['is.tarif.cial'].search([
                ('product_id', '=', obj.name.product_tmpl_id.id),
                ('indice_prix', '=', 999),
                ('partner_id.is_code', '=', code_client)
            ])
            for tarif in tarifs:
                obj.amortissement_moule = tarif.amortissement_moule
                obj.surcout_pre_serie   = tarif.surcout_pre_serie
                obj.prix_vente          = tarif.prix_vente


    @api.multi
    def write(self, vals):
        for obj in self:
            matiere   = vals.get('cout_std_matiere'  , obj.cout_std_matiere)
            machine   = vals.get('cout_std_machine'  , obj.cout_std_machine)
            mo        = vals.get('cout_std_mo'       , obj.cout_std_mo)
            st        = vals.get('cout_std_st'       , obj.cout_std_st)
            vals['cout_std_total']=matiere+machine+mo+st
        res=super(is_cout, self).write(vals)
        return res


    @api.multi
    def action_calcul_cout(self):
        for obj in self:
            vals={
                'product_id'   : obj.name.id,
                'multiniveaux' : False,
            }
            cout_calcul=self.env['is.cout.calcul'].create(vals)
            cout_calcul.action_calcul_prix_achat_thread(nb_threads=0)
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
    def action_calcul_cout_pk(self):
        for obj in self:
            vals={
                'product_id'   : obj.name.id,
                'multiniveaux' : False,
            }
            cout_calcul=self.env['is.cout.calcul'].create(vals)
            cout_calcul.action_calcul_prix_achat_thread(nb_threads=0)
            cout_calcul.action_calcul_prix_revient()
            dummy, view_id = self.env['ir.model.data'].get_object_reference('is_plastigray', 'is_cout_pk_form_view')
            return {
                'name': obj.name.name,
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'is.cout',
                'type': 'ir.actions.act_window',
                'view_id': view_id,
                'res_id': obj.id,
            }


    @api.multi
    def _copie_cout_actualise_dans_cout_standard(self,obj):
        vals={
            'cout_std_matiere'    : obj.cout_act_matiere,
            'cout_std_condition'  : obj.cout_act_condition,
            'cout_std_machine'    : obj.cout_act_machine,
            'cout_std_mo'         : obj.cout_act_mo,
            'cout_std_st'         : obj.cout_act_st,
            'cout_std_total'      : obj.cout_act_total,
            'cout_std_prix_vente' : obj.cout_act_prix_vente,
        }
        obj.write(vals)


    @api.multi
    def copie_cout_actualise_dans_cout_standard(self):
        for obj in self:
            self._copie_cout_actualise_dans_cout_standard(obj)




    @api.multi
    def _copie_cout_actualise_dans_cout_budget(self,obj):
        vals={
            'cout_budget_matiere'    : obj.cout_act_matiere,
            'cout_budget_condition'  : obj.cout_act_condition,
            'cout_budget_machine'    : obj.cout_act_machine,
            'cout_budget_mo'         : obj.cout_act_mo,
            'cout_budget_st'         : obj.cout_act_st,
            'cout_budget_total'      : obj.cout_act_total,
            'cout_budget_prix_vente' : obj.cout_act_prix_vente,
        }
        obj.write(vals)


    @api.multi
    def copie_cout_actualise_dans_cout_budget(self):
        for obj in self:
            self._copie_cout_actualise_dans_cout_budget(obj)










    @api.multi
    def initialisation_prix_vente_standard(self):
        for obj in self:
            obj.cout_std_prix_vente = obj.prix_vente-obj.amortissement_moule-obj.surcout_pre_serie

    @api.model
    def print_btn_report(self):
        threaded_calculation = threading.Thread(target=self.save_cout_report, args=())
        threaded_calculation.start()
        return True

    def save_cout_report(self):
        user = self.env['res.users'].browse(self._uid)
        with api.Environment.manage():
            new_cr = self.pool.cursor()
            self = self.with_env(self.env(cr=new_cr))
            report_service = 'is_plastigray.report_is_cout'
            #file_param  = self.env['ir.config_parameter'].get_param('path_report_pdf')
            db=self._cr.dbname
            path="/tmp/couts-" + db
            cde="rm -Rf " + path
            os.popen(cde).readlines()
            if not os.path.exists(path):
                os.makedirs(path)
            recs=self.search([], order="name",limit=50000)
            nb=len(recs)
            _logger.info("#### Début sauvegarde Coûts ####")
            ct=0
            for rec in recs:
                ct=ct+1
                code_pg=rec.name.is_code
                _logger.info('- '+str(ct)+'/'+str(nb)+' : '+str(code_pg))
                result, format = self.env['report'].get_pdf(rec, report_service), 'pdf'
                file_name = path + '/'+str(code_pg) +'.pdf'
                fd = os.open(file_name,os.O_RDWR|os.O_CREAT)
                try:
                    os.write(fd, result)
                finally:
                    os.close(fd)
            filename="/var/www/odoo/couts/"+db+".zip"
            cde="rm -f " + filename + " && cd /tmp && zip -r " + filename + " couts-" +db+" && chmod 755 "+filename
            os.popen(cde).readlines()
            self.send_mail_notyfy_user()
            new_cr.close()
            _logger.info("#### Fin sauvegarde Coûts ####")
            return {}

    def send_mail_notyfy_user(self):
        db=self._cr.dbname
        user = self.env['res.users'].browse(self._uid)
        mail_pool = self.env['mail.mail']
        values={}
        values.update({'subject': 'Génération des PDF des coûts terminée'})
        values.update({'email_from': user.partner_id.email})
        values.update({'email_to': user.partner_id.email})
        values.update({'body_html': '<p>Bonjour,</p><p>Le zip contenant tous les PDF est disponible <a href="http://odoo/couts/'+db+'.zip">ici</a></p>' })
        #values.update({'body': 'Bonjour,\nLe zip contenant tous les PDF est disonible ici http://odoo/couts-odoo1.zip' })
#         values.update({'res_id': 'obj.id' }) #[optional] here is the record id, where you want to post that email after sending
        values.update({'model': 'is.cout' }) #[optional] here is the object(like 'project.project')  to whose record id you want to post that email after sending
        msg_id = mail_pool.sudo().create(values)
        # And then call send function of the mail.mail,
        if msg_id:
            msg_id.send()
        return True

    @api.multi
    def cout_standard_indice_precedent(self):
        if len(self)>1:
            raise Warning(u"Modification multiple non autorisée !")
        for obj in self:
            is_code=obj.name.is_code
            indice=is_code[6:7]
            if indice=='':
                raise Warning(u"Code sans indice !")
            code=is_code[0:6]
            if indice!='A':
                code=code+chr(ord(indice)-1)
            couts=self.env['is.cout'].search([('name.is_code', '=', code)])
            if len(couts)==0:
                raise Warning(u"Coût précédent non trouvé !")
            for cout in couts:
                obj.cout_std_matiere    = cout.cout_std_matiere
                obj.cout_std_condition  = cout.cout_std_condition
                obj.cout_std_machine    = cout.cout_std_machine
                obj.cout_std_mo         = cout.cout_std_mo
                obj.cout_std_st         = cout.cout_std_st
                obj.cout_std_total      = cout.cout_std_total
                obj.cout_std_prix_vente = cout.cout_std_prix_vente


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
    msg_err          = fields.Char('Err')


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


class is_cout_gamme_ma_pl(models.Model):
    _name='is.cout.gamme.ma.pk'

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


class is_cout_gamme_mo_pk(models.Model):
    _name='is.cout.gamme.mo.pk'

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


class base_config_settings(models.TransientModel):
    _inherit = 'base.config.settings'
    
    path_report_pdf = fields.Char('Report saved Path', 
                                               help="Location to store pdf.")
        
    @api.model
    def get_default_path_report_pdf(self, fields):
        path_report_pdf = self.env['ir.config_parameter'].get_param('path_report_pdf')
        if not path_report_pdf:
            path_report_pdf = '/tmp/Cout article'
        return {'path_report_pdf': str(path_report_pdf)}
    
    @api.one
    def set_default_path_report_pdf(self):
        config = self
        config = config and config[0]
        val = '%s' % (config.path_report_pdf) or '/tmp/Cout article'
        self.env['ir.config_parameter'].set_param('path_report_pdf', val)
        return True


