# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning
from datetime import datetime
from dateutil.relativedelta import relativedelta


def num(s):
    """ Permet de convertir une chaine en entier en évitant les exeptions"""
    try:
        return int(s)
    except ValueError:
        return 0


class is_pic_3ans_saisie(models.Model):
    _name='is.pic.3ans.saisie'
    _order='annee desc, product_id'

    ordre=0

    annee      = fields.Char('Année PIC',                         required=True)
    product_id = fields.Many2one('product.product', 'Article',    required=True)
    recharger  = fields.Boolean('Recharger les données')
    raz        = fields.Boolean('Mise à 0 des données')

    liv_01     = fields.Integer('Livré 01', compute='_compute', readonly=True, store=False)
    liv_02     = fields.Integer('Livré 02', compute='_compute', readonly=True, store=False)
    liv_03     = fields.Integer('Livré 03', compute='_compute', readonly=True, store=False)
    liv_04     = fields.Integer('Livré 04', compute='_compute', readonly=True, store=False)
    liv_05     = fields.Integer('Livré 05', compute='_compute', readonly=True, store=False)
    liv_06     = fields.Integer('Livré 06', compute='_compute', readonly=True, store=False)
    liv_07     = fields.Integer('Livré 07', compute='_compute', readonly=True, store=False)
    liv_08     = fields.Integer('Livré 08', compute='_compute', readonly=True, store=False)
    liv_09     = fields.Integer('Livré 09', compute='_compute', readonly=True, store=False)
    liv_10     = fields.Integer('Livré 10', compute='_compute', readonly=True, store=False)
    liv_11     = fields.Integer('Livré 11', compute='_compute', readonly=True, store=False)
    liv_12     = fields.Integer('Livré 12', compute='_compute', readonly=True, store=False)
    liv_total  = fields.Integer('Livré Total', compute='_compute', readonly=True, store=False)

    pic_01     = fields.Integer('PIC 01')
    pic_02     = fields.Integer('PIC 02')
    pic_03     = fields.Integer('PIC 03')
    pic_04     = fields.Integer('PIC 04')
    pic_05     = fields.Integer('PIC 05')
    pic_06     = fields.Integer('PIC 06')
    pic_07     = fields.Integer('PIC 07')
    pic_08     = fields.Integer('PIC 08')
    pic_09     = fields.Integer('PIC 09')
    pic_10     = fields.Integer('PIC 10')
    pic_11     = fields.Integer('PIC 11')
    pic_12     = fields.Integer('PIC 12')
    pic_total  = fields.Integer('PIC Total', compute='_compute_pic_total', readonly=True, store=False)


    _defaults = {
        'annee': lambda self, cr, uid, ctx=None: self.pool.get('is.mem.var').get(cr, uid, uid, uid, 'annee_pic'),
    }


    @api.multi
    def name_get(self):
        res=[]
        for obj in self:
            name=obj.annee+u' - '+obj.product_id.is_code
            res.append((obj.id, name))
        return res


    @api.depends('pic_01','pic_02','pic_03','pic_04','pic_05','pic_06','pic_07','pic_08','pic_09','pic_10','pic_11','pic_12',)
    def _compute_pic_total(self):
        for obj in self:
            if obj.annee and obj.product_id:
                pic_total=0
                for i in range(1,13):
                    champ="pic_"+("00"+str(i))[-2:]
                    qt=getattr(obj, champ)
                    if qt:
                        pic_total=pic_total+qt
                obj.pic_total=pic_total



    @api.depends('annee','product_id')
    def _compute(self):
        cr = self._cr
        for obj in self:
            if obj.annee:
                annee=num(obj.annee)
                if annee<2017 or annee>=2040:
                    raise Warning("Année non valide")
            if obj.annee and obj.product_id:
                code_pg=obj.product_id.is_code
                code_pg=code_pg[:6]
                date_debut = datetime.strptime(str(annee)+'-01-01', '%Y-%m-%d')
                liv_total=0
                pic_total=0
                for i in range(1,13):
                    date_fin = date_debut + relativedelta(months=1)
                    SQL="""
                        select 
                            sum(sm.product_uom_qty)
                        from stock_picking sp inner join stock_move       sm on sp.id=sm.picking_id
                                              inner join product_product  pp on sm.product_id=pp.id 
                                              inner join product_template pt on pp.product_tmpl_id=pt.id
                        where 
                            pt.is_code like '"""+code_pg+"""%' and
                            sp.state='done' and
                            sp.picking_type_id=2 and 
                            sp.is_date_expedition>='"""+date_debut.strftime('%Y-%m-%d')+"""' and
                            sp.is_date_expedition<'"""+date_fin.strftime('%Y-%m-%d')+"""'
                    """
                    cr.execute(SQL)
                    result = cr.fetchall()
                    qt=0
                    for row in result:
                        qt=row[0]
                    if qt:
                        liv_total=liv_total+qt
                    champ="liv_"+("00"+str(i))[-2:]
                    setattr(obj, champ, qt)
                    date_debut = date_debut + relativedelta(months=1)
                obj.liv_total=liv_total



    @api.multi
    def on_change_recharger(self, annee, product_id):
        cr = self._cr
        if annee and product_id:
            annee=num(annee)
            if annee<2017 or annee>=2040:
                raise Warning("Année non valide")
            product=self.env['product.product'].browse(product_id)
            code_pg=product.is_code
            code_pg=code_pg[:6]
            date_debut = datetime.strptime(str(annee)+'-01-01', '%Y-%m-%d')
            value={}
            for i in range(1,13):
                SQL="""
                    select quantite
                    from is_pic_3ans
                    where 
                        product_id="""+str(product_id)+""" and
                        mois='"""+date_debut.strftime('%Y-%m')+"""' 
                """
                cr.execute(SQL)
                result = cr.fetchall()
                qt=0
                for row in result:
                    qt=row[0]
                champ="pic_"+("00"+str(i))[-2:]
                value[champ]=qt
                date_debut = date_debut + relativedelta(months=1)
            return {'value': value}


    @api.multi
    def on_change_raz(self):
        value={}
        for i in range(1,13):
            champ="pic_"+("00"+str(i))[-2:]
            value[champ]=0
        return {'value': value}



    @api.model
    def create(self, vals):
        obj = super(is_pic_3ans_saisie, self).create(vals)
        self.env['is.mem.var'].set(self._uid, 'annee_pic', obj.annee)
        self.create_pic_3ans(obj)
        return obj


    @api.multi
    def write(self,vals):
        res=super(is_pic_3ans_saisie, self).write(vals)
        for obj in self:
            annee=num(obj.annee)
            if annee<2017 or annee>=2040:
                raise Warning("Année non valide")
            self.env['is.mem.var'].set(self._uid, 'annee_pic', annee)
            self.create_pic_3ans(obj)
        return res


    @api.multi
    def create_pic_3ans(self,obj):
        annee=num(obj.annee)
        pic_obj = self.env['is.pic.3ans']
        pic_obj.search([
            ('annee'      ,'=',obj.annee),
            ('product_id' ,'=',obj.product_id.id),
            ('type_donnee','=','pic'),
        ]).unlink()
        for i in range(1,13):
            champ = "pic_"+("00"+str(i))[-2:]
            mois  = str(annee)+'-'+("00"+str(i))[-2:]
            quantite = getattr(obj, champ)
            if quantite>0:
                vals={
                    'type_donnee': 'pic',
                    'annee'      : obj.annee,
                    'mois'       : mois,
                    'product_id' : obj.product_id.id,
                    'quantite'   : quantite,
                }
                pic=pic_obj.create(vals)


    def run_cbb_scheduler_action(self, cr, uid, use_new_cursor=False, company_id = False, context=None):
        self.run_cbb(cr, uid, context)


    @api.multi
    def run_cbb(self):
        cr = self._cr
        print "#### Début du CBB ####"

        #** Recherche des PIC à traiter ************************************
        pic_obj = self.env['is.pic.3ans']

        print 'search pics'
        pics=pic_obj.search([
            ('type_donnee','=','pic'),
        ])
        #*******************************************************************

        #** Suppression des données du calcul précédent ********************
        print 'unlink pics'
