# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning
import datetime
import time
import psycopg2
import sys


#TODO : 
# - Liste des clients livrables avant la création de la liste à servir
# - Gestion du stock A et Q => Attente tests à ce sujet
# - Gestion des certificats => Attente réponse CC

@api.multi
def _acceder_commande(self,id):
    dummy, view_id = self.env['ir.model.data'].get_object_reference('sale', 'view_order_form')
    return {
        'name': "Commande",
        'view_mode': 'form',
        'view_id': view_id,
        'view_type': 'form',
        'res_model': 'sale.order',
        'type': 'ir.actions.act_window',
        'res_id': id,
        'domain': '[]',
    }


#livrable=[('livrable', u'Livrable'),('toutes', u'Toutes')]


class is_liste_servir_client(models.Model):
    _name='is.liste.servir.client'
    _order='name'

    name            = fields.Many2one('res.partner', 'Client')
    liste_servir_id = fields.Many2one('is.liste.servir', 'Liste à servir')
    zip             = fields.Char('Code postal')
    city            = fields.Char('Ville')
    delai_transport = fields.Integer('Délai de transport')
    date_debut      = fields.Date("Date de début d'expédition")
    date_fin        = fields.Date("Date de fin d'expédition")
    livrable        = fields.Boolean("Livrable")

    @api.multi
    def action_creer_liste_servir(self):
        for obj in self:
            liste_servir_obj = self.env['is.liste.servir']

            if obj.name.is_source_location_id:
                is_source_location_id=obj.name.is_source_location_id.id
            else:
                is_source_location=liste_servir_obj._get_default_location()
                is_source_location_id=is_source_location.id
            vals={
                'partner_id'           : obj.name.id,
                'transporteur_id'      : obj.name.is_transporteur_id.id,
                'is_source_location_id': is_source_location_id,
                'date_debut'           : obj.date_debut,
                'date_fin'             : obj.date_fin,
                'livrable'             : obj.livrable,
            }
            liste_servir=liste_servir_obj.create(vals)
            liste_servir.action_importer_commandes()

            obj.liste_servir_id=liste_servir.id

            return {
                'name': "Liste à servir",
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'is.liste.servir',
                'type': 'ir.actions.act_window',
                'res_id': liste_servir.id,
            }


    @api.multi
    def action_voir_liste_servir(self):
        for obj in self:
            return {
                'name': "Liste à servir",
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'is.liste.servir',
                'type': 'ir.actions.act_window',
                'res_id': obj.liste_servir_id.id,
            }







