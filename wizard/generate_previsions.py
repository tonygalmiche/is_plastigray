# -*- coding: utf-8 -*-
import time
import datetime

#from openerp.osv import fields, osv
from openerp import models,fields,api


from openerp.tools.translate import _
from openerp import netsvc

#TODO : 
# Lors de la création d'une suggestion, vérfier s'il en existe déja une ou pas. 
# => Modifier celle existante pour n'avoir qu'une suggestion par semaine et regrouper celle-ci au lot
# Reste à supprimer les anciennes suggestions avant de les créer. Eviter de supprimer et recréer si seulement une FS
# Tenir compte des lots et multuple de lots lors de la création des FS/SA (lot_mini et multiple) 
# => Cela genere du surstock => Voir pour faire cela à la fin
# => Mettre une case à cochée dans l'assistant pour paramètrer cela
# Tenir compte des délais de fabrication ou de livraiosn lors de la création des FS/SA (dates de début et de fin des FS et SA)
# Tester les résultats avec des commandes partielles, des réceptions partielles ou des OF partiels
# => Avec une livraison partielle, le calcul semble bon, mais l'affichage n'est pas bon dans l'intranet
# => Dans l'intranet utilser les routes pour distiniquer si un produit est acheté ou fabriqué
# Lancer le calcul dans un ordre logique : prendu vendu, produits fabriqués (semi-fini) produit achetés
# Le calcul ne tient pas compte des SF actullement
# Renommer mrp_prevision en mrp_suggestion
# Renommer fs en FS, ft en FT et sa en SA
# Remettre à 0 les compteurs avant chaque lancement
# Tenir compte du lot mini => TODO : Voir pour faire cela a la fin du traitement car cela génére du surstock



def duree(debut):
    dt = datetime.datetime.now() - debut
    ms = (dt.days * 24 * 60 * 60 + dt.seconds) * 1000 + dt.microseconds / 1000.0
    ms=int(ms)
    return ms


#TODO : Permet d'indiquer le produit à analyser
product_id_test=0

#class mrp_generate_previsions(osv.osv_memory):



class mrp_generate_previsions(models.TransientModel):

    _name = "mrp.previsions.generate"
    _description = "Generate previsions"

    max_date   = fields.Date('Date limite', required=True)
    company_id = fields.Many2one('res.company', 'Société', required=True)



    @api.multi
    def _check_date_max(self):
        for obj in self:
            if obj.max_date < time.strftime('%Y-%m-%d'):
                return False
            return True

    def _max_date():
        now = datetime.date.today()                # Date du jour
        date = now + datetime.timedelta(days=1)   # Date + 30 jours
        return date.strftime('%Y-%m-%d')           # Formatage

    _defaults = {
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'mrp.previsions.generate', context=c),
        'max_date':  _max_date(),
    }

    _constraints = [
        (_check_date_max, u'La date max doit être supérieure à la date de jour', ['max_date']),
    ]


    #** Liste des dates à traiter **********************************************
    @api.multi
    def _dates(self, date_max):
        now     = datetime.datetime.now()               # Date de jour
        weekday = now.weekday()                         # Jour dans la semaine
        date   = now - datetime.timedelta(days=weekday) # Date du lundi précédent
        dates = []
        while(date.strftime('%Y-%m-%d')<=date_max):
            dates.append(date.strftime('%Y-%m-%d'))
            date = date + datetime.timedelta(days=7)    # Lundi suivant
        return dates



    #** Ajouter 7 jours à la date indiquée *************************************
    @api.multi
    def _date_fin(self, date):
        date_fin = datetime.datetime.strptime(date, '%Y-%m-%d')
        date_fin = date_fin + datetime.timedelta(days=7)
        date_fin = date_fin.strftime('%Y-%m-%d')
        return date_fin


    #** Enlever 7 jours à la date indiquée *************************************
    @api.multi
    def _date_debut(self, date):
        date_debut = datetime.datetime.strptime(date, '%Y-%m-%d')
        date_debut = date_debut - datetime.timedelta(days=7)
        date_debut = date_debut.strftime('%Y-%m-%d')
        return date_debut

    @api.multi
    def _articles(self):
        articles=[]
        for product in self.env['product.product'].search([]):
            articles.append(product)

