# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning
import datetime
import base64
import MySQLdb

#TODO : 
# - Une fois l'inventaire validé, plus rien n'est modifiable
# - Faire une doc : Saisie en US ou UC, sasie unqiuement au clavier et tri des lignes



class is_inventaire(models.Model):
    _name='is.inventaire'
    _order='name desc'

    name          = fields.Char("N°", readonly=True)
    date_creation = fields.Date("Date de l'inventaire", required=True)
    createur_id   = fields.Many2one('res.users', 'Créé par', readonly=True)
    commentaire   = fields.Text('Commentaire')
    line_ids      = fields.One2many('is.inventaire.feuille'  , 'inventaire_id', u"Lignes")
    inventory_ids = fields.One2many('is.inventaire.inventory', 'inventaire_id', u"Inventaires Odoo")
    ecart_ids     = fields.One2many('is.inventaire.ecart'    , 'inventaire_id', u"Ecarts")
    state         = fields.Selection([('creation', u'Création'),('cloture', u'Cloturé'),('traite', u'Traité')], u"État", readonly=True, select=True)

    def _date_creation():
        return datetime.date.today() # Date du jour

    _defaults = {
        'date_creation': _date_creation(),
        'createur_id': lambda obj, cr, uid, ctx=None: uid,
        'state': 'creation',
    }


    @api.model
    def create(self, vals):

        #Blocage si inventaire existe déja
        inventaires=self.env['is.inventaire'].search([ ['state', '=', 'creation'] ])
        if len(inventaires)>1:
            raise Warning(u"Un inventaire en cours existe déjà !")

        data_obj = self.pool.get('ir.model.data')
        sequence_ids = data_obj.search(self._cr, self._uid, [('name','=','is_inventaire_seq')])
        if sequence_ids:
            sequence_id = data_obj.browse(self._cr, self._uid, sequence_ids[0]).res_id
            vals['name'] = self.pool.get('ir.sequence').get_id(self._cr, self._uid, sequence_id, 'id')
        new_id = super(is_inventaire, self).create(vals)
        return new_id



    @api.multi
    def creer_feuille(self,obj):
        dummy, view_id = self.env['ir.model.data'].get_object_reference('is_plastigray', 'is_inventaire_feuille_form_view')
        context=self._context
        if context is None:
            context = {}
        ctx = context.copy()
        ctx.update({'default_inventaire_id': obj.id})
        return {
            'name': "Feuille d'inventaire",
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 'is.inventaire.feuille',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context':ctx,
        }

    @api.multi
    def action_creer_feuille(self):
        for obj in self:
            return self.creer_feuille(obj)



    @api.multi
    def action_fin_inventaire(self):
        for obj in self:
            # ** Calcul des encours ********************************************
            for line in obj.line_ids:
                line.calculer_encours()
            # ** Détermine si les lots sont importés ou calculés ***************
            lots=self.env['is.inventaire.line'].search([ ['inventaire_id','=',obj.id], ['lot_id','!=',False] ])
            nb=len(lots)
            if nb>0:
                self.action_fin_inventaire_avec_lot()
            else:
                self.action_fin_inventaire_sans_lot()



    @api.multi
    def action_fin_inventaire_sans_lot(self):
        cr=self._cr
        for obj in self:
            self.action_calcul_ecart()

            # ** Suppression des inventaires liés à cette importation **********
            for row in obj.inventory_ids:
                row.inventory_id.unlink()
                row.unlink()
            #*******************************************************************

            # ** Recherche de la liste des emplacements ************************
            SQL="""
                select distinct location_id
                from is_inventaire_line
                where inventaire_id='"""+str(obj.id)+"""' 
            """
            cr.execute(SQL)
            res=cr.fetchall()
            # ******************************************************************
            for row in res:
                location_id=row[0]
                # ** Creation inventaire ***************************************
                location=self.env['stock.location'].browse(location_id)
                vals={
                    'name': obj.name+'-'+location.name,
                    'location_id': location_id,
                    'state': 'confirm',
                }
                inventory=self.env['stock.inventory'].create(vals)
                vals={
                    'inventaire_id': obj.id,
                    'inventory_id': inventory.id,
                }
                inventaire_inventory=self.env['is.inventaire.inventory'].create(vals)

                # ** Suppression des données temporaires  **********************
                SQL="delete from is_inventaire_line_tmp"
                cr.execute(SQL)

                # ** Liste des stocks actuels **********************************
                SQL="""
                    select sq.product_id, pt.uom_id, sq.lot_id, spl.create_date, sq.qty
                    from stock_quant sq inner join product_product pp on sq.product_id=pp.id
                                        inner join product_template pt on pp.product_tmpl_id=pt.id
                                        left outer join stock_production_lot spl on sq.lot_id=spl.id
                    where sq.location_id='"""+str(location_id)+"""'
                """
                cr.execute(SQL)
                res2=cr.fetchall()
                for row2 in res2:
                    vals={
                        'product_id' : row2[0],
                        'us_id'      : row2[1],
                        'location_id': location_id,
                        'lot_id'     : row2[2],
                        'date_lot'   : row2[3] or datetime.datetime.now(),
                        'qt_us'      : row2[4],
                    }
                    tmp=self.env['is.inventaire.line.tmp'].create(vals)


                # ** Traitement des écarts *************************************
                ecarts=self.env['is.inventaire.ecart'].search([ ['inventaire_id','=',obj.id], ['location_id','=',location_id] ])
                for ecart in ecarts:
                    #Si ecart positif, il faut ajouter des lignes : 
                    if ecart.ecart>0:
                        # ** Il faut créer un lot du nom de l'inventaire *******
                        vals={
                            'name': obj.name,
                            'product_id': ecart.product_id.id,
                        }
                        lot=self.env['stock.production.lot'].create(vals)

                        vals={
                            'product_id' : ecart.product_id.id,
                            'us_id'      : ecart.product_id.product_tmpl_id.uom_id.id,
                            'location_id': location_id,
                            'lot_id'     : lot.id,
                            'date_lot'   : datetime.datetime.now(),
                            'qt_us'      : ecart.ecart,
                        }
                        tmp=self.env['is.inventaire.line.tmp'].create(vals)

                    #Si ecart négatif, il faut enlever les quantités sur les lots les plus anciens
                    if ecart.ecart<0:
                        SQL="""
                            select id,product_id, lot_id, date_lot, qt_us
                            from is_inventaire_line_tmp
                            where location_id='"""+str(location_id)+"""' and
                                  product_id='"""+str(ecart.product_id.id)+"""'
                            order by date_lot, qt_us
                        """
                        cr.execute(SQL)
                        res2=cr.fetchall()
                        ecart=-ecart.ecart
                        for row2 in res2:
                            line=self.env['is.inventaire.line.tmp'].browse(row2[0])
                            qt=line.qt_us
                            if qt>=ecart:
                                qt_us=qt-ecart
                                ecart=0
                            else:
                                qt_us=0
                                ecart=ecart-qt
                            line.qt_us=qt_us


                # ** Création des inventaires à partir de la table temporaire **
                SQL="""
                    select product_id, us_id, lot_id, sum(qt_us)
                    from is_inventaire_line_tmp
                    where location_id='"""+str(location_id)+"""'
                    group by product_id, us_id, lot_id
                """
                cr.execute(SQL)
                res2=cr.fetchall()
                for row2 in res2:
                    qty=row2[3]
                    vals={
                        'inventory_id'  : inventory.id,
                        'location_id'   : location_id,
                        'product_id'    : row2[0],
                        'product_uom_id': row2[1],
                        'prod_lot_id'   : row2[2],
                        'product_qty'   : qty,
                    }
                    line_id=self.env['stock.inventory.line'].create(vals)

            for feuille in obj.line_ids:
                feuille.state="cloture"
                for line in feuille.line_ids:
                    line.state="cloture"
            obj.state="cloture"







    @api.multi
    def action_fin_inventaire_avec_lot(self):
        cr=self._cr
        for obj in self:
            # ** Suppression des inventaires liés à cette importation **********
            for row in obj.inventory_ids:
                row.inventory_id.unlink()
                row.unlink()
            #*******************************************************************

            # ** Recherche de la liste des emplacements ************************
            SQL="""
                select distinct location_id
                from is_inventaire_line
                where inventaire_id='"""+str(obj.id)+"""' 
            """
            cr.execute(SQL)
            res=cr.fetchall()
            # ******************************************************************
            for row in res:
                # ** Creation inventaire ***************************************
                location_id=row[0]
                location=self.env['stock.location'].browse(location_id)
                vals={
                    'name': obj.name+'-'+location.name,
                    'location_id': location_id,
                    'state': 'confirm',
                }
                inventory=self.env['stock.inventory'].create(vals)
                vals={
                    'inventaire_id': obj.id,
                    'inventory_id': inventory.id,
                }
                new_id=self.env['is.inventaire.inventory'].create(vals)
                # ** Suppression des données temporaires  **********************
                SQL="delete from is_inventaire_line_tmp"
                cr.execute(SQL)

                # ** Liste des saisies de toutes les feuilles ******************
                SQL="""
                    select product_id, us_id, lot_id, sum(qt_us_calc)
                    from is_inventaire_line
                    where inventaire_id='"""+str(obj.id)+"""' and 
                          location_id='"""+str(location_id)+"""' and
                          encours!=True
                    group by product_id, us_id, lot_id 
                """
                cr.execute(SQL)
                res2=cr.fetchall()
                for row2 in res2:
                    vals={
                        'product_id' : row2[0],
                        'us_id'      : row2[1],
                        'location_id': location_id,
                        'lot_id'     : row2[2],
                        'qt_us'      : row2[3],
                    }
                    tmp=self.env['is.inventaire.line.tmp'].create(vals)
                # ** Liste des stocks actuels pour les mettre à 0 **************
                SQL="""
                    select sq.product_id, pt.uom_id, sq.lot_id, sum(sq.qty)
                    from stock_quant sq inner join product_product pp on sq.product_id=pp.id
                                        inner join product_template pt on pp.product_tmpl_id=pt.id
                    where sq.location_id='"""+str(location_id)+"""'
                    group by sq.product_id, pt.uom_id, sq.lot_id 
                """
                cr.execute(SQL)
                res2=cr.fetchall()
                for row2 in res2:
                    vals={
                        'product_id' : row2[0],
                        'us_id'      : row2[1],
                        'location_id': location_id,
                        'lot_id'     : row2[2],
                        'qt_us'      : 0,
                    }
                    tmp=self.env['is.inventaire.line.tmp'].create(vals)
                # ** Création des inventaires à partir de la table temporaire **
                SQL="""
                    select product_id, us_id, lot_id, sum(qt_us)
                    from is_inventaire_line_tmp
                    where location_id='"""+str(location_id)+"""'
                    group by product_id, us_id, lot_id
                """
                cr.execute(SQL)
                res2=cr.fetchall()
                for row2 in res2:
                    qty=row2[3]
                    if qty<0:
                        qty=0
                    vals={
                        'inventory_id'  : inventory.id,
                        'location_id'   : location_id,
                        'product_id'    : row2[0],
                        'product_uom_id': row2[1],
                        'prod_lot_id'   : row2[2],
                        'product_qty'   : qty,
                    }
                    line_id=self.env['stock.inventory.line'].create(vals)

            self.action_calcul_ecart()

            for feuille in obj.line_ids:
                feuille.state="cloture"
                for line in feuille.line_ids:
                    line.state="cloture"
            obj.state="cloture"


    @api.multi
    def action_calcul_ecart(self):
        cr=self._cr
        for obj in self:
            for row in obj.ecart_ids:
                row.unlink()


            # ** Recherche de la liste des emplacements ************************
            SQL="""
                select distinct location_id
                from is_inventaire_line
                where inventaire_id='"""+str(obj.id)+"""' 
            """
            cr.execute(SQL)
            res=cr.fetchall()
            # ******************************************************************
            for row in res:
                location_id=row[0]
                SQL="""
                    select 
                        pt.is_code,
                        pt.name,
                        pt.uom_id,
                        (   select sum(sq.qty) 
                            from stock_quant sq
                            where sq.location_id='"""+str(location_id)+"""' and
                                  sq.product_id=pp.id
                        ),
                        (   select sum(qt_us_calc) 
                            from is_inventaire_line iil
                            where iil.location_id='"""+str(location_id)+"""' and
                                  iil.product_id=pp.id and 
                                  iil.inventaire_id='"""+str(obj.id)+"""' and
                                  iil.encours!=True
                        ),
                        pp.id
                    from product_product pp inner join product_template pt on pp.product_tmpl_id=pt.id
                    where pp.id>0
                """
                cr.execute(SQL)
                res2=cr.fetchall()
                for row2 in res2:
                    qt_odoo       = row2[3] or 0
                    qt_inventaire = row2[4] or 0
                    ecart         = qt_inventaire-qt_odoo
                    if ecart!=0:
                        vals={
                            'inventaire_id': obj.id,
                            'location_id'  : location_id,
                            'product_id'   : row2[5],
                            'code'         : row2[0],
                            'designation'  : row2[1],
                            'us_id'        : row2[2],
                            'qt_odoo'      : qt_odoo,
                            'qt_inventaire': qt_inventaire,
                            'ecart'        : ecart,

                        }
                        tmp=self.env['is.inventaire.ecart'].create(vals)



    @api.multi
    def action_valide_inventaire(self):
        for obj in self:

            for row in obj.inventory_ids:
                row.inventory_id.action_done()

            for feuille in obj.line_ids:
                feuille.state="traite"
                for line in feuille.line_ids:
                    line.state="traite"
            obj.state="traite"





