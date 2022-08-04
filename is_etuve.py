# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _
import datetime
from openerp.exceptions import Warning
import psycopg2
from psycopg2.extras import RealDictCursor
import sys


dessication_list=[('N', u'N'),('DS', u'DS')]


class is_etuve(models.Model):
    _name='is.etuve'
    _order='name'
    _sql_constraints = [('name_uniq','UNIQUE(name)', u'Cette étuve existe déjà')]

    name            = fields.Char("N°étuve",size=10, select=True                    , required=True)
    dessication     = fields.Selection(dessication_list, "Dessication" , required=True)
    type_etuve      = fields.Selection([('0', u'0'),('MAT', u'MAT')], "Type étuve"  , required=True)
    capacite        = fields.Integer("Capacité"                                     , required=True)

    matiere_id        = fields.Many2one('product.product', 'Matière', readonly=True)
    num_ordre_matiere = fields.Char("N°ordre matière"               , readonly=True)
    of                = fields.Char("OF"                            , readonly=True)
    moule             = fields.Char("Moule"                         , readonly=True)
    taux_utilisation  = fields.Float("Taux d'utilisation étuve (%)" , readonly=True)
    progressbar       = fields.Float("Taux d'utilisation étuve"     , readonly=False)
    test_taux         = fields.Boolean("Test Taux"                  , readonly=True)
    message           = fields.Char("Message"                       , readonly=True)
    rsp_etuve_id      = fields.Many2one('is.etuve.rsp', 'Rsp étuve' , readonly=True)
    commentaire       = fields.Char("Commenaire optionnel"          , readonly=True)



    _defaults = {
        'capacite'   :  0,
        'dessication':  'N',
        'type_etuve' :  '0',
    }

    @api.multi
    def action_saisie_etuve(self):
        for obj in self:
            saisie_obj = self.env['is.etuve.saisie']
            saisies  = saisie_obj.search([('etuve_id','=',obj.id)],limit=1)
            context={}
            for saisie in saisies:
                context={
                    'default_etuve_id'    : saisie.etuve_id.id,
                    'default_matiere_id'  : saisie.matiere_id.id,
                    'default_rsp_etuve_id': saisie.rsp_etuve_id.id,
                }
                ids=[]
                for of in saisie.of_ids:
                    vals={
                        'of_id': of.of_id.id
                    }
                    ids.append(vals)
                if len(ids)>0:
                    context.update({'default_of_ids': ids})
            return {
                'name'     : 'Saisie étuve',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'is.etuve.saisie',
                'type'     : 'ir.actions.act_window',
                'context'  : context,
             }






class is_etuve_rsp(models.Model):
    _name='is.etuve.rsp'
    _order='name'
    _sql_constraints = [('name_uniq','UNIQUE(name)', u'Ce responsable existe déjà')]

    name         = fields.Char("Responsable étuve", required=True, select=True)
    mot_de_passe = fields.Char("Mot de passe"     , required=True)


class is_etuve_commentaire(models.Model):
    _name='is.etuve.commentaire'
    _order='name'
    _sql_constraints = [('name_uniq','UNIQUE(name)', u'Ce commentaire existe déjà')]

    name         = fields.Char("Commentaire étuve", required=True, select=True)