#        cr=self._cr
#        obj = self.pool.get('product.product')
#        ids = obj.search([])
#        articles=[]
#        if ids:
#            for product in obj.browse(cr, uid, ids, context=context):
#                    articles.append(product)
        articles.sort()
        return articles

    @api.multi
    def _stocks(self,articles):
        cr=self._cr
        res={}
        sql="""
            select product_id, sum(qty) 
            from stock_quant  
            where location_id=12 
            group by product_id"""
        cr.execute(sql)
        for row in cr.fetchall():
            res[row[0]]=row[1]
        return res

    def _cde_cli(self, date_debut, date_fin):
        cr=self._cr
        now=datetime.datetime.now().strftime('%Y-%m-%d')
        if date_debut<=now:
            date_debut="2000-01-01"
        sql="""
            select sol.product_id, sum(sol.product_uom_qty)
            from sale_order so inner join sale_order_line sol on so.id=sol.order_id  
            where sol.state not in ('cancel','done') 
                  and sol.is_date_expedition>='"""+str(date_debut)+"""'
                  and sol.is_date_expedition<'"""+str(date_fin)+"""'
            group by sol.product_id 
        """
        res={}
        cr.execute(sql)
        for row in cr.fetchall():
            res[row[0]]=row[1]
            if row[0]==product_id_test:
                print "_cde_cli : ",row[0], row[1], date_debut, date_fin

        return res


    def _fl(self, date_debut, date_fin):
        cr=self._cr
        now=datetime.datetime.now().strftime('%Y-%m-%d')
        if date_debut<=now:
            date_debut="2000-01-01"

        date_debut = date_debut + ' 23:59:59'
        date_fin   = date_fin   + ' 23:59:59'
        sql="""
            select sm.product_id, sum(sm.product_uom_qty)
            from stock_move sm inner join mrp_production mp on sm.production_id=mp.id 
            where sm.state not in ('cancel', 'done') 
                  and mp.date_planned>='"""+date_debut+"""'
                  and mp.date_planned<'"""+date_fin+"""'
            group by sm.product_id
        """
        res={}
        cr.execute(sql)
        for row in cr.fetchall():
            res[row[0]]=row[1]

            if row[0]==product_id_test:
                print sql

        return res


    def _fm(self, date_debut, date_fin):
        cr=self._cr
        now=datetime.datetime.now().strftime('%Y-%m-%d')
        if date_debut<=now:
            date_debut="2000-01-01"

        date_debut = date_debut + ' 23:59:59'
        date_fin   = date_fin   + ' 23:59:59'
        sql="""
            select sm.product_id, sum(sm.product_uom_qty)
            from stock_move sm inner join mrp_production mp on sm.raw_material_production_id=mp.id 
            where sm.state not in ('cancel', 'done')
                  and mp.date_planned>='"""+date_debut+"""'
                  and mp.date_planned<'"""+date_fin+"""'
            group by sm.product_id
        """
        res={}
        cr.execute(sql)
        for row in cr.fetchall():
            res[row[0]]=row[1]
        return res


    @api.multi
    def _suggestions(self, date_debut, date_fin, type):
        cr=self._cr
#        obj = self.pool.get('mrp.prevision')
#        start_date = date_debut
#        now=datetime.datetime.now().strftime('%Y-%m-%d')
#        if start_date<=now:
#            start_date="2000-01-01"
#        end_date   = date_fin

#        if type=='fs':
#            ids = obj.search(cr, uid, ['&','&',('type','=',type),('start_date','>=',start_date),('start_date','<',end_date)])
#            if len(ids)>1:
#                for row in obj.browse(cr, uid, ids, context=context):
#                    print "-- type=",type, row.name, row.quantity, start_date, end_date, row.product_id


        now=datetime.datetime.now().strftime('%Y-%m-%d')
        if date_debut<=now:
            date_debut="2000-01-01"
        sql="""
            select product_id, sum(quantity)
            from mrp_prevision  
            where type='"""+str(type)+"""' 
                  and start_date>='"""+str(date_debut)+"""'
                  and start_date<'"""+str(date_fin)+"""'
            group by product_id 
        """
        res={}
        cr.execute(sql)
        for row in cr.fetchall():
            res[row[0]]=row[1]
        return res


