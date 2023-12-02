# -*- coding: utf-8 -*-
import datetime
from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning
import base64
import csv, cStringIO
from datetime import date,datetime,timedelta
import unicodedata
import math


_MOIS=['Janvier', 'Février','Mars','Avril','Mai', 'Juin','Juillet','Aout','Septembre','Octobre','Novembre','Décembre']

class is_mini_delta_dore(models.Model):
    _name = "is.mini.delta.dore"
    _order='name desc'

    name            = fields.Char('N° traitement', readonly=True)
    partner_id      = fields.Many2one('res.partner', 'Client', required=True, domain=[('customer','=',True),('is_company','=',True)])
    file_ids        = fields.Many2many('ir.attachment', 'is_mini_delta_dore_file_rel', 'doc_id', 'file_id', 'Fichier à traiter')
    nb_jours        = fields.Integer('Nombre de jours dans le fichier')
    nb_semaines     = fields.Integer('Nombre de semaines dans le fichier')
    nb_mois         = fields.Integer('Nombre de mois dans le fichier')
    edi_id          = fields.Many2one('is.edi.cde.cli', 'EDI généré', readonly=True)
    line_ids        = fields.One2many('is.mini.delta.dore.line'  , 'mini_delta_dore_id', u"Lignes")
    besoin_ids      = fields.One2many('is.mini.delta.dore.besoin', 'mini_delta_dore_id', u"Besoins")


    @api.model
    def create(self, vals):
        data_obj = self.env['ir.model.data']
        sequence_ids = data_obj.search([('name','=','is_mini_delta_dore_seq')])
        if sequence_ids:
            sequence_id = data_obj.browse(sequence_ids[0].id).res_id
            vals['name'] = self.env['ir.sequence'].get_id(sequence_id, 'id')
        obj = super(is_mini_delta_dore, self).create(vals)
        return obj


    @api.multi
    def calcul_action(self):
        cr, uid, context = self.env.args
        for obj in self:
            if obj.edi_id:
                raise Warning('Un EDI a déjà été généré. Il faut le traiter ou le supprimer pour pouvoir lancer un nouveau calcul')
            obj.line_ids.unlink()
            obj.besoin_ids.unlink()
            for attachment in obj.file_ids:
                res=self.traitement(attachment)
            self.creation_edi()


    @api.multi
    def creation_edi(self):
        cr, uid, context = self.env.args
        for obj in self:
            SQL="""
                select
                    l.reference_client,
                    b.date_livraison,
                    b.type_commande,
                    sum(b.commande)
                from is_mini_delta_dore_besoin b inner join is_mini_delta_dore_line l on b.line_id=l.id 
                where b.mini_delta_dore_id="""+str(obj.id)+""" and b.commande!=0
                group by l.reference_client, b.date_livraison, b.type_commande
            """
            cr.execute(SQL)
            result = cr.fetchall()
            datas=''
            for row in result:
                lig=str(row[0])+'\t'+str(row[1])+'\t'+str(row[2])+'\t'+str(row[3])+'\n'
                datas+=lig

            #** Ajout en pièce jointe ******************************************
            name='edi-mini-delta-dore.csv'
            attachment_obj = self.env['ir.attachment']
            model='is.edi.cde.cli'
            vals = {
                'name':        name,
                'datas_fname': name,
                'type':        'binary',
                'file_type':   'text/csv',
                'res_model':   model,
                'datas':       datas.encode('base64'),
            }
            attachment=attachment_obj.create(vals)
            vals = {
                'partner_id': obj.partner_id.id,
                'file_ids' : [(6,0,[attachment.id])],
            }
            edi=self.env['is.edi.cde.cli'].create(vals)
            obj.edi_id=edi.id
            #*******************************************************************

    @api.multi
    def traitement(self, attachment):
        cr, uid, context = self.env.args
        res = []
        for obj in self:
            #** Recherche du prochain jour livrable de ce client ***************
            closing_days = obj.partner_id.num_closing_days(obj.partner_id)
            d = datetime.now()        # Date de jour
            d = d + timedelta(days=1) # Ne pas livrer le jour même => Ajouter 1 jour
            while (int(d.strftime('%w')) in closing_days):
                d = d + timedelta(days=1)
            date_prochaine_livraison=d
            #*******************************************************************

            nb_jours    = obj.nb_jours
            nb_semaines = obj.nb_semaines
            nb_mois     = obj.nb_mois

            attachment=base64.decodestring(attachment.datas)
            attachment=attachment.decode('iso-8859-1').encode('utf8')
            csvfile = attachment.split("\n")
            csvfile = csv.reader(csvfile, delimiter=';')
            #tsemaines={}
            tmardi={}
            tjeudi={}
            tmois={}
            tdates=[]
            for lig, row in enumerate(csvfile):
                if lig==2:
                    annee=date.today().year
                    ct=1
                    for cel in row:
                        if ct==10:
                            #** Recherche du lundi de chaque semaine ***********
                            d=datetime.strptime(cel, '%d/%m/%y')
                            for i in range(0,365):
                                semaine='S'+d.strftime('%W/%Y')
                                #Test si lundi
                                if d.isoweekday()==2:
                                    #tsemaines[semaine]=d
                                    tmardi[semaine]=d
                                if d.isoweekday()==4:
                                    tjeudi[semaine]=d
                                d = d + timedelta(days=+1)   # Date +1 jour
                            #***************************************************

                            #** Recherche du premier jour de chaque mois *******
                            d=datetime.strptime(cel, '%d/%m/%y')
                            for i in range(0,12):
                                d = d.replace(day=1)      # Fixe le jour à 1
                                d = self.premier_mardi(d) # Recherche le premier mardi suivant
                                mois=d.strftime('%m/%Y')
                                tmois[mois]=d
                                d = d + timedelta(days=32) # Ajoute 32 jours => mois suivant
                            #***************************************************


                        #** Dates en jours => Mardi ou jeudi le plus prés précédent ******************
                        if ct>=10 and ct<(10+nb_jours):

                            #** Date premier mardi et jeudi ********************
                            d=datetime.strptime(cel, '%d/%m/%y')

                            weekday = d.isoweekday() # Jour dans la semaine (1=lundi, 7=dimanche)
                            if weekday==1:
                                mardi_jeudi_precedent = d - timedelta(days=4) # lundi => jeudi précédent
                            if weekday==2:
                                mardi_jeudi_precedent = d - timedelta(days=0) # mardi => mardi
                            if weekday==3:
                                mardi_jeudi_precedent = d - timedelta(days=1) # mercredi => mardi précédent
                            if weekday==4:
                                mardi_jeudi_precedent = d - timedelta(days=0) # jeudi => jeudi
                            if weekday==5:
                                mardi_jeudi_precedent = d - timedelta(days=1) # vendredi => jeudi précédent
                            if weekday==6:
                                mardi_jeudi_precedent = d - timedelta(days=2) # samedi => jeudi précédent
                            if weekday==7:
                                mardi_jeudi_precedent = d - timedelta(days=3) # dimanche => jeudi précédent
                            #date_lundi = d - timedelta(days=weekday)  # Date du lundi de la semaine
                            #***************************************************

                            #tdates.append([cel,date_lundi])
                            tdates.append([cel,mardi_jeudi_precedent])
                            annee=mardi_jeudi_precedent.year

                        # if ct>=10 and ct<(10+nb_jours):
                        #     print(ct, d, annee, 'Jour',cel)
                        # if ct>=(10+nb_jours) and ct<(10+nb_jours+nb_semaines):
                        #     print(ct, d, annee, 'Semaine',cel)
                        # if ct>=(10+nb_jours+nb_semaines) and ct<(10+nb_jours+nb_semaines+nb_mois):
                        #     print(ct, d, annee, 'Mois',cel)

                        #* Dates en semaines => Jeudi de la semaine ************
                        if ct>=(10+nb_jours) and ct<(10+nb_jours+nb_semaines):
                            annee=d.year
                            cel=cel.strip()
                            semaine=cel+'/'+str(annee)
                            d=tjeudi[semaine]
                            tdates.append([cel,d])
                            d = d + timedelta(days=7) # Ajoute 7 jours => semaine suivant

                        #* Dates en mois => 1er mardi du mois ******************
                        if ct>=(10+nb_jours+nb_semaines) and ct<(10+nb_jours+nb_semaines+nb_mois):
                            if ct==(10+nb_jours+nb_semaines):
                                d = d - timedelta(days=7) # Enlever 7 jours au début des mois pour ne pas changer d'année
                            annee=d.year
                            mois=cel.strip()
                            num_mois=_MOIS.index(mois)+1
                            num_mois=str(num_mois).zfill(2)
                            mois_annee=num_mois+'/'+str(annee)
                            date_mois=tmois[mois_annee]
                            tdates.append([mois,date_mois])
                            d = date_mois + timedelta(days=32) # Ajoute 32 jours => mois suivant
                        ct+=1

                if lig>2:
                    ct=1
                    reference_client=''
                    product={}
                    line={}
                    anomalie   = []
                    stock      = 0
                    stock_mini = 0
                    stock_maxi = 0
                    stock_date = 0
                    for cel in row:
                        if ct==1:
                            reference_client=cel.strip()
                            product = self.env['product.product'].search([
                                ('is_ref_client', '=', reference_client),
                                ('is_client_id' , '=', obj.partner_id.id),
                            ],limit=1,order='id desc')
                            order = self.env['sale.order'].search([
                                ('partner_id.is_code', '=', obj.partner_id.is_code),
                                ('is_ref_client'     , '=', reference_client),
                                ('is_type_commande'  , '=', 'ouverte'),
                            ],limit=1)
                            if order:
                                product=order.is_article_commande_id
                        if ct==2:
                            designation_client=cel.strip()
                        if ct==3:
                            indice_client=cel.strip()
                        if ct==5:
                            multiple=self.txt2integer(cel)
                        if ct==6:
                            stock=self.txt2integer(cel)
                        if ct==7:
                            stock_mini=self.txt2integer(cel)
                        if ct==8:
                            stock_maxi=self.txt2integer(cel)
                        if ct==10:
                            #Recherche multiple de livraison *******************
                            multiple_livraison=0
                            for l in product.is_client_ids:
                                if l.client_id.id==obj.partner_id.id:
                                    multiple_livraison=l.multiple_livraison

                            #***************************************************
                            if indice_client!=product.is_ind_plan:
                                anomalie.append(u'Indice différent')
                            if stock<stock_mini:
                                anomalie.append(u'Stock<Mini')
                            if stock>stock_maxi:
                                anomalie.append(u'Stock>Maxi')
                            if multiple_livraison==0:
                                anomalie.append(u'Multiple Plastigray=0')
                            else:
                                if round(multiple/multiple_livraison,2)!=round(multiple/multiple_livraison):
                                    anomalie.append(u'Multiple Client incohérent avec multiple Plastigray')
                            vals={
                                'mini_delta_dore_id': obj.id,
                                'reference_client'  : reference_client,
                                'designation_client': designation_client,
                                'indice_client'     : indice_client,
                                'multiple'          : multiple,
                                'stock'             : stock,
                                'stock_mini'        : stock_mini,
                                'stock_maxi'        : stock_maxi,
                                'product_id'        : product.id,
                                'indice'            : product.is_ind_plan,
                                'multiple_livraison': multiple_livraison,
                                'order_id'          : order.id,
                                'anomalie'          : ', '.join(anomalie),
                            }
                            line=self.env['is.mini.delta.dore.line'].create(vals)
                            stock_date=stock-stock_mini

                        if ct>=10 and ct<(10+nb_jours+nb_semaines+nb_mois):

                            #** Pour les mois, il faut éclater en 4 lignes *****
                            eclate=1
                            if ct>=(10+nb_jours+nb_semaines) and ct<(10+nb_jours+nb_semaines+nb_mois):
                                eclate=4
                            #***************************************************

                            for i in range(0,eclate):
                                besoin         = self.txt2integer(cel)
                                date_origine   = tdates[ct-10][0]
                                d              = tdates[ct-10][1]
                                date_calculee  = d + timedelta(days=i*7) # Ajoute 7 jours => semaine suivant
                                besoin_calcule = besoin/eclate
                                vals={
                                    'mini_delta_dore_id': obj.id,
                                    'line_id'           : line.id,
                                    'product_id'        : product.id,
                                    'multiple'          : multiple,
                                    'stock'             : stock,
                                    'stock_mini'        : stock_mini,
                                    'stock_maxi'        : stock_maxi,
                                    'product_id'        : product.id,
                                    'besoin'            : besoin,
                                    'date_origine'      : date_origine,
                                    'date_calculee'     : date_calculee,
                                    'besoin_calcule'    : besoin_calcule,
                                }
                                self.env['is.mini.delta.dore.besoin'].create(vals)
                        ct+=1


            #** Calcul du stock à date et des livraisons ***********************
            for line in obj.line_ids:
                SQL="""
                    select
                        id,
                        line_id,
                        product_id,
                        multiple,
                        stock,
                        stock_mini,
                        stock_maxi,
                        date_calculee,
                        besoin_calcule
                    from is_mini_delta_dore_besoin 
                    where line_id="""+str(line.id)+""" 
                    order by date_calculee, id
                """
                cr.execute(SQL)
                result = cr.fetchall()
                lig=0
                for row in result:
                    b=self.env['is.mini.delta.dore.besoin'].browse(row[0])
                    if b:
                        lig=lig+1
                        multiple       = row[3]
                        stock          = row[4]
                        stock_mini     = row[5]
                        stock_maxi     = row[6]
                        date_calculee  = row[7]
                        besoin_calcule = row[8]
                        date_calculee=datetime.strptime(date_calculee, '%Y-%m-%d')
                        if lig==1:
                            stock_date=stock-stock_mini
                        stock_date     = stock_date - besoin_calcule
                        commande       = 0
                        date_livraison = False
                        type_commande  = False
                        if stock_date<0:
                            type_commande  = 'previsionnel'
                            commande=-stock_date
                            x=float(commande)/float(multiple)
                            x=math.ceil(x)
                            commande=multiple*x
                            date_livraison=date_calculee
                            if date_calculee<=date_prochaine_livraison:
                                type_commande  = 'ferme'
                                date_livraison=date_prochaine_livraison
                                #commande=commande+multiple # Ajoute 1 multiple si commande ferme
                            stock_date=stock_date+commande
                        anomalie = []
                        if stock_date<0:
                            anomalie.append(u'Stock<Mini')
                        if (stock_date+stock_mini)>stock_maxi:
                            anomalie.append(u'Stock>Maxi')
                        vals={
                            'stock_date'        : stock_date+stock_mini,
                            'stock_date_mini'   : stock_date,
                            'type_commande'     : type_commande,
                            'commande'          : commande,
                            'date_livraison'    : date_livraison,
                            'anomalie'          : ', '.join(anomalie),
                        }
                        b.write(vals)
            #*******************************************************************
        return res


    @api.multi
    def txt2integer(self,txt):
        txt=str(txt).strip()
        txt = unicode(txt,'utf-8')
        txt = unicodedata.normalize('NFD', txt).encode('ascii', 'ignore')
        txt=txt.replace(u' ', '')
        try:
            x = int(txt)
        except ValueError:
            x=0
        return x


    @api.multi
    def premier_mardi(self,d):
        while (d.isoweekday()!=2):
            d = d + timedelta(days=1)
        return d


    @api.multi
    def besoins_action(self):
        cr, uid, context = self.env.args
        for obj in self:
            return {
                'name': u'Besoins mini Delta Dore',
                'view_mode': 'tree,form',
                'view_type': 'form',
                'res_model': 'is.mini.delta.dore.besoin',
                'domain': [
                    ('mini_delta_dore_id'  ,'=', obj.id),
                ],
                'type': 'ir.actions.act_window',
                'limit': 1000,
            }