#        pic_obj.search([
#            ('type_donnee','=','pdp'),
#        ]).unlink()
        SQL="""
            delete
            from is_pic_3ans
            where type_donnee='pdp'
        """
        cr.execute(SQL)
        print 'fin unlink pics'
        #*******************************************************************

        #** CBB sur les PIC ************************************************
        print "debut cbb"
        global ordre
        nb=len(pics)
        ct=0
        for pic in pics:
            ct=ct+1
            print ct,'/',nb, pic, pic.product_id, pic.quantite
            ordre=0
            self.cbb_multi_niveaux(pic, pic.product_id, pic.quantite)
        #*******************************************************************
        print "#### Fin du CBB ####"

    @api.multi
    def cbb_article(self):

        #self.run_cbb()
        #return

        if len(self)>1:
            raise Warning("Calcul multiple non autorisé")
        for obj in self:
            pic_obj = self.env['is.pic.3ans']

            #** Recherche des PIC à traiter ************************************
            pics=pic_obj.search([
                ('annee'      ,'=',obj.annee),
                ('product_id' ,'=',obj.product_id.id),
                ('type_donnee','=','pic'),
            ])
            #*******************************************************************

            #** Suppression des données du calcul précédent ********************
            for pic in pics:
                print 'unlink',pic
                pic_obj.search([
                    ('annee'      ,'=',obj.annee),
                    ('origine_id' ,'=',pic.id),
                    ('type_donnee','=','pdp'),
                ]).unlink()
            #*******************************************************************

            #** CBB sur les PIC ************************************************
            global ordre
            print len(pics)
            for pic in pics:
                print pic, pic.product_id, pic.quantite
                ordre=0
                self.cbb_multi_niveaux(pic, pic.product_id, pic.quantite)
            #*******************************************************************


    @api.multi
    def cbb_multi_niveaux(self, pic, product, quantite=1, niveau=1):
        global ordre
        bom_obj = self.env['mrp.bom']
        bom_id = bom_obj._bom_find(product.product_tmpl_id.id, properties=None)
        bom = bom_obj.browse(bom_id)
        res= bom_obj._bom_explode(bom, product, 1)
        pic_obj = self.env['is.pic.3ans']
        for line in res[0]:
            ordre=ordre+1
            line_product  = self.env['product.product'].browse(line['product_id'])
            line_quantite = quantite*line['product_qty']
            vals={
                'type_donnee': 'pdp',
                'annee'      : pic.annee,
                'mois'       : pic.mois,
                'product_id' : line_product.id,
                'quantite'   : line_quantite,
                'origine_id' : pic.id,
                'niveau'     : niveau,
                'ordre'      : ordre,
            }
            pdp=pic_obj.create(vals)
            self.cbb_multi_niveaux(pic, line_product, line_quantite, niveau+1)