#    #** Déterminer le premier niveau de la nomenclature d'un produit ***********
#    def get_product_boms(self, cr, uid, product, context=None):
#        boms = []
#        bom_obj = self.pool.get('mrp.bom')
#        template_id = product.product_tmpl_id and product.product_tmpl_id.id or False
#        if template_id:
#            bom_ids = bom_obj.search(cr, uid, [('product_tmpl_id','=',template_id),], context=context)
#            if bom_ids:
#                for line in bom_obj.browse(cr, uid, bom_ids[0], context=context).bom_line_ids:
#                    boms.append(line.id)
#        return boms


#    def _creer_mrp_prevision(self, cr, uid, type, product_id, quantity, start_date, end_date, note='', parent_id=False, context=None):
#        vals = {
#            'type': type,
#            'parent_id': parent_id,
#            'product_id': product_id,
#            'quantity': quantity,
#            'quantity_origine': quantity,
#            'start_date': start_date,
#            'end_date': end_date,
#            'note': note,
#        }
#        obj = self.pool.get('mrp.prevision')
#        id = obj.create(cr, uid, vals, context=context)
#        if product_id==product_id_test:
#            print "creer_mrp_prevision : id=",id, vals

#        return id

    @api.multi
    def _creer_suggestion(self, product, quantity, date):
        type="fs"
        if product.route_ids:
            route=product.route_ids[0].name
            if route=="Manufacture":
                type="fs"
            if route=="Buy":
                type="sa"
        if type=='fs':
            obj = self.env['mrp.prevision']
            end_date   = date
            start_date = self._date_debut(date)
            now=datetime.datetime.now().strftime('%Y-%m-%d')
            if start_date<=now:
                start_date="2000-01-01"
            rows = obj.search(['&','&','&',('type','=',type),('product_id','=',product.id),('start_date','>',start_date),('start_date','<=',end_date)])
            for row in rows:
                quantity=row.quantity+quantity


                obj.browse([row.id]).write({'quantity': quantity})


                if product.id==product_id_test:
                    print "creer_mrp_prevision : write : ", row.quantity
                return quantity

        vals = {
            'type': type,
            'product_id': product.id,
            'quantity': quantity,
            'quantity_origine': quantity,
            'start_date': date,
            'end_date': date,
        }
        obj = self.env['mrp.prevision']
        id = obj.create(vals)
        if product.id==product_id_test:
            print "creer_mrp_prevision : create : id=",id, date, vals
        return vals["quantity"]


#creer_mrp_prevision : id= 44537 {'product_id': 10, 'end_date': '2016-04-25', 'name': u'FS-2108', 'start_date': '2016-03-12', 'type': 'fs', 'quantity_origine': 1010.0, 'quantity': 1010.0}


#    def _regrouper_suggestion(self, cr, uid, date, product, type, quantity, context=None):
#        id=None
#        obj = self.pool.get('mrp.prevision')
#        start_date = date
#        now=datetime.datetime.now().strftime('%Y-%m-%d')
#        if start_date<=now:
#            start_date="2000-01-01"
#        end_date   = self._date_fin(cr, uid, date)
#        ids = obj.search(cr, uid, ['&','&','&',('type','=',type),('product_id','=',product.id),('start_date','>=',start_date),('start_date','<',end_date)])
#        if len(ids)>1:
#            #print "#Regroupement ici : ", date, product, quantity, ids, len(ids)
#            #for row in obj.browse(cr, uid, ids, context=context):
#            #    print row.name, row.quantity, date, start_date, end_date, product.id
#            id=self._creer_suggestion(cr, uid, product, quantity, date)
#            obj.unlink(cr, uid, ids)
#        return id