class is_liste_servir(models.Model):
    _name='is.liste.servir'
    _order='name desc'

    @api.model
    def _get_default_location(self):
        company_id = self.env.user.company_id.id
        warehouse_obj = self.env['stock.warehouse']
        warehouse_id = warehouse_obj.search([('company_id','=',company_id)])
        location = warehouse_id.out_type_id and  warehouse_id.out_type_id.default_location_src_id
        return location and location or False

    name                   = fields.Char("N°", readonly=True)
    partner_id             = fields.Many2one('res.partner', 'Client', required=True)
    date_debut             = fields.Date("Date de début d'expédition")
    date_fin               = fields.Date("Date de fin d'expédition", required=True)
    livrable               = fields.Boolean("Livrable")
    transporteur_id        = fields.Many2one('res.partner', 'Transporteur')
    message                = fields.Text("Message")
    commentaire            = fields.Text("Commentaire")
    state                  = fields.Selection([('creation', u'Création'),('analyse', u'Analyse'),('traite', u'Traité')], u"État", readonly=True, select=True)
    order_ids              = fields.One2many('sale.order', 'is_liste_servir_id', 'Commandes générées', readonly=False)
    line_ids               = fields.One2many('is.liste.servir.line', 'liste_servir_id', u"Lignes")
    uc_ids                 = fields.One2many('is.liste.servir.uc', 'liste_servir_id', u"UCs")
    um_ids                 = fields.One2many('is.liste.servir.um', 'liste_servir_id', u"UMs")
    is_source_location_id  = fields.Many2one('stock.location', 'Source Location', default=_get_default_location) 
    poids_brut             = fields.Float('Poids brut', compute='_compute', readonly=True, store=False)
    poids_net              = fields.Float('Poids net' , compute='_compute', readonly=True, store=False)
    info_client            = fields.Text("Information client complèmentaire")


    def _date_fin():
        now = datetime.date.today()                 # Date du jour
        date_fin = now + datetime.timedelta(days=1) # J+1
        return date_fin.strftime('%Y-%m-%d')        # Formatage

    _defaults = {
        'state': 'creation',
        'date_fin':  _date_fin(),
        'livrable':  'livrable',
    }



    @api.depends('line_ids')
    def _compute(self):
        for obj in self:
            poids_brut = 0
            poids_net  = 0
            for line in obj.line_ids:
                poids_brut = poids_brut + line.quantite * line.product_id.weight
                poids_net  = poids_net  + line.quantite * line.product_id.weight_net
            obj.poids_brut = poids_brut
            obj.poids_net  = poids_net




    def onchange_partner_id(self, cr, uid, ids, partner_id, context=None):
        res  = {}
        vals = {}
        if partner_id:
            partner = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
            if partner.is_source_location_id:
                vals.update({'is_source_location_id': partner.is_source_location_id })

            if partner.is_transporteur_id:
                vals.update({'transporteur_id': partner.is_transporteur_id })
        res['value']=vals
        return res



    def _message(self,partner_id,vals):
        if partner_id:
            message=""
            r=self.env['is.liste.servir.message'].search([['name', '=', partner_id]])
            for l in r:
                message=message+l.message+'\n'

            partner=self.env['res.partner'].browse(partner_id)
            if partner.is_certificat_matiere:
                message=message+'JOINDRE CERTIFICAT CONFORMITE \n'


            vals["message"]=message




        return vals


    #def create(self, cr, uid, vals, context=None):

    @api.model
    def create(self, vals):
        if "partner_id" in vals:
            vals=self._message(vals["partner_id"], vals)
        data_obj = self.pool.get('ir.model.data')
        sequence_ids = data_obj.search(self._cr, self._uid, [('name','=','is_liste_servir_seq')])
        if sequence_ids:
            sequence_id = data_obj.browse(self._cr, self._uid, sequence_ids[0]).res_id
            vals['name'] = self.pool.get('ir.sequence').get_id(self._cr, self._uid, sequence_id, 'id')
        new_id = super(is_liste_servir, self).create(vals)

        return new_id


    @api.multi
    def write(self,vals):
        cr = self._cr
        if "partner_id" in vals:
            vals=self._message(vals["partner_id"], vals)
        res=super(is_liste_servir, self).write(vals)
        for obj in self:
            if 'line_ids' in vals or not obj.uc_ids:
                #La procédure sotckée permet de gérer le regoupement des UC
                SQL="""
                    CREATE OR REPLACE FUNCTION fmixer(mixer boolean, id integer) RETURNS integer AS $$
                            BEGIN
                                IF mixer = True THEN
                                    RETURN 0;
                                ELSE
                                    RETURN id;
                                END IF;
                            END;
                    $$ LANGUAGE plpgsql;

                    select uc_id,um_id,fmixer(mixer,id), sum(nb_uc),sum(nb_um) 
                    from is_liste_servir_line 
                    where liste_servir_id="""+str(obj.id)+"""  
                    group by uc_id,um_id,fmixer(mixer,id);
                """

                #** Création du tableau des UC *************************************
                for row in obj.uc_ids:
                    row.unlink()
                cr.execute(SQL)
                result = cr.fetchall()
                for r in result:
                    vals={
                        'liste_servir_id': obj.id,
                        'uc_id': r[0],
                        'um_id': r[1],
                        'nb_uc': r[3],
                        'nb_um': r[4],
                    }
                    self.env['is.liste.servir.uc'].create(vals)
                #*******************************************************************


            if 'line_ids' in vals or 'uc_ids' in vals or not obj.um_ids:

                #** Création du tableau des UM *************************************
                for row in obj.um_ids:
                    row.unlink()
                r={}
                for row in obj.uc_ids:
                    if row.mixer:
                        k=1000+row.um_id.id
                    else:
                        k=2000+row.id
                    um_id=row.um_id.id
                    if k in r:
                        nb_um=r[k]['nb_um']+row.nb_um
                    else:
                        nb_um=row.nb_um
                    r[k]={'um_id': um_id, 'nb_um': nb_um}

                for k in r:
                    vals={
                        'liste_servir_id': obj.id,
                        'um_id': r[k]['um_id'],
                        'nb_um': r[k]['nb_um'],
                    }
                    self.env['is.liste.servir.um'].create(vals)
                #*******************************************************************

        return res






    @api.multi
    def _get_sql(self,obj):
        SQL="""
            select  sol.order_id, 
                    sol.product_id, 
                    sol.is_client_order_ref,
                    sol.is_date_livraison, 
                    sol.is_date_expedition, 
                    sol.product_uom_qty, 
                    sol.price_unit, 
                    sol.is_justification
            from sale_order so inner join sale_order_line sol on so.id=sol.order_id 
            where so.partner_id="""+str(obj.partner_id.id)+""" 
                  and so.state='draft' 
                  and sol.is_date_expedition<='"""+str(obj.date_fin)+"""' 
                  and sol.product_id>0
                  and sol.is_type_commande='ferme' 
                  and so.is_type_commande!='ls' 
        """
        #if obj.order_id:
        #    SQL=SQL+" and so.id!="+str(obj.order_id.id)+" "
        if obj.date_debut:
            SQL=SQL+" and sol.is_date_expedition>='"+str(obj.date_debut)+"' "

        #SQL=SQL+"group by sol.order_id,sol.product_id, sol.is_client_order_ref "


        if obj.partner_id.is_caracteristique_bl=='cde_client':
            OrderBy="sol.is_client_order_ref"
        else:
            OrderBy="sol.product_id"
        SQL=SQL+"order by "+OrderBy
        return SQL


    @api.multi
    def action_importer_commandes(self):
        cr = self._cr
        for obj in self:


            #** Connexion à Dynacase *******************************************
            if obj.partner_id.is_certificat_matiere:
                uid=self._uid
                user=self.env['res.users'].browse(uid)
                password=user.company_id.is_dynacase_pwd
                cnx=False
                try:
                    cnx = psycopg2.connect("host='dynacase' port=5432 dbname='freedom' user='dynacaseowner' password='"+password+"'")
                except:
                    raise Warning("Impossible de se connecter à Dynacase")
                cursor = cnx.cursor()
            #*******************************************************************


            for row in obj.line_ids:
                row.unlink()
            SQL=self._get_sql(obj)
            cr.execute(SQL)
            result = cr.fetchall()
            line_obj = self.env['is.liste.servir.line']
            for row in result:
                product_id=row[1]

                #** Recherche du certificat matière ****************************
                certificat_matiere=False
                if obj.partner_id.is_certificat_matiere:
                    product=self.env['product.product'].browse(product_id)
                    SQL="""
                        select id
                        from doc69106
                        where doctype='F' and locked='0' and cmc_codepg='"""+product.is_code+"""' limit 1
                    """
                    cursor.execute(SQL)

                    for row2 in cursor:
                        certificat_matiere=row2[0]
                #***************************************************************

                stock01 = self.env['product.product'].get_stock(product_id,'f', '01')
                stocka  = self.env['product.product'].get_stock(product_id,'f')
                stockq  = self.env['product.product'].get_stock(product_id,'t')
                qt=row[5]

                livrable=False
                if qt<=stocka:
                    livrable=True


                test=True
                if obj.livrable==True and livrable==False:
                    test=False

                if test:
                    vals={
                        'liste_servir_id'   : obj.id,
                        'order_id'          : row[0],
                        'product_id'        : row[1],
                        'client_order_ref'  : row[2],
                        'date_livraison'    : row[3],
                        'date_expedition'   : row[4],
                        'prix'              : row[6],
                        'justification'     : row[7],
                        'quantite'          : qt,
                        'livrable'          : livrable,
                        'stock01'           : stock01,
                        'stocka'            : stocka,
                        'stockq'            : stockq,
                        'certificat_matiere': certificat_matiere,
                    }
                    line_obj.create(vals)
            obj.state="analyse"







    @api.multi
    def action_generer_bl(self):
        cr = self._cr
        for obj in self:
            obj.order_ids.unlink()
            SQL=self._get_sql(obj)
            cr.execute(SQL)
            result = cr.fetchall()
            Test=True
            for line in obj.line_ids:
                key1=str(line.order_id.id)+"-"+str(line.product_id.id)
                anomalie="Commande non trouvée"
                for order in result:
                    key2=str(order[0])+"-"+str(order[1])
                    if key1==key2:
                        anomalie=""
                        if line.quantite>order[3]:
                            anomalie="Qt en commande = "+ str(order[3])
                line.anomalie=anomalie
                if anomalie!="":
                    Test=False
            #** Accèder à la liste des commandes générées **********************
            if Test:
                self.generer_bl(obj)
                obj.state="traite"
                ids=[]
                for order in obj.order_ids:
                    ids.append(order.id)
                res= {
                    'domain': "[('id','in',[" + ','.join(map(str, list(ids))) + "])]",
                    'name': 'Commandes',
                    'view_mode': 'tree,form',
                    'view_type': 'form',
                    'context': {'tree_view_ref': 'sale.view_order_tree'},
                    'res_model': 'sale.order',
                    'type': 'ir.actions.act_window',
                }
                return res
            #*******************************************************************





    @api.multi
    def generer_bl(self,obj):
        cr = self._cr
        uid = self._uid
        ids = self._ids
        context = self._context
        order_line_obj = self.pool.get('sale.order.line')
        order_obj = self.pool.get('sale.order')
        vals={}
        lines = []
        mem=''
        for line in obj.line_ids:
            key=''
            if obj.partner_id.is_caracteristique_bl=='cde_odoo':
                key=''
            if obj.partner_id.is_caracteristique_bl=='cde_client':
                key=str(line.client_order_ref)
            if obj.partner_id.is_caracteristique_bl=='ref_article':
                key=str(line.product_id.id)
            if mem!=key:
                if vals:
                    new_id = order_obj.create(cr, uid, vals, context=context)
                    vals={}
                    lines = []
                mem=key


            quotation_line = order_line_obj.product_id_change(cr, uid, ids, obj.partner_id.property_product_pricelist.id, 
                                                              line.product_id.id, 0, False, 0, False, '', obj.partner_id.id, 
                                                             False, True, False, False, False, False, context=context)['value']
            if 'tax_id' in quotation_line:
                quotation_line.update({'tax_id': [[6, False, quotation_line['tax_id']]]})
            quotation_line.update({
                'product_id'          : line.product_id.id, 
                'product_uom_qty'     : line.quantite,
                'is_date_livraison'   : line.date_livraison,
                'is_type_commande'    : 'ferme',
                'is_client_order_ref' : line.client_order_ref,
                'price_unit'          : line.prix,
                'is_justification'    : line.justification,
            })
            lines.append([0,False,quotation_line]) 

            values = {
                'partner_id': obj.partner_id.id,
                'is_source_location_id': obj.is_source_location_id.id,
                'client_order_ref'     : obj.name,
                'is_liste_servir_id'   : obj.id,
                'origin'               : obj.name,
                'order_line'           : lines,
                'picking_policy'       : 'direct',
                'order_policy'         : 'picking',
                'is_transporteur_id'   : obj.transporteur_id.id,
                'is_type_commande'     : 'ls',
                'is_info_client'       : obj.info_client,
            }
            vals.update(values)
        if vals:
            new_id = order_obj.create(cr, uid, vals, context=context)

        #** Supprimer les lignes des commandes d'origine ***********************
        SQL="""
            select sol.order_id, sol.product_id, sol.product_uom_qty, sol.id
            from sale_order so inner join sale_order_line sol on so.id=sol.order_id
            where so.partner_id="""+str(obj.partner_id.id)+""" and so.state='draft' 
                  and sol.is_date_expedition<='"""+str(obj.date_fin)+"""' and sol.product_id>0
        """
        if obj.date_debut:
            SQL=SQL+" and sol.is_date_expedition>='"+str(obj.date_debut)+"' "
        cr.execute(SQL)
        result = cr.fetchall()
        for line in obj.line_ids:
            key1=str(line.order_id.id)+"-"+str(line.product_id.id)
            quantite=line.quantite
            for order in result:
                key2=str(order[0])+"-"+str(order[1])
                if key1==key2 and quantite>=0:
                    order_line=self.env['sale.order.line'].search([('id', '=', order[3])])
                    qty=order_line.product_uom_qty
                    if quantite>=qty:
                        order_line.unlink()
                    else:
                        order_line.product_uom_qty=qty-quantite
                    quantite=quantite-qty
        #***********************************************************************


