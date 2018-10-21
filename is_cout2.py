# -*- coding: utf-8 -*-

from openerp import models,fields,api,registry
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


#TODO Nombre de threads
nb_threads=4


def duree(debut):
    dt = datetime.datetime.now() - debut
    ms = (dt.days * 24 * 60 * 60 + dt.seconds) * 1000 + dt.microseconds / 1000.0
    ms=int(ms)
    return ms


def _now(debut):
    return str(int(duree(debut)/100.0)/10.0)+"s"


class is_cout_calcul(models.Model):
    _inherit='is.cout.calcul'


#    #TODO : Fonction à désactiver pour retrouver le fonctionnement classique
#    @api.multi
#    def get_products(self,obj):
#        products=self.env['product.product'].search([('is_code', 'like', '290745%')])
#        return products


    @api.multi
    def nomenclature2(self, cout_calcul_obj, product, niveau, multiniveaux=True):
        cr = self._cr

        #** Ajout de l'article et de son niveau dans la table prévue ***********
        #_logger.info('- composant nomenclature/niveau : '+str(product.is_code)+'/'+str(niveau))
        vals={
            'cout_calcul_id': cout_calcul_obj.id,
            'product_id'    : product.id,
            'niveau'        : niveau,
        }
        res=self.env['is.cout.calcul.niveau'].create(vals)
        #***********************************************************************


        type_article=self.type_article(product)
        #cout=self.creation_cout(cout_calcul_obj, product, type_article)
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
                self.nomenclature2(cout_calcul_obj, composant, niv)


    @api.multi
    def _creation_couts_thread(self,obj_id,rows,thread,nb_threads=0):
        with api.Environment.manage():
            if nb_threads>0:
                new_cr = registry(self._cr.dbname).cursor()
                self.cursors.append(new_cr)
                self = self.with_env(self.env(cr=new_cr))
            obj=self.env['is.cout.calcul'].search([('id', '=', obj_id)])[0]
            nb=len(rows)
            ct=0
            for row in rows:
                ct=ct+1
                product_id = row[0]
                niveau     = row[1]
                product = self.env['product.product'].browse(product_id)
                _logger.info('creation_cout : thread : '+str(thread)+' - '+str(ct)+'/'+str(nb)+' : '+str(product.is_code))
                type_article=self.type_article(product)
                cout=self.creation_cout(obj, product, type_article, niveau=niveau)


    @api.multi
    def _creation_couts(self,nb_threads=0):
        cr = self._cr
        for obj in self:
            SQL="""
                select product_id,max(niveau) 
                from is_cout_calcul_niveau 
                where cout_calcul_id="""+str(obj.id)+""" 
                group by product_id order by max(niveau) desc,product_id;
            """
            cr.execute(SQL)
            result = cr.fetchall()

            #** Répartition des lignes dans le nombre de threads indiqué *******
            t=0
            res={}
            for row in result:
                if not t in res:
                    res[t]=[]
                res[t].append(row)
                t=t+1
                if t>=nb_threads:
                    t=0
            #*******************************************************************

            #** Lancement des threads ******************************************
            threads=[]
            self.cursors=[]
            ct=0
            for r in res:
                rows=res[r]
                if nb_threads>0:
                    t = threading.Thread(target=self._creation_couts_thread, args=[obj.id,rows,r,nb_threads])
                    t.start()
                    threads.append(t)
                else:
                    self._creation_couts_thread(obj.id,rows,r,nb_threads)
            #*******************************************************************

            #** Attente de la fin des threads et fermeture des cursors *********
            while any(thread.is_alive() for thread in threads):
                time.sleep(1)
            for cursor in self.cursors:
                cursor.commit()
                cursor.close()
            #*******************************************************************


