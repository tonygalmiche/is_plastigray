# -*- coding: utf-8 -*-
import datetime
from turtle import title
from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning
import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
_logger = logging.getLogger(__name__)


class is_consigne_journaliere(models.Model):
    _name = "is.consigne.journaliere"
    _description = "Consignes journalieres"
    _order='create_date desc'

    name                = fields.Char('Titre')
    chef_atelier        = fields.Char("Chef d'atelier")
    remarque_generale   = fields.Text('Remarque générale')
    date_derniere_modif = fields.Datetime("Date dernière modification", readonly=True)
    total_mod_inj       = fields.Float('Total MOD Injection' , readonly=True, compute='_compute', store=True)
    total_mod_ass       = fields.Float('Total MOD Assemblage', readonly=True, compute='_compute', store=True)
    injection_ids       = fields.One2many('is.consigne.journaliere.inj'  , 'consigne_id', u"Injection" , copy=True)
    assemblage_ids      = fields.One2many('is.consigne.journaliere.ass'  , 'consigne_id', u"Assemblage", copy=True)


    @api.depends('injection_ids','assemblage_ids')
    def _compute(self):
        for obj in self:
            total_mod_inj=0
            for line in obj.injection_ids:
                total_mod_inj=total_mod_inj+line.mod1
            total_mod_ass=0
            for line in obj.assemblage_ids:
                total_mod_ass=total_mod_ass+line.mod
            obj.total_mod_inj=total_mod_inj
            obj.total_mod_ass=total_mod_ass


    @api.multi
    def write(self,vals):
        vals['date_derniere_modif']=datetime.datetime.now()
        res = super(is_consigne_journaliere, self).write(vals)
        return res