class is_inventaire_feuille(models.Model):
    _name='is.inventaire.feuille'
    _order='name'

    inventaire_id   = fields.Many2one('is.inventaire', 'Inventaire', required=True, ondelete='cascade', readonly=True)
    name            = fields.Char('Numéro de feuille', required=True)
    date_creation   = fields.Date("Date de création"         , readonly=True)
    createur_id     = fields.Many2one('res.users', 'Créé par', readonly=True)
    fichier         = fields.Binary('Fichier à importer', help=u"Le fichier doit-être au format CSV. Séparateur virgule avec ces colonnes : article, lot, emplacement, statut, stotck A et stock Q")
    line_ids        = fields.One2many('is.inventaire.line', 'feuille_id', u"Lignes")
    anomalies       = fields.Text('Anomalies')
    state           = fields.Selection([('creation', u'Création'),('cloture', u'Cloturé'),('traite', u'Traité')], u"État", readonly=True, select=True)

    sequence=1

    def _date_creation():
        return datetime.date.today() # Date du jour

    _defaults = {
        'createur_id': lambda obj, cr, uid, ctx=None: uid,
        'date_creation': _date_creation(),
        'state': 'creation',
    }




    def calculer_encours(self):
        for obj in self:
            #Suppression des lignes calculées
            for line in obj.line_ids:
                if line.composant_encours:
                    line.unlink()

            #Renumérotation des lignes
            self.sequence=1
            for line in obj.line_ids:
                line.sequence=self.sequence
                self.sequence=self.sequence+1


            #Création des lignes des composants
            self.sequence=10000
            for line in obj.line_ids:
                if line.encours:
                    product_tmpl_id=line.product_id.product_tmpl_id.id
                    self.eclate_nomenclature(obj,product_tmpl_id,line.qt_us,line.location_id.id)
                    self.sequence=self.sequence+1



    @api.multi
    def eclate_nomenclature(self,obj,product_tmpl_id,qt_us,location_id):
        nomenclatures=self.env['mrp.bom'].search([ ['product_tmpl_id','=',product_tmpl_id],['is_sous_traitance','!=',True]  ])
        if len(nomenclatures)>0:
            code=self.env['product.template'].browse(product_tmpl_id).is_code
            nomenclature=nomenclatures[0]
            for bom_line in nomenclature.bom_line_ids:
                qt=bom_line.product_qty*qt_us
                if bom_line.type=='phantom':
                    product_tmpl_id=bom_line.product_id.product_tmpl_id.id
                    self.eclate_nomenclature(obj,product_tmpl_id,qt,location_id)
                else:
                    vals={
                        'feuille_id'        : obj.id,
                        'sequence'          : self.sequence,
                        'product_id'        : bom_line.product_id.id,
                        'encours'           : False,
                        'composant_encours' : True,
                        'location_id'       : location_id,
                        'qt_us'             : qt,
                        'lieu'              : code
                    }
                    tmp=self.env['is.inventaire.line'].create(vals)
                self.sequence=self.sequence+1




    @api.multi
    def action_acceder_feuille(self):
        dummy, view_id = self.env['ir.model.data'].get_object_reference('is_plastigray', 'is_inventaire_feuille_form_view')
        for obj in self:
            return {
                'name': "Feuille d'inventaire",
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'is.inventaire.feuille',
                'type': 'ir.actions.act_window',
                'res_id': obj.id,
                'domain': '[]',
            }


    @api.multi
    def action_creer_feuille(self):
        for obj in self:
            return obj.inventaire_id.creer_feuille(obj.inventaire_id)


    #TODO : Cette fonction n'est plus active, mais je la garde pour l'exemple
    @api.multi
    def action_import_fichier(self):
        for obj in self:
            for row in obj.line_ids:
                row.unlink()
            csvfile=base64.decodestring(obj.fichier)
            csvfile=csvfile.split("\n")
            tab=[]
            sequence=0
            for row in csvfile:
                lig=row.split(",")
                ligne=[]
                for cel in lig:
                    if cel.startswith('"'):
                        cel = cel[1:]
                    if cel.endswith('"'):
                        cel = cel[0:-1]
                    ligne.append(cel)
                tab.append(ligne)
                # Recherche de l'article
                products=self.env['product.product'].search([['is_code', '=', ligne[0]]])
                product_id=0
                for product in products:
                    product_id=product.id
                # Recherche emplacement
                location_id=0
                statut=""
                if len(ligne)>4:
                    # Si statur = Q recherche d'un autre emplacement
                    emplacement = ligne[2]
                    statut      = ligne[3][0:1]
                    if statut=="Q":
                        emplacement="Q0"
                    locations=self.env['stock.location'].search([ ['usage','=','internal'],['name','like',emplacement]  ])
                    for location in locations:
                        location_id=location.id
                #Quantité
                qt=0
                if len(ligne)>6:
                    if statut=="Q":
                        val=ligne[6]
                    else:
                        val=ligne[4]
                    val=val.replace(" ", "")
                    try:
                        qt=float(val)
                    except ValueError:
                        continue
                if product_id and location_id:
                    sequence=sequence+1
                    vals={
                        'feuille_id': obj.id,
                        'sequence': sequence,
                        'product_id':product_id,
                        'location_id':location_id,
                        'qt_us': qt,
                        'lot': ligne[1],
                    }
                    self.env['is.inventaire.line'].create(vals)



    @api.multi
    def action_import_prodstar(self):
        uid=self._uid
        user=self.env['res.users'].browse(uid)
        soc=user.company_id.partner_id.is_code
        pwd=user.company_id.is_mysql_pwd
        for obj in self:
            for row in obj.line_ids:
                row.unlink()
            try:
                db = MySQLdb.connect(host="dynacase", user="root",    passwd=pwd, db="Plastigray")
            except MySQLdb.OperationalError, msg:
                raise Warning(u"La connexion à Prodstar a échouée ! \n"+str(msg[1]))
            cur = db.cursor()
            SQL="""
                SELECT PA0003, PF0023, PF0059, PF0102, sum(PF0104), sum(PF0113) 
                FROM FP2STO inner join FP2ART on PF0001=PA0001 AND PF0003=PA0003
                WHERE PF0001="""+str(soc)+""" AND (PA0184<70 OR PA0184=80) 
                GROUP BY PA0003, PF0023, PF0059, PF0102
            """
            cur.execute(SQL)
            sequence=0
            anomalies=[]
            for row in cur.fetchall():
                # Recherche de l'article
                products=self.env['product.product'].search([['is_code', '=', row[0]]])
                product=False
                for p in products:
                    product=p
                if product==False:
                    anomalies.append("Article "+str(row[0])+" inexistant !")
                else:
                    # Recherche du lot
                    lot=False
                    lots=self.env['stock.production.lot'].search([['name', '=', row[1]],['product_id', '=', product.id]])
                    for l in lots:
                        lot=l
                    # Création du lot s'il n'existe pas
                    if lot==False:
                        vals={
                            'name': str(row[1]),
                            'product_id': product.id,
                        }
                        lot=self.env['stock.production.lot'].create(vals)
                    # Recherche emplacement
                    location_id=0
                    statut=""
                    # Si statur = Q recherche d'un autre emplacement
                    emplacement = row[2]
                    statut      = row[3][0:1]
                    if statut=="Q":
                        emplacement=row[3]
                    if emplacement=="Q":
                        emplacement="Q0"
                    locations=self.env['stock.location'].search([ ['usage','=','internal'],['name','=',emplacement]  ])
                    location=False
                    for l in locations:
                        location=l
                    if location==False:
                        anomalies.append("Emplacement "+str(emplacement)+" inexistant !")
                    if statut=="Q":
                        qt=round(row[5],2)
                    else:
                        qt=round(row[4],2)
                    if product and location:
                        sequence=sequence+1
                        vals={
                            'feuille_id': obj.id,
                            'sequence': sequence,
                            'product_id':product.id,
                            'location_id':location.id,
                            'qt_us': qt,
                            'lot_id': lot.id,
                        }
                        self.env['is.inventaire.line'].create(vals)
                    obj.anomalies='\n'.join(anomalies)
            db.close()