class is_pic_3ans(models.Model):
    _name='is.pic.3ans'
    #_order='mois,origine_id,ordre,product_id'
    _order='product_id'


    @api.depends('product_id')
    def _compute(self):
        for obj in self:
            if obj.product_id:
                obj.mold_dossierf  = obj.product_id.is_mold_dossierf
                obj.client_id      = obj.product_id.is_client_id
                obj.fournisseur_id = obj.product_id.is_fournisseur_id
                description=\
                    obj.product_id.is_code+\
                    u' ('+(obj.product_id.is_mold_dossierf or u'')+\
                    u'/'+(obj.product_id.is_client_id.is_code or u'')+\
                    u'/'+(obj.product_id.is_fournisseur_id.is_code or u'')+u')'
                obj.description=description


    type_donnee = fields.Selection([('pic', u'PIC'),('pdp', u'PDP')], u"Type de données", select=True, required=True)
    annee       = fields.Char('Année', required=True                                    , select=True)
    mois        = fields.Char('Mois' , required=True                                    , select=True)
    product_id  = fields.Many2one('product.product', 'Article', required=True           , select=True)
    quantite    = fields.Integer('Quantité')
    origine_id  = fields.Many2one('is.pic.3ans', 'Origine du besoin'                    , select=True)
    niveau      = fields.Integer('Niveau dans la nomenclature'                          , select=True)
    ordre       = fields.Integer('Ordre dans la nomenclature'                           , select=True)

    mold_dossierf  = fields.Char('Moule ou Dossier F'                       , store=True, compute='_compute')
    client_id      = fields.Many2one('res.partner', 'Client par défaut'     , store=True, compute='_compute')
    fournisseur_id = fields.Many2one('res.partner', 'Fournisseur par défaut', store=True, compute='_compute')
    description    = fields.Char('Article (Moule/Client/Fournisseur)'       , store=True, compute='_compute')

    # La fonction name_get est une fonction standard d'Odoo permettant de définir le nom des fiches (dans les relations x2x)
    # La fonction name_search permet de définir les résultats des recherches dans les relations x2x. En général, elle appelle la fonction name_get
    @api.multi
    def name_get(self):
        res=[]
        for obj in self:
            name=obj.mois+u' - '+obj.product_id.is_code
            res.append((obj.id, name))
        return res