class is_mini_delta_dore_line(models.Model):
    _name='is.mini.delta.dore.line'
    _order='id'

    mini_delta_dore_id = fields.Many2one('is.mini.delta.dore', 'Mini Delta Dore', required=True, ondelete='cascade', readonly=True)
    reference_client   = fields.Char('Référence client')
    designation_client = fields.Char('Désignation client')
    indice_client      = fields.Char('Indice Client')
    multiple           = fields.Integer('Multiple Client')
    stock              = fields.Integer('Stock Client')
    stock_mini         = fields.Integer('Stock mini')
    stock_maxi         = fields.Integer('Stock maxi')
    product_id         = fields.Many2one('product.product', 'Article')
    indice             = fields.Char('Indice Plastigray')
    multiple_livraison = fields.Integer('Multiple Plastigray')
    order_id           = fields.Many2one('sale.order', 'Commande ouverte')
    anomalie           = fields.Char('Anomalie')
    besoin_ids         = fields.One2many('is.mini.delta.dore.besoin', 'line_id', u"Besoins")


    @api.multi
    def besoins_action(self):
        cr, uid, context = self.env.args
        for obj in self:
            return {
                'name': u'Besoins mini Delta Dore '+obj.product_id.is_code,
                'view_mode': 'tree,form',
                'view_type': 'form',
                'res_model': 'is.mini.delta.dore.besoin',
                'domain': [
                    ('line_id','=', obj.id),
                ],
                'type': 'ir.actions.act_window',
                'limit': 1000,
            }