class is_inventaire_line(models.Model):
    _name='is.inventaire.line'
    _order='feuille_id,sequence,id'

    inventaire_id     = fields.Many2one('is.inventaire', 'Inventaire', store=True, compute='_compute')
    feuille_id        = fields.Many2one('is.inventaire.feuille', 'Feuille Inventaire', required=True, ondelete='cascade')
    sequence          = fields.Integer('Séquence')
    product_id        = fields.Many2one('product.product', 'Article' , required=True)
    encours           = fields.Boolean('Encours')
    composant_encours = fields.Boolean('Composant', help='Composant encours')
    us_id             = fields.Many2one('product.uom','US', store=True, compute='_compute')
    uc                = fields.Char('UC', store=True, compute='_compute')
    uc_us             = fields.Integer('US par UC', store=True, compute='_compute')
    location_id       = fields.Many2one('stock.location', 'Emplacement', required=True)
    qt_us             = fields.Float("Qt US saisie")
    qt_uc             = fields.Float("Qt UC saisie")
    qt_us_calc        = fields.Float('Qt US', store=True, compute='_compute')
    lieu              = fields.Char('Lieu')
    lot_id            = fields.Many2one('stock.production.lot','Lot')
    state             = fields.Selection([('creation', u'Création'),('cloture', u'Cloturé'),('traite', u'Traité')], u"État", readonly=True, select=True)

    _defaults = {
        'sequence': 10,
        'state': 'creation',
    }

    @api.multi
    def get_emplacement(self, obj):
        emplacement_name = ''
        if obj.location_id.location_id:
            emplacement_name = str(obj.location_id.location_id.name) + '/' + str(obj.location_id.name)
        return emplacement_name

    @api.depends('product_id','qt_us','qt_uc')
    def _compute(self):
        for obj in self:
            obj.inventaire_id=obj.feuille_id.inventaire_id.id
            if obj.product_id:
                obj.us_id=obj.product_id.uom_id.id
                obj.uc_us=1
                if len(obj.product_id.packaging_ids):
                    packaging=obj.product_id.packaging_ids[0]
                    obj.uc=packaging.ul.name
                    obj.uc_us=packaging.qty
                if obj.qt_uc!=0:
                    obj.qt_us_calc=obj.qt_uc*obj.uc_us
                else:
                    obj.qt_us_calc=obj.qt_us

    @api.multi
    def onchange_product_id(self,product_id):
        v={}
        valeur=self.env['is.mem.var'].get(self._uid,'location_id')
        v['location_id'] = int(valeur)
        return {'value': v}


    @api.multi
    def onchange_location_id(self,product_id,location_id,qt_us,qt_uc,lieu):
        v={}
        v['product_id']  = product_id
        v['location_id'] = location_id
        v['qt_us']       = qt_us
        v['qt_uc']       = qt_uc
        v['lieu']        = lieu
        if location_id:
            self.env['is.mem.var'].set(self._uid, 'location_id', location_id)
        return {'value': v}