#    def _multiple_lot(self, cr, uid, date, product, type, quantity, context=None):
#        rep=False
#        id=None
#        obj = self.pool.get('mrp.prevision')
#        start_date = date
#        now=datetime.datetime.now().strftime('%Y-%m-%d')
#        if start_date<=now:
#            start_date="2000-01-01"
#        end_date   = self._date_fin(cr, uid, date)
#        ids = obj.search(cr, uid, ['&','&','&',('type','=',type),('product_id','=',product.id),('start_date','>=',start_date),('start_date','<',end_date)])
#        if ids:
#            #print "#Multiple du lot ici : ", date, product, quantity, ids, len(ids)
#            for row in obj.browse(cr, uid, ids, context=context):
#                quantity=row.quantity
#                if quantity<row.product_id.lot_mini:
#                    quantity=row.product_id.lot_mini
#                    obj.write(cr, uid, [row.id], {'quantity': quantity}, context=context)
#                    #qty = product.lot_mini + (qty2 * product.multiple)
#                    rep=True

#                    print "multiple_lot : ",row.name, row.quantity, quantity, product.id
#        return rep




    @api.multi
    def generate_previsions(self):
        cr=self._cr
        debut=datetime.datetime.now()

        #TODO : Mettre en place une liste d'étapes pour gérer les différentes phases du CBN 
        #=> calcul brut => Regroupement des suggestions => Suggestions multiples du lot
        regroupement = False
        #multiple_lot = False

        #Etapes du cbn
        #states=["cbb","regrouper_suggestion","multiple_lot"]
        states=["cbb"]


        for obj in self:
            prevision_obj = self.env['mrp.prevision']
            bom_line_obj  = self.env['mrp.bom.line']
            company_obj   = self.env['res.company']
            partner_obj   = self.env['res.partner']
            company       = obj.company_id
















            #** supprimer les previsions existantes ****************************
            prevision_ids = prevision_obj.search([('active','=',True),]).unlink()
            #*******************************************************************

            dates    = self._dates(obj.max_date)

            print dates

            articles = self._articles()
            stocks   = self._stocks(articles)
            num_od=1
            compteur=1
            stock_theorique={}
            niveau=0
            state=states[niveau]
            while True:
                nb=0
                print "##### DEBUT Boucle state="+str(state)+" : "+str(compteur)+" : nb="+str(nb)+"#####"


                for date in dates:
                    date_debut  = date
                    date_fin    = self._date_fin(date)
                    cde_cli     = self._cde_cli(date_debut, date_fin)
                    fs          = self._suggestions(date_debut, date_fin, 'fs')
                    sa          = self._suggestions(date_debut, date_fin, 'sa')
                    ft          = self._suggestions(date_debut, date_fin, 'ft')
                    fl          = self._fl(date_debut, date_fin)
                    fm          = self._fm(date_debut, date_fin)
                    for product in articles:
                        qt_stock      = stocks.get(product.id, 0)
                        qt_cde_cli    = cde_cli.get(product.id, 0)
                        qt_fs         = fs.get(product.id, 0)
                        qt_sa         = sa.get(product.id, 0)
                        qt_ft         = ft.get(product.id, 0)
                        qt_fl         = fl.get(product.id, 0)
                        qt_fm         = fm.get(product.id, 0)

#                        #** Regroupement des suggestions ***********************
#                        #if regroupement:
#                        if state=="regrouper_suggestion":
#                            if qt_fs!=0:
#                                id=self._regrouper_suggestion(cr, uid, date, product, 'fs', qt_fs)
#                                if id:
#                                    nb=nb+1
#                            if qt_sa!=0:
#                                id=self._regrouper_suggestion(cr, uid, date, product, 'sa', qt_sa)
#                                if id:
#                                    nb=nb+1
#                        #*******************************************************


                        #** Suggestions multiples du lot ***********************
                        # TODO : Modifier les fs suivantes si trop importantes (ou les supprimer)