class is_mini_delta_dore_besoin(models.Model):
    _name='is.mini.delta.dore.besoin'
    _order='product_id,date_calculee,id'

    mini_delta_dore_id = fields.Many2one('is.mini.delta.dore'     , 'Mini Delta Dore'     , required=True, ondelete='cascade', readonly=True)
    line_id            = fields.Many2one('is.mini.delta.dore.line', 'Mini Delta Dore Line', required=True, ondelete='cascade', readonly=True)
    product_id         = fields.Many2one('product.product', 'Article')
    multiple           = fields.Integer('Multiple Client')
    stock              = fields.Integer('Stock Client')
    stock_mini         = fields.Integer('Stock mini')
    stock_maxi         = fields.Integer('Stock maxi')
    multiple_livraison = fields.Integer('Multiple Plastigray')
    besoin             = fields.Integer('Besoin')
    date_origine       = fields.Char('Date origine')
    date_calculee      = fields.Date('Date calculée')
    besoin_calcule     = fields.Integer('Besoin calculé')
    stock_date         = fields.Integer('Stock à date')
    stock_date_mini    = fields.Integer('Stock à date - Mini')
    type_commande      = fields.Selection([('ferme', 'Ferme'),('previsionnel', 'Prév.')], "Type")
    commande           = fields.Integer('Quantité à livrer')
    date_livraison     = fields.Date('Date de livraison')
    anomalie           = fields.Char('Anomalie')