class is_inventaire_line_tmp(models.Model):
    _name='is.inventaire.line.tmp'
    _order='product_id'

    product_id      = fields.Many2one('product.product', 'Article' , required=True)
    us_id           = fields.Many2one('product.uom','US')
    location_id     = fields.Many2one('stock.location', 'Emplacement', required=True)
    qt_us           = fields.Float("Qt US")
    lot_id          = fields.Many2one('stock.production.lot','Lot')
    date_lot        = fields.Datetime('Date création lot')



class is_inventaire_inventory(models.Model):
    _name='is.inventaire.inventory'
    _order='inventaire_id'

    inventaire_id   = fields.Many2one('is.inventaire', 'Inventaire', required=True, ondelete='cascade', readonly=True)
    inventory_id    = fields.Many2one('stock.inventory', 'Inventaire')


    @api.multi
    def action_acceder_inventaire(self):
        dummy, view_id = self.env['ir.model.data'].get_object_reference('stock', 'view_inventory_form')
        for obj in self:
            return {
                'name': "Inventaire",
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'stock.inventory',
                'type': 'ir.actions.act_window',
                'res_id': obj.inventory_id.id,
                'domain': '[]',
            }


class is_inventaire_ecart(models.Model):
    _name='is.inventaire.ecart'
    _order='inventaire_id,location_id,code'

    inventaire_id     = fields.Many2one('is.inventaire', 'Inventaire', select=True)
    location_id     = fields.Many2one('stock.location', 'Emplacement', required=True, select=True)
    product_id      = fields.Many2one('product.product', 'Article' , required=True, select=True)
    code            = fields.Char("Article")
    designation     = fields.Char("Désignation")
    us_id           = fields.Many2one('product.uom','US')
    qt_odoo         = fields.Float("Qt Odoo")
    qt_inventaire   = fields.Float("Qt Inventaire")
    ecart           = fields.Float("Ecart", help="Qt Inventaire - Qt Odoo")