class is_etuve_saisie(models.Model):
    _name='is.etuve.saisie'
    _order='name desc'


    @api.multi
    def _string2float(self,val):
        val=str(val)
        print 'val=',val,type(val),str(val)
        res=0
        if val!='None':
            res=float(val.replace(',','.'))
        return res


    @api.depends('matiere_id','of_ids')
    def _compute(self):
        cr, uid, context = self.env.args
        company = self.env.user.company_id
        for obj in self:
            base0="odoo0"
            if company.is_postgres_host=='localhost':
                base0="pg-odoo0"
            try:
                cnx0 = psycopg2.connect("dbname='"+base0+"' user='"+company.is_postgres_user+"' host='"+company.is_postgres_host+"' password='"+company.is_postgres_pwd+"'")
                cr0 = cnx0.cursor(cursor_factory=RealDictCursor)
            except:
                raise Warning("Impossible de se connecter à %s"%(base0))

            #** Recherche fiche technique Matière dans Dynacase ****************
            # user=self.env['res.users'].browse(uid)
            # password=user.company_id.is_dynacase_pwd
            # cnx=False
            # try:
            #     cnx = psycopg2.connect("host='dynacase' port=5432 dbname='freedom' user='freedomowner' password='"+password+"'")
            # except:
            #     raise Warning("Impossible de se connecter à Dynacase")
            # cursor = cnx.cursor()
            # SQL="""select dosart_codepg, dosart_designation, dosmat_tmp_etuvage, dosmat_tps_etuvage, dosmat_densite, dosmat_ds
            #        from doc48613
            #        where doctype='D' and locked='0' and dosart_codepg='"""+str(CodeMatiere)+"""' """
            # cursor.execute(SQL)
            # result = cursor.fetchall()

            # tmp_etuvage=tps_etuvage=densite=dessication_matiere=False
            # for row in result:
            #     tmp_etuvage         = self._string2float(row[2])
            #     tps_etuvage         = self._string2float(row[3])
            #     densite             = self._string2float(row[4])
            #     dessication_matiere = row[5]


            #** Recherche fiche technique Matière dans odoo0 ******************
            tmp_etuvage=tps_etuvage=densite=dessication_matiere=False
            CodeMatiere=obj.matiere_id.is_code
            if CodeMatiere:
                SQL="""
                    SELECT densite, temps_etuvage, temperature_etuvage, dessiccateur
                    FROM is_dossier_article
                    WHERE code_pg=%s
                """
                cr0.execute(SQL, [CodeMatiere])
                result = cr0.fetchall()
                for row in result:
                    tmp_etuvage         = row["temperature_etuvage"]
                    tps_etuvage         = row["temps_etuvage"]
                    densite             = row["densite"]
                    dessication_matiere = row["dessiccateur"]
            #******************************************************************

            obj.tmp_etuvage   = tmp_etuvage
            obj.tps_etuvage   = tps_etuvage
            obj.densite       = densite
            obj.dessication_matiere = dessication_matiere
            obj.capacite_maxi = str(len(obj.of_ids))
            EtuveCapacite=obj.etuve_id.capacite
            CoefSecurite=0.95
            CoefFoisonnement=0.6
            capacite_maxi=False
            if densite:
                capacite_maxi=round(CoefSecurite*CoefFoisonnement*EtuveCapacite*densite,0)
            obj.capacite_maxi = capacite_maxi
            conso_horaire=0.0
            for row in obj.of_ids:
                conso_horaire=conso_horaire+round(row.debit)
            obj.conso_horaire = conso_horaire
            taux_utilisation=False
            if capacite_maxi: 
                taux_utilisation=round(100*tps_etuvage*conso_horaire/capacite_maxi,2)
            obj.taux_utilisation=taux_utilisation
            test_taux=message=False
            if taux_utilisation>105:
                test_taux=True
                message=u"Attention : Le taux d'utilisation de l'étuve est de "+str(int(taux_utilisation))+u'%'
            obj.test_taux=test_taux
            obj.message=message


    name                 = fields.Char("Saisie", select=True , readonly=True)
    etuve_id             = fields.Many2one('is.etuve', 'Etuve', required=True)
    capacite             = fields.Integer('Capacité' , related='etuve_id.capacite'   , readonly=True)
    dessication          = fields.Selection(dessication_list, "Dessication", related='etuve_id.dessication', readonly=True)
    num_ordre_matiere    = fields.Char("N°ordre matière", required=True)
    rsp_etuve_id         = fields.Many2one('is.etuve.rsp', 'Rsp étuve', required=True)
    mot_de_passe         = fields.Char("Mot de passe"   , required=True)
    commentaire_id       = fields.Many2one('is.etuve.commentaire', 'Commenaire', required=True)
    commentaire_optionel = fields.Char("Commenaire optionnel")

    matiere_id           = fields.Many2one('product.product', 'Matière', required=True, domain=[('family_id.name','=','MATIERE')] )
    tmp_etuvage          = fields.Float("Température d'étuvage"    , readonly=True, compute='_compute', store=True)
    tps_etuvage          = fields.Float("Temps d'étuvage matière"  , readonly=True, compute='_compute', store=True)
    densite              = fields.Float("Densité"                  , readonly=True, compute='_compute', store=True)
    dessication_matiere  = fields.Char("Dessication"               , readonly=True, compute='_compute', store=True)
    capacite_maxi        = fields.Float("Capacité maxi étuve (Kg)"  , readonly=True, compute='_compute', store=True)
    conso_horaire        = fields.Float("Consommation horaire (Kg/H)", readonly=True, compute='_compute', store=True)
    taux_utilisation     = fields.Float("Taux utilisation étuve (%)", readonly=True, compute='_compute', store=True)
    test_taux            = fields.Boolean("Test Taux"               , readonly=True, compute='_compute', store=True)
    message              = fields.Char("Message"                    , readonly=True, compute='_compute', store=True)
    of_ids               = fields.One2many('is.etuve.of', 'etuve_id', u"OFs")
    

    @api.model
    def create(self, vals):
        rsp_obj = self.env['is.etuve.rsp']
        rsp = rsp_obj.browse(vals['rsp_etuve_id'])
        if rsp.mot_de_passe!=vals['mot_de_passe']:
            raise Warning(u"Mot de passe incorecte !")
        data_obj = self.env['ir.model.data']
        sequence_ids = data_obj.search([('name','=','is_etuve_saisie_seq')])
        if sequence_ids:
            sequence_id = data_obj.browse(sequence_ids[0].id).res_id
            vals['name'] = self.env['ir.sequence'].get_id(sequence_id, 'id')
        obj = super(is_etuve_saisie, self).create(vals)

        #** Vérfication des matières *******************************************
        for row in obj.of_ids:
            if not row.matiere:
                raise Warning(u"Les matières des OF ne correspondent pas à la matière de l'étuve !")
        #***********************************************************************


        #** Mise à jour des données de l'étuve *********************************
        etuve=self.env['is.etuve'].browse(obj.etuve_id.id).sudo()
        etuve.matiere_id        = obj.matiere_id.id
        etuve.num_ordre_matiere = obj.num_ordre_matiere
        etuve.taux_utilisation  = obj.taux_utilisation
        etuve.progressbar       = obj.taux_utilisation
        etuve.test_taux         = obj.test_taux
        etuve.message           = obj.message
        etuve.rsp_etuve_id      = obj.rsp_etuve_id.id
        of=[]
        moule=[]
        for row in obj.of_ids:
            of.append(row.of_id.name)
            moule.append(row.moule)
        etuve.of=', '.join(of)
        etuve.moule=', '.join(moule)
        commentaire = obj.commentaire_id.name
        if obj.commentaire_optionel:
            commentaire=commentaire+u', '+obj.commentaire_optionel
        etuve.commentaire = commentaire
        #***********************************************************************

        return obj



    @api.multi
    def copy(self, default=None):
        raise Warning(u"Duplication interdite !")