class is_consigne_journaliere_inj(models.Model):
    _name='is.consigne.journaliere.inj'
    _order='consigne_id,sequence'

    consigne_id    = fields.Many2one('is.consigne.journaliere', 'Consigne journaliere', required=True, ondelete='cascade', readonly=True)
    sequence       = fields.Integer('Ordre')
    presse_id      = fields.Many2one('mrp.workcenter', 'Presse', 
                    domain=[('resource_type','=','material'),('code','<','9000'),('name','not ilike','GENERIQUE')])
    of1_id         = fields.Many2one('is.mrp.production.workcenter.line', 'OF en cours')
    mod1           = fields.Float('MOD')
    operateur      = fields.Char('Opérateur')
    moule1         = fields.Char('Moule')
    info_planning1 = fields.Text('Info Planning' , compute="_compute_info_planning1", store=True)
    matiere1       = fields.Char('Matière')
    tps_arret      = fields.Char('Tps arrêt matière')
    heure          = fields.Char('Heure')
    of2_id         = fields.Many2one('is.mrp.production.workcenter.line', 'OF suivant')
    mod2           = fields.Float('MOD')
    moule2         = fields.Char('Moule')
    matiere2       = fields.Char('Matière')
    remarque       = fields.Text('Remarques / Consignes')


    @api.depends('sequence','presse_id','of1_id','remarque')
    def _compute_info_planning1(self):
        cr , uid, context = self.env.args
        company = self.env.user.company_id
        base0="odoo0"
        cr0 = False
        if company.is_postgres_host=='localhost':
            base0="pg-odoo0"
        try:
            cnx0 = psycopg2.connect("dbname='"+base0+"' user='"+company.is_postgres_user+"' host='"+company.is_postgres_host+"' password='"+company.is_postgres_pwd+"'")
            cr0 = cnx0.cursor(cursor_factory=RealDictCursor)
        except:
            cr0 = False
            #raise Warning("Impossible de se connecter à odoo0")

        #** Connexion à Dynacase **********************************************
        password=company.is_dynacase_pwd
        cr_dynacase=False
        if password:
            try:
                cnx_dynacase = psycopg2.connect("host='dynacase' port=5432 dbname='freedom' user='freedomowner' password='"+password+"'")
                #cr_dynacase = cnx_dynacase.cursor(cursor_factory=RealDictCursor)
                cr_dynacase = cnx_dynacase.cursor()
            except:
                cr_dynacase=False
 

        for obj in self:
            info=[]
            if cr0 and cr_dynacase:

                if obj.of1_id:
                    #** Moule à verion ********************************************
                    moule = obj.of1_id.product_id.is_mold_id
                    if moule.moule_a_version=="oui":
                        if moule.lieu_changement=="en_mecanique":
                            info.append("-Moule à version en mécanique")
                        else:
                            info.append("-Moule à version")

                    #** Reprise humidité ******************************************
                    if obj.of1_id.name.routing_id.is_reprise_humidite==True:
                        info.append("-Reprise humidité")

                    #** Recherche si OT sur le moule ******************************
                    moule = obj.of1_id.product_id.is_mold_id.name
                    if moule:
                        SQL="""
                            select 
                                io.name,
                                io.gravite,
                                io.state,
                                io.id
                            from is_ot io inner join is_mold im on io.moule_id=im.id
                            where 
                                im.name=%s and
                                io.state in ('travaux_a_realiser','analyse_ot','travaux_a_valider') and
                                io.gravite in ('1','2')
                        """
                        cr0.execute(SQL, [moule])
                        result = cr0.fetchall()
                        niv=mem_niv=99
                        state=title=False
                        for row in result:
                            if row['state']=='travaux_a_realiser':
                                state="à réaliser"
                            if row['state']=='analyse_ot':
                                state="à analyser"
                            if row['state']=='travaux_a_valider':
                                state="à valider"
                            if row['state']=='analyse_ot':
                                niv=3
                            else:
                                if row['gravite']=='1':
                                        niv=1
                                if row['gravite']=='2':
                                        niv=2
                            if row['state']=='travaux_a_valider':
                                niv=4
                            if niv<mem_niv:
                                mem_niv=niv
                                title="- OT moule %s %s (Gravité=%s)"%(row["name"],state,row['gravite'])
                        if title:
                            info.append(title)

                    #** Netoyer moule *********************************************
                    moule = obj.of1_id.product_id.is_mold_id
                    if moule.nettoyer:
                        info.append("- Nettoyage Moule")
                    if moule.nettoyer_vis:
                        info.append("- Nettoyage Vis")


                    #** Controle 100% *********************************************
                    moule_id   = obj.of1_id.product_id.is_mold_id.id
                    product_id = obj.of1_id.product_id.id
                    if product_id and moule_id:
                        SQL = """
                            SELECT g.name
                            FROM is_ctrl100_gamme_mur_qualite g left outer join is_mold m on g.mold_id=m.id              and g.gamme_sur='moule'
                                                                left outer join product_product pp on g.product_id=pp.id and g.gamme_sur='article'
                                                                left outer join product_template pt on pp.product_tmpl_id=pt.id
                            WHERE g.active='t' and (m.id=%s or pp.id=%s) 
                            ORDER BY g.name
                        """
                        cr.execute(SQL, [moule_id,product_id])
                        result = cr.fetchall()
                        for row in result:
                            info.append("- CTRL 100% "+(row[0] or ''))

                #** Recherche si la presse est prioritaire ********************
                    if obj.of1_id.name.is_prioritaire:
                        info.append("- OF prioritaire")


                if obj.presse_id:
                    #** Recherche si OT sur la presse *****************************
                    SQL="""
                        select 
                            io.name,
                            ie.numero_equipement,
                            iet.code,
                            io.gravite,
                            io.state,
                            io.id
                        from is_ot io inner join is_equipement      ie  on io.equipement_id=ie.id
                                    inner join is_equipement_type iet on ie.type_id=iet.id
                        where 
                            iet.code='PE' and 
                            ie.numero_equipement=%s and
                            io.state in ('travaux_a_realiser','analyse_ot','travaux_a_valider') and
                            io.gravite in ('1','2')
                    """
                    cr0.execute(SQL, [obj.presse_id.code])
                    result = cr0.fetchall()
                    niv=mem_niv=99
                    state=title=False
                    for row in result:
                        if row['state']=='travaux_a_realiser':
                            state="à réaliser"
                        if row['state']=='analyse_ot':
                            state="à analyser"
                        if row['state']=='travaux_a_valider':
                            state="à valider"
                        if row['state']=='analyse_ot':
                            niv=3
                        else:
                            if row['gravite']=='1':
                                    niv=1
                            if row['gravite']=='2':
                                    niv=2
                        if row['state']=='travaux_a_valider':
                            niv=4
                        if niv<mem_niv:
                            mem_niv=niv
                            title="- OT presse %s %s (Gravité=%s)"%(row["name"],state,row['gravite'])
                    if title:
                        info.append(title)

                    #** Recherche si la presse est prioritaire ********************
                    if obj.presse_id.is_prioritaire:
                        info.append("- Presse prioritaire")

                if cr_dynacase:
                    if obj.of1_id:
                        #** Recherche acceptation EI dans Dynacase ****************
                        moule = obj.of1_id.product_id.is_mold_id.name
                        if moule:
                            AcceptationEI=True
                            SQL=""""
                                select id,plasfil_moule,plasfil_dateend,plasfil_j_etat 
                                from doc1225 
                                where 
                                    locked='0' and 
                                    plasfil_dateend<now() and 
                                    plasfil_j_etat='AF' 
                            """

                            SQL=SQL + " and plasfil_moule='"+moule+"' "

                            _logger.info(SQL)



                            cr_dynacase.execute(SQL)
                            result = cr_dynacase.fetchall()
                            for row in result:
                                AcceptationEI=False
                        if AcceptationEI==False:
                            info.append("- Acceptation EI non validée")

            info = "\n".join(info)
            obj.info_planning1 = info
       

    @api.multi
    def of1_id_change(self, mpwl_id):
        values = {}
        if mpwl_id:
            mpwl = self.env['is.mrp.production.workcenter.line'].browse(mpwl_id)
            mod=0
            matieres=[]
            for line in mpwl.name.product_lines:
                code=line.product_id.is_code
                if code[:1]=='5':
                    if code not in matieres:
                        matieres.append(code)
            matieres=u', '.join(matieres)
            for line in mpwl.name.routing_id.workcenter_lines:
                if line.is_nb_mod:
                    mod=line.is_nb_mod
            values['mod1']     = mod
            values['moule1']   = mpwl.name.product_id.is_mold_dossierf
            values['matiere1'] = matieres
        return {'value': values}

    @api.multi
    def of2_id_change(self, mpwl_id):
        values = {}
        if mpwl_id:
            mpwl = self.env['is.mrp.production.workcenter.line'].browse(mpwl_id)
            mod=0
            matieres=[]
            for line in mpwl.name.product_lines:
                code=line.product_id.is_code
                if code[:1]=='5':
                    if code not in matieres:
                        matieres.append(code)
            matieres=u', '.join(matieres)
            for line in mpwl.name.routing_id.workcenter_lines:
                if line.is_nb_mod:
                    mod=line.is_nb_mod
            matiere=mpwl.name.product_id.is_couleur
            values['mod2']     = mod
            values['moule2']   = mpwl.name.product_id.is_mold_dossierf
            values['matiere2'] = matieres
        return {'value': values}



class is_consigne_journaliere_ass(models.Model):
    _name='is.consigne.journaliere.ass'
    _order='consigne_id,sequence'

    consigne_id    = fields.Many2one('is.consigne.journaliere', 'Consigne journaliere', required=True, ondelete='cascade', readonly=True)
    sequence       = fields.Integer('Ordre')
    poste_id       = fields.Many2one('mrp.workcenter', 'Poste', 
                    domain=[('resource_type','=','material'),('code','>=','9000'),('name','not ilike','GENERIQUE')])
    priorite       = fields.Char('Priorité')
    mod            = fields.Float('MOD')
    operateur      = fields.Char('Opérateur')
    of1_id         = fields.Many2one('is.mrp.production.workcenter.line', 'OF en cours')
    of2_id         = fields.Many2one('is.mrp.production.workcenter.line', 'OF suivant')
    remarque       = fields.Text('Remarques / Consignes')