#    @api.multi
#    def _get_pricelist(self,product):
#        """Recherche pricelist du fournisseur par défaut"""
#        seller=False
#        if product.seller_ids:
#            seller=product.seller_ids[0]
#        pricelist=False
#        if seller:
#            partner=seller.name
#            pricelist=partner.property_product_pricelist_purchase
#        return pricelist


    @api.multi
    def _get_pricelist(self,product):
        """Recherche pricelist du fournisseur par défaut"""
        cr = self._cr
        seller=False
        if product.seller_ids:
            seller=product.seller_ids[0]
        pricelist=False
        if seller:
            partner=seller.name
            SQL="""
                SELECT get_product_pricelist_purchase(id)
                FROM res_partner
                WHERE id="""+str(partner.id)+"""
            """
            cr.execute(SQL)
            result = cr.fetchall()
            for row in result:
                pricelist=self.env['product.pricelist'].browse(row[0])
        return pricelist


    @api.multi
    def _get_prix_tarif(self,cout,pricelist):
        """Recherche du prix tarif"""
        cr = self._cr
        product=cout.name
        prix_tarif=0
        date=time.strftime('%Y-%m-%d') # Date du jour
        if pricelist:
            #Convertion du lot_mini de US vers UA
            min_quantity = self.env['product.uom']._compute_qty(cout.name.uom_id.id, cout.name.lot_mini, cout.name.uom_po_id.id)
            #TODO : Pour contourner un bug d'arrondi (le 31/01/2017)
            min_quantity=min_quantity+0.00000000001
            #TODO en utilisant la fonction repr à la place de str, cela ne tronque pas les décimales
            SQL="""
                select ppi.price_surcharge
                from product_pricelist_version ppv inner join product_pricelist_item ppi on ppv.id=ppi.price_version_id
                where ppv.pricelist_id="""+str(pricelist.id)+ """ 
                      and min_quantity<="""+repr(min_quantity)+"""
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
                coef=1
                if min_quantity:
                    coef=cout.name.lot_mini/min_quantity
                prix_tarif=row[0]/coef
        return prix_tarif


    @api.multi
    def _get_prix_commande(self,product):
        """Recherche prix dernière commande"""
        cr = self._cr
        SQL="""
            select pol.price_unit*pu.factor
            from purchase_order_line pol inner join product_uom pu on pol.product_uom=pu.id
            where pol.product_id="""+str(product.id)+ """ 
                  and state in('confirmed','done')
            order by pol.id desc limit 1
        """
        cr.execute(SQL)
        result = cr.fetchall()
        prix_commande=0
        for row in result:
            prix_commande=row[0]
        return prix_commande


    @api.multi
    def _get_prix_facture(self,product):
        """Recherche prix dernière facture"""
        cr = self._cr
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
        prix_facture=0
        for row in result:
            prix_facture=row[0]
        return prix_facture


    @api.multi
    def _maj_couts_thread(self,obj_id,rows,thread,nb_threads):
        #pr=cProfile.Profile()
        #pr.enable()
        with api.Environment.manage():
            if nb_threads>0:
                new_cr = registry(self._cr.dbname).cursor()
                self.cursors.append(new_cr)
                self = self.with_env(self.env(cr=new_cr))
            obj=self.env['is.cout.calcul'].search([('id', '=', obj_id)])[0]
            nb=len(rows)
            ct=0
            for row in rows:
                ct=ct+1
                cout = self.env['is.cout'].browse(row)
                product=cout.name
                _logger.info('maj_cout : thread : '+str(thread)+' - '+str(ct)+'/'+str(nb)+' : '+str(product.is_code))
                prix_tarif    = 0
                prix_commande = 0
                prix_facture  = 0
                prix_calcule  = 0
                ecart_calcule_matiere = 0
                vals={
                    'cout_calcul_id': obj.id,
                    'product_id': product.id,
                }
                res=self.env['is.cout.calcul.actualise'].create(vals)
                type_article=cout.type_article
                if type_article!='F':
                    pricelist     = self._get_pricelist(product)         # Recherche pricelist du fournisseur par défaut
                    prix_tarif    = self._get_prix_tarif(cout,pricelist) # Recherche du prix tarif
                    prix_commande = self._get_prix_commande(product)     # Recherche prix dernière commande
                    prix_facture  = self._get_prix_facture(product)      # Recherche prix dernière facture
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
                vals={}
                if prix_tarif:
                    vals.update({
                        'prix_tarif' : prix_tarif
                    })
                vals.update({
                    'type_article'         : type_article,
                    'prix_commande'        : prix_commande,
                    'prix_facture'         : prix_facture,
                    'prix_calcule'         : prix_calcule,
                    'ecart_calcule_matiere': ecart_calcule_matiere,
                })
                cout.write(vals)
        #pr.disable()
        #pr.dump_stats('/tmp/analyse.cProfile')


    @api.multi
    def _maj_couts(self,nb_threads=0):
        """Mise à jour des couts en threads"""
        for obj in self:
            #** Répartition des lignes dans le nombre de threads indiqué *******
            t=0
            res={}
            #TODO : Nouvelle environnement pour avoir un cr  contenant les dernières modifications des threads précédents
            with api.Environment.manage():
                if nb_threads>0:
                    new_cr = registry(self._cr.dbname).cursor()
                    self = self.with_env(self.env(cr=new_cr))
                couts=self.env['is.cout'].search([('cout_calcul_id', '=', obj.id)])
                for cout in couts:
                    if not t in res:
                        res[t]=[]
                    res[t].append(cout.id)
                    t=t+1
                    if t>=nb_threads:
                        t=0
                if nb_threads>0:
                    new_cr.commit()
                    new_cr.close()
            #*******************************************************************

            #** Lancement des threads ******************************************
            threads=[]
            self.cursors=[]
            ct=0
            for r in res:
                rows=res[r]
                if nb_threads>0:
                    t = threading.Thread(target=self._maj_couts_thread, args=[obj.id,rows,r,nb_threads])
                    t.start()
                    threads.append(t)
                else:
                    self._maj_couts_thread(obj.id,rows,r,nb_threads)

            #*******************************************************************


            #** Attente de la fin des threads et fermeture des cursors *********
            while any(thread.is_alive() for thread in threads):
                time.sleep(1)
            for cursor in self.cursors:
                cursor.commit()
                cursor.close()
            #*******************************************************************


    @api.multi
    def action_calcul_prix_achat2(self):
        """Fonction initiale appellée au début du calcul"""
        self.action_calcul_prix_achat_thread()


    @api.multi
    def action_calcul_prix_achat_thread(self,nb_threads=""):
        """Début du calcul en déterminant les threads à utiliser"""
        self.mem_couts={}
        cr = self._cr
        uid=self._uid
        user=self.env['res.users'].browse(uid)
        if nb_threads=="":
            nb_threads=user.company_id.is_nb_threads
            if nb_threads>10:
                nb_threads=0
        debut=datetime.datetime.now()
        for obj in self:
            obj.niveau_ids.unlink()
            self._log("## DEBUT Calcul des prix d'achat ("+str(nb_threads)+" coeurs)")
            _logger.info('début unlink')
            obj.cout_actualise_ids.unlink()
            _logger.info('fin unlink')
            calcul_actualise_obj = self.env['is.cout.calcul.actualise']
            _logger.info("début get_products")
            products=self.get_products(obj)
            _logger.info("fin get_products : nb="+str(len(products)))
            ct=1
            nb=len(products)
            _logger.info("début boucle products : nb="+str(nb))
            for product in products:
                _logger.info(str(ct)+'/'+str(nb)+' : boucle products : '+product.is_code)
                ct+=1
                #cProfile.runctx("self.nomenclature2(obj,product,0, obj.multiniveaux)",globals(),locals(),"/tmp/test.bin")
                self.nomenclature2(obj,product,0, obj.multiniveaux)

            _logger.info("fin boucle products")

            _logger.info("début création coûts "+_now(debut))
            self._creation_couts(nb_threads) # Création ou initialisation des fiches de couts en threads
            _logger.info("fin création coûts "+_now(debut))

            _logger.info("début boucle couts : nb="+str(nb)+' '+_now(debut))
            self._maj_couts(nb_threads) # Mise à jour des coûts en threads
            _logger.info("fin boucle couts"+' '+_now(debut))

            self._log("## FIN Calcul des prix d'achat ("+str(nb_threads)+" coeurs) "+_now(debut))

            obj.state="prix_achat"

        #pr.disable()
        #pr.dump_stats('/tmp/test.bin')