class is_liste_servir_line(models.Model):
    _name='is.liste.servir.line'
    _order='product_id'


    @api.depends('product_id','quantite')
    def _compute(self):
        cr = self._cr
        for obj in self:
            if obj.product_id:
                mold_dossierf=False
                if obj.product_id.is_dossierf_id:
                    mold_dossierf=obj.product_id.is_dossierf_id.name
                if obj.product_id.is_mold_id:
                    mold_dossierf=obj.product_id.is_mold_id.name
                obj.mold_dossierf=mold_dossierf

                SQL="""
                    select pa.ul,pa.qty,pa.ul_container,pa.rows*pa.ul_qty
                    from product_product pp left outer join product_packaging pa on pp.product_tmpl_id=pa.product_tmpl_id 
                    where pp.id="""+str(obj.product_id.id)+"""
                    limit 1
                """
                cr.execute(SQL)
                result = cr.fetchall()
                for row in result:


                    if row[0]:
                        qt=obj.quantite
                        stock01_uc = obj.stock01
                        stocka_uc  = obj.stocka
                        stockq_uc  = obj.stockq
                        uc=row[1]
                        if uc!=0:
                            nb_uc=qt/uc
                            stock01_uc = stock01_uc/uc
                            stocka_uc  = stocka_uc/uc
                            stockq_uc  = stockq_uc/uc
                        nb_um=row[3]
                        if row[1]!=0 and row[3]!=0:
                            nb_um=qt/(row[1]*row[3])
                        obj.uc_id     = row[0]
                        obj.nb_uc     = nb_uc
                        obj.um_id     = row[2]
                        obj.nb_um     = nb_um
                        obj.stock01_uc = stock01_uc
                        obj.stocka_uc  = stocka_uc
                        obj.stockq_uc  = stockq_uc


    liste_servir_id    = fields.Many2one('is.liste.servir', 'Liste à servir', required=True, ondelete='cascade')
    product_id         = fields.Many2one('product.product', 'Article', required=True, readonly=True)

    mold_id            = fields.Many2one('is.mold', 'Moule'          , related='product_id.is_mold_id', readonly=True)
    dossierf_id        = fields.Many2one('is.dossierf', 'Dossier F'  , related='product_id.is_dossierf_id', readonly=True)
    mold_dossierf      = fields.Char('Moule / Dossier F', compute='_compute', readonly=True, store=True)

    stock01            = fields.Float('Stock 01 US' , help="Stock 01 en US")
    stocka             = fields.Float('Stock A US'  , help="Stock A en US")
    stockq             = fields.Float('Stock Q US'  , help="Stock Q en US")

    stock01_uc         = fields.Float('Stock 01 UC' , help="Stock 01 en UC", compute='_compute', readonly=True, store=True)
    stocka_uc          = fields.Float('Stock A UC'  , help="Stock A en UC" , compute='_compute', readonly=True, store=True)
    stockq_uc          = fields.Float('Stock Q UC'  , help="Stock Q en UC" , compute='_compute', readonly=True, store=True)

    date_livraison     = fields.Date('Date de livraison', readonly=True)
    quantite           = fields.Float('Qt Cde US')
    livrable           = fields.Boolean("Livrable")
    date_expedition    = fields.Date("Date d'expédition"   , readonly=True)
    prix               = fields.Float("Prix", digits=(14,4), readonly=True)
    justification      = fields.Char('Justification')
    uc_id              = fields.Many2one('product.ul', 'UC'      , compute='_compute', readonly=True, store=True)
    nb_uc              = fields.Float('Qt Cde UC'                    , compute='_compute', readonly=True, store=True)
    um_id              = fields.Many2one('product.ul', 'UM'      , compute='_compute', readonly=True, store=True)
    nb_um              = fields.Float('Qt Cde UM'                    , compute='_compute', readonly=True, store=True)
    mixer              = fields.Boolean('Mixer', help="L'UM de cet article peut-être mixée avec un autre")
    order_id           = fields.Many2one('sale.order', 'Commande', required=True     , readonly=True)
    client_order_ref   = fields.Char('Cde Client', readonly=True)
    certificat_matiere = fields.Char('Certificat matiere', readonly=True)
    anomalie           = fields.Char('Commentaire')


    #TODO : Le champ HTML pour le certificat matiere ne fonctionne pas en tree view => Enregsitrer l'ID de Dynacase et mettre un bouton pour acceder

    _defaults = {
        'mixer': True,
    }


    @api.multi
    def action_acceder_certificat(self):
        context=self._context
        if 'certificat_matiere' in context:
            docid=context['certificat_matiere']
            return {
                'name': "Certificat",
                'url': "http://dynacase/?sole=Y&app=FDL&action=FDL_CARD&id="+docid,
                'type': 'ir.actions.act_url',
            }


    @api.multi
    def action_acceder_commande(self):
        dummy, view_id = self.env['ir.model.data'].get_object_reference('sale', 'view_order_tree')
        for obj in self:
            ids=[]
            for id in obj.order_ids:
                ids.append(id)


            return _acceder_commande(self,ids)


    @api.multi
    def action_acceder_article(self):
        dummy, view_id = self.env['ir.model.data'].get_object_reference('is_pg_product', 'is_product_template_only_form_view')
        for obj in self:
            return {
                'name': "Article",
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'product.template',
                'type': 'ir.actions.act_window',
                'res_id': obj.product_id.product_tmpl_id.id,
                'domain': '[]',
            }



class is_liste_servir_message(models.Model):
    _name='is.liste.servir.message'
    _order='name'
    _sql_constraints = [('name_uniq','UNIQUE(name)', 'Ce client existe déjà')] 

    name    = fields.Many2one('res.partner', 'Client', required=True)
    message = fields.Text('Message')




class is_liste_servir_uc(models.Model):
    _name='is.liste.servir.uc'
    _order='uc_id'

    liste_servir_id = fields.Many2one('is.liste.servir', 'Liste à servir', required=True, ondelete='cascade')
    uc_id           = fields.Many2one('product.ul', 'UC')
    nb_uc           = fields.Float('Nb UC')
    um_id           = fields.Many2one('product.ul', 'UM')
    nb_um           = fields.Float('Nb UM')
    mixer           = fields.Boolean('Mixer', help="L'UM peut-être mixée avec une autre")

    _defaults = {
        'mixer': False,
    }


class is_liste_servir_um(models.Model):
    _name='is.liste.servir.um'
    _order='um_id,nb_um desc'

    liste_servir_id = fields.Many2one('is.liste.servir', 'Liste à servir', required=True, ondelete='cascade')
    um_id           = fields.Many2one('product.ul', 'UM')
    nb_um           = fields.Float('Nb UM')