#                        if state=="multiple_lot":
#                            if qt_fs!=0:
#                                rep=self._multiple_lot(cr, uid, date, product, 'fs', qt_fs)
#                                if rep:
#                                    nb=nb+1
                        #*******************************************************


                        if date==dates[0]:
                            stock_theorique[product.id] = qt_stock - product.is_stock_secu
                        
                        if product.id==product_id_test:
                            print "stock_theorique avant calcul=",stock_theorique[product.id]

                        stock_theorique[product.id] = stock_theorique[product.id] - qt_cde_cli + qt_fl - qt_fm + qt_fs + qt_sa - qt_ft

                        #** Uniquement pour le debuggage à l'écran *****************
                        if product.id==product_id_test:
                            print str(product.id)+"\t"+ \
                                str(date)+"\t"+ \
                                "cde_cli:"     +str(qt_cde_cli)+"\t"+ \
                                "fl:"          +str(qt_fl)+"\t"+ \
                                "fm:"          +str(qt_fm)+"\t"+ \
                                "fs:"          +str(qt_fs)+"\t"+ \
                                "sa:"          +str(qt_sa)+"\t"+ \
                                "ft:"          +str(qt_ft)+"\t"+ \
                                "theorique:"   +str(stock_theorique[product.id])
                        #***********************************************************

                        #** Création des suggestions *******************************
                        if stock_theorique[product.id]<0:
                            #id=self._creer_suggestion(cr, uid, num_od, product, -stock_theorique[product.id], date)
                            qt=self._creer_suggestion(product, -stock_theorique[product.id], date)
                            #TODO : Le stock dépend de la quantité réélement créée en tenant comte du lot (à revoir à ce momement là)
                            stock_theorique[product.id]=stock_theorique[product.id]+qt
                            if product.id==product_id_test:
                                print "Création qt=",qt,stock_theorique[product.id]
                            num_od=num_od+1
                            nb=nb+1
                        if product.id==product_id_test:
                            print "stock_theorique=",stock_theorique[product.id]
                        #***********************************************************

                print "##### Fin Boucle state="+str(state)+" : "+str(compteur)+" : nb="+str(nb)+"#####"


                if nb==0:
                    niveau=niveau+1
                    if niveau>=len(states):
                        break
                    else:
                        compteur=0
                        state=states[niveau]


                #if nb==0:
                #    regroupement=True
                #    compteur=0
#               # if nb==0 and regroupement==True:
#                    multiple_lot=True
#                    compteur=0
                compteur=compteur+1
                if compteur>10:
                    break


            x=duree(debut)
            print "Fin du CBN = "+str(x)+"ms" + " / "+ str(int(x/1000))+"s"



            #** Date de fin des SA pendant les jours ouvrés de l'entreprise ****
            sas = prevision_obj.search([('type','=','sa'),])
            for sa in sas:
                new_date=partner_obj.get_date_dispo(company.partner_id, sa.end_date)
                sa.end_date=new_date
            #*******************************************************************


            x=duree(debut)
            print "Fin traitement date de fin des SA = "+str(x)+"ms" + " / "+ str(int(x/1000))+"s"


            #** Date de début des SA en tenant compte du délai de livraison ****
            for sa in sas:
                product=sa.product_id
                if len(product.seller_ids)>0:
                    delay=product.seller_ids[0].delay
                    partner_id=product.seller_ids[0].name
                    new_date = datetime.datetime.strptime(sa.end_date, '%Y-%m-%d')
                    new_date = new_date - datetime.timedelta(days=delay)
                    new_date = new_date.strftime('%Y-%m-%d')
                    new_date = partner_obj.get_date_dispo(product.seller_ids[0].name, new_date)
                    sa.start_date=new_date
            #*******************************************************************

            x=duree(debut)
            print "Fin traitement date de début des SA = "+str(x)+"ms" + " / "+ str(int(x/1000))+"s"





        x=duree(debut)
        print "Durée de traitement = "+str(x)+"ms" + " / "+ str(int(x/1000))+"s"

        #** Action pour retourner à la liste des prévisions ********************
        action =  {
            'name': "Previsions",
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'mrp.prevision',
            'type': 'ir.actions.act_window',
            'domain': '[]',
        }
        return action

