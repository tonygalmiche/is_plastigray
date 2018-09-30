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


def duree(debut):
    dt = datetime.datetime.now() - debut
    ms = (dt.days * 24 * 60 * 60 + dt.seconds) * 1000 + dt.microseconds / 1000.0
    ms=int(ms)
    return ms


def _now(debut):
    return datetime.datetime.now(pytz.timezone('Europe/Paris')).strftime('%H:%M:%S') + ' : '+ str(int(duree(debut)/100.0)/10.0)+"s"




class is_cout_calcul(models.Model):
    _inherit='is.cout.calcul'


#    @api.multi
#    def calcul_prix_revient_ext(self,rows,thread):
#        for obj in self:
#            nb=len(rows)
#            ct=0
#            for row in rows:
#                cout=self.env['is.cout.calcul.actualise'].search([('id', '=', row)])[0]
#                ct=ct+1
#                _logger.info(str(thread)+'/'+str(ct)+'/'+str(nb)+'/'+str(row)+' : '+str(cout.product_id.is_code))
#                self.calcul_prix_revient_thread(obj,cout,thread)

#        return True



    @api.multi
    def calcul_prix_revient(self,obj_id,row_ids,thread):


        #is.cout.calcul.actualise
        #is.cout.calcul

        #print 'calcul_prix_revient=',obj_id,row_ids,thread

        with api.Environment.manage():
            new_cr = registry(self._cr.dbname).cursor()

            self.cursors.append(new_cr)

            #print '### thread,cursors=',thread,self.cursors



            #new_cr.autocommit(True) 
            self = self.with_env(self.env(cr=new_cr))

            nb=len(row_ids)
            ct=0
            for row_id in row_ids:
                #print 'row=',row

                ct=ct+1
                _logger.info('thread : '+str(thread)+' - '+str(ct)+'/'+str(nb))
                self.calcul_prix_revient_thread(obj_id,row_id,thread)


            #self._cr.rollback()
            #self._cr.commit()
            #self._cr.close()
            #new_cr.commit()
            #new_cr.close()



    @api.multi
    def calcul_prix_revient_thread(self,obj_id,row_id,thread_id=False):
        #print 'row=',row,row._cr



        #print '## obj,row,thread_id,product=',obj,row,thread_id,product

        obj=self.env['is.cout.calcul'].search([('id', '=', obj_id)])[0]
        row=self.env['is.cout.calcul.actualise'].search([('id', '=', row_id)])[0]
        product=row.product_id


        cout_obj = self.env['is.cout']
        couts=cout_obj.search([('name', '=', product.id)])
        if len(couts):
            for cout in couts:


                #print self._cr,cout, cout.name.is_code


                #fh = open('/tmp/cout.lock', 'a') 
                #fh.write(str(cout.id)+'\n') 
                #fh.close 

                #if cout.thread_id:
                #    print 'thread_id=',thread_id
                #    return
                #cout.thread_id=thread_id

                cout_act_matiere    = 0
                cout_act_st         = 0
                cout_act_condition  = 0
                cout_act_machine    = 0
                cout_act_machine_pk = 0
                cout_act_mo         = 0
                cout_act_mo_pk      = 0
                cout_act_total      = 0

                for row2 in cout.nomenclature_ids:
                    row2.unlink()
                for row2 in cout.gamme_ma_ids:
                    row2.unlink()
                for row2 in cout.gamme_mo_ids:
                    row2.unlink()
                cout.gamme_mo_pk_ids.unlink()
                cout.gamme_ma_pk_ids.unlink()

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

                    self.nomenclature_prix_revient(obj, 0, product, False, 1, 1, cout.prix_calcule, thread_id)
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

                #Client par défaut
                for row2 in row.product_id.is_client_ids:
                    if row2.client_defaut:
                        cout.partner_id=row2.client_id.id

                cout.nb_err              = nb_err
                if nb_err>0:
                    cout_act_matiere=0

                cout_act_total=cout_act_matiere+cout_act_machine+cout_act_mo+cout_act_st

                cout.cout_act_matiere    = cout_act_matiere
                cout.cout_act_condition  = cout_act_condition
                cout.cout_act_machine    = cout_act_machine
                cout.cout_act_mo         = cout_act_mo
                cout.cout_act_machine_pk = cout_act_machine_pk
                cout.cout_act_mo_pk      = cout_act_mo_pk
                cout.cout_act_st         = cout_act_st
                cout.cout_act_total      = cout_act_total
                cout.is_category_id      = row.product_id.is_category_id
                cout.is_gestionnaire_id  = row.product_id.is_gestionnaire_id
                cout.is_mold_id          = row.product_id.is_mold_id
                cout.is_mold_dossierf    = row.product_id.is_mold_dossierf
                cout.uom_id              = row.product_id.uom_id
                cout.lot_mini            = row.product_id.lot_mini
                cout.cout_act_prix_vente = cout.prix_vente-cout.amortissement_moule-cout.surcout_pre_serie

                row.cout_act_matiere     = cout_act_matiere
                row.cout_act_machine     = cout_act_machine
                row.cout_act_mo          = cout_act_mo
                row.cout_act_machine_pk  = cout_act_machine_pk
                row.cout_act_mo_pk       = cout_act_mo_pk

                row.cout_act_st          = cout_act_st
                row.cout_act_total       = cout_act_total


                #try:
                #    self._cr.commit()
                #except ValueError:
                #    print 'ValueError=',ValueError


    @api.multi
    def action_calcul_prix_revient2(self):
        #cr = self._cr
        #SQL="update is_cout set thread_id=0;"
        #cr.execute(SQL)
        #cr.commit()

        #print 'cr origine = ',self._cr

        self.locks=[]
        self.cursors=[]

        for obj in self:
            nb=len(obj.cout_actualise_ids)

            #** Répartition des lignes dans le nombre de threads indiqué *******
            nb_threads=4
            self._log("## DEBUT Calcul des prix de revient (threads="+str(nb_threads)+")")

            t=0
            res={}
            for row in obj.cout_actualise_ids:
                #print row
                if not t in res:
                    res[t]=[]
                res[t].append(row.id)
                t=t+1
                if t>=nb_threads:
                    t=0
            #*******************************************************************


            #for r in res:
            #    print r,len(res[r])


            #** Lancement des threads ******************************************
            threads=[]
            ct=0
            for r in res:
                rows=res[r]
                t = threading.Thread(target=self.calcul_prix_revient, args=[obj.id,rows,r])
                t.start()
                #print r,t
                #t.join()
                threads.append(t)




#                for row in res[r]:
#                    ct=ct+1
#                    _logger.info(str(r)+'/'+str(ct)+'/'+str(nb)+' : '+str(row.product_id.is_code))
#                    t = threading.Thread(target=self.calcul_prix_revient, args=[obj,row])
#                    t.start()
#                    print t
#                    t.join()
#                    threads.append(t)

            #for t in threads:
            #    print 't=',t
            #    t.join()


            while any(thread.is_alive() for thread in threads):
                #print('running...')
                time.sleep(1)


            #print 'cursors=',self.cursors

            for cursor in self.cursors:
                cursor.commit()
                cursor.close()

            obj.state="termine"
            self._log("## FIN Calcul des prix de revient")