class is_etuve_of(models.Model):
    _name='is.etuve.of'
    _order='etuve_id,id'

    @api.depends('of_id')
    def _compute(self):
        cr, uid, context = self.env.args
        for obj in self:
            if not obj.of_id or not obj.etuve_id.matiere_id:
                return
            of=obj.of_id
            obj.code_pg   = of.product_id.is_code
            obj.qt_prevue = of.product_qty
            obj.moule     = of.product_id.is_mold_id.name
 
            #** Recherche de la presse de l'OF *************************************
            presse=False
            for line in of.workcenter_lines:
                if line.workcenter_id.resource_type=='material' and line.workcenter_id.code<'9000':
                    presse=line.workcenter_id.code
                    obj.presse=presse
            #***********************************************************************

            #** Recherche du temps de cycle de la gamme ****************************
            tps_cycle_matiere=False
            nb_empreintes = of.routing_id.is_nb_empreintes
            theia         = of.routing_id.is_coef_theia


            for line in of.routing_id.workcenter_lines:
                if line.workcenter_id.resource_type=='material':
                    nb_secondes=line.is_nb_secondes
                    tps_cycle_matiere=nb_secondes*nb_empreintes*theia
                    obj.tps_cycle_matiere=tps_cycle_matiere
            if nb_empreintes==0:
                nb_empreintes=1
            #***********************************************************************

            #** Recherche de la matière utilisée dans l'OF *************************
            matiere = obj.etuve_id.matiere_id.is_code
            suffix  = matiere[-4:]
            broye   = '59'+suffix
            SQL="""
                select pt.is_code, sum(mppl.product_qty) 
                from mrp_production_product_line mppl inner join product_product pp on mppl.product_id=pp.id 
                                                      inner join product_template pt on pp.product_tmpl_id=pt.id 
                where mppl.production_id="""+str(obj.of_id.id)+""" and (pt.is_code='"""+str(matiere)+"""' or pt.is_code='"""+str(broye)+"""')
                group by mppl.product_id,mppl.name,pt.is_code 
                order by max(mppl.id) """
            matiere=poids_moulee=False
            cr.execute(SQL)
            result = cr.fetchall()
            besoin_total_of=qty=0.0
            for row in result:
                matiere = row[0]
                qty     = row[1]
                #Si le code est du broyé, il faut multiplier la quantité par deux pour doubler le temps d'étuvage
                if matiere[0:2]=='59':
                    qty=qty*2
                besoin_total_of=besoin_total_of+qty
            obj.matiere         = matiere
            obj.besoin_total_of = besoin_total_of
            #***********************************************************************

            #** Calcul poids de la moulée et du débit ******************************
            poids_moulee=debit=0
            if of.product_qty!=0.0:
                poids_moulee=nb_empreintes*1000*besoin_total_of/of.product_qty
            obj.poids_moulee=poids_moulee
            if tps_cycle_matiere:
                debit=poids_moulee*3.6/tps_cycle_matiere
            obj.debit=debit
            #***********************************************************************


    etuve_id          = fields.Many2one('is.etuve.saisie', 'Étuve', required=True, ondelete='cascade')
    of_id             = fields.Many2one('mrp.production', 'Ordre de fabrication', required=True, domain=[('state','in',['ready','in_production'])])
    matiere           = fields.Char("Matière"              , readonly=True, compute='_compute', store=True, required=False)
    code_pg           = fields.Char("Code PG"              , readonly=True, compute='_compute', store=True)
    qt_prevue         = fields.Integer("Qt prévue"         , readonly=True, compute='_compute', store=True)
    moule             = fields.Char("Moule"                , readonly=True, compute='_compute', store=True)
    presse            = fields.Char("Presse"               , readonly=True, compute='_compute', store=True)
    tps_arret_matiere = fields.Float("Tps arrêt matière"   , readonly=True, compute='_compute', store=True)
    tps_cycle_matiere = fields.Float("Tps cycle matière"   , readonly=True, compute='_compute', store=True)
    besoin_total_of   = fields.Float("Besoin total of (Kg)", readonly=True, compute='_compute', store=True)
    poids_moulee      = fields.Float("Poids moulée (g)"    , readonly=True, compute='_compute', store=True)
    debit             = fields.Float("Débit (Kg/H)"        , readonly=True, compute='_compute', store=True)




