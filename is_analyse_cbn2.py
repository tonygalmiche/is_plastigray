# -*- coding: utf-8 -*-
from openerp import models,fields,api
import time
import datetime
from collections import OrderedDict
import tempfile
import logging
_logger = logging.getLogger(__name__)


def duree(debut):
    dt = datetime.datetime.now() - debut
    ms = (dt.days * 24 * 60 * 60 + dt.seconds) * 1000 + dt.microseconds / 1000.0
    ms=int(ms)
    return ms


def _now(debut):
    return str(int(duree(debut)/100.0)/10.0)+"s"


class product_product(models.Model):
    _inherit = "product.product"


    @api.model
    def load_tr(self,filter,trcolor,trid):
        product_id=filter.get('product_id')
        res=self.analyse_cbn2(filter,trcolor,trid)

        html=res['html']

        vals={
            'product_id': product_id,
            'html'      : html, 
        }
        return vals


    @api.model
    def _get_titre(self,type_rapport,valorisation):
        titre="Suggestions de fabrication (2.0)"
        if type_rapport=="Achat":
            titre="Suggestions d'achat";
        if valorisation:
            titre="Valorisation stock fabrication"
            if type_rapport=="Achat":
                titre="Valorisation stock achat (2.0)"
        return titre


    @api.model
    def _get_cat2id(self):
        cr, uid, context = self.env.args
        SQL="""
            select id, name
            from is_category 
            where id>0
        """
        cr.execute(SQL)
        result = cr.fetchall()
        cat2id={}
        for row in result:
            cat2id[row[1]]=row[0]
        return cat2id


    @api.model
    def _get_Couts(self):
        cr, uid, context = self.env.args
        SQL="""
            select name, cout_act_total
            from is_cout 
        """
        cr.execute(SQL)
        result = cr.fetchall()
        Couts={}
        for row in result:
            Couts[row[0]]=row[1]
        return Couts


    @api.model
    def _get_TypeCde(self,type_rapport):
        cr, uid, context = self.env.args
        TypeCde={}
        if type_rapport=="Achat":
            SQL="""
                SELECT 
                    cof.type_commande, 
                    cof.partner_id, 
                    rp.is_code, 
                    rp.is_adr_code, 
                    cofp.product_id
                FROM is_cde_ouverte_fournisseur cof inner join is_cde_ouverte_fournisseur_product cofp on cofp.order_id=cof.id
                                                    inner join res_partner rp on cof.partner_id=rp.id
            """
            cr.execute(SQL)
            result = cr.fetchall()
            for row in result:
                cle=('0000'+row[2])[-4:]+'-'+row[3]+'/'+str(row[4])
                TypeCde[cle]=row[0]
            SQL="""
                SELECT 
                    rp.is_code, 
                    rp.is_adr_code, 
                    product_id
                FROM is_cde_ferme_cadencee cfc inner join res_partner rp on cfc.partner_id=rp.id
            """
            cr.execute(SQL)
            result = cr.fetchall()
            for row in result:
                cle=('0000'+row[0])[-4:]+'-'+row[1]+'/'+str(row[2])
                TypeCde[cle]=u'cadencée'
        return TypeCde


    @api.model
    def _get_select_gest(self,filtre,fournisseur):
        cr, uid, context = self.env.args
        SQL="""
            SELECT distinct ig.name gest
            FROM product_product pp inner join product_template      pt   on pp.product_tmpl_id=pt.id

                                    left outer join is_mold          im   on pt.is_mold_id=im.id
                                    left outer join is_dossierf      id   on pt.is_dossierf_id=id.id
                                    inner join      is_gestionnaire  ig   on pt.is_gestionnaire_id=ig.id
                                    left outer join is_category      ic   on pt.is_category_id=ic.id
                                    left outer join is_mold_project  imp1 on im.project=imp1.id
                                    left outer join is_mold_project  imp2 on id.project=imp2.id
                                    left outer join res_partner      rp   on pt.is_client_id=rp.id
            WHERE pp.id>0 """+filtre+"""
        """
        if fournisseur:
            code=fournisseur.split('-')[0]
            SQL=SQL+""" 
                and (
                    (
                        select rp2.is_code 
                        from product_supplierinfo ps inner join res_partner rp2 on ps.name=rp2.id   
                        where ps.product_tmpl_id=pt.id order by ps.sequence,ps.id limit 1
                    )='"""+code+"""'
                )

            """
        SQL=SQL+""" ORDER BY ig.name """
        cr.execute(SQL)
        result = cr.fetchall()
        SelectGestionnaires={}
        for row in result:
            SelectGestionnaires[row[0]]=1
        SelectGestionnaires=OrderedDict(sorted(SelectGestionnaires.items(), key=lambda t: t[0]))

        select_gest=[]
        select_gest.append('')
        for x in SelectGestionnaires:
            select_gest.append(x)
        return select_gest


    @api.model
    def _get_select_fournisseur(self,filtre,gest=False):
        cr, uid, context = self.env.args
        if gest:
            filtre=filtre+" and ig.name='"+gest+"' "

        #** Recherche des articles ayant des données ***************************
        #debut=datetime.datetime.now()
        #_logger.info('Début')
        #_logger.info('Fin '+_now(debut))
        r1=self._get_FS_SA(filtre)
        r2=self._get_CF_CP(filtre)
        r3=self._get_FL(filtre)
        r4=self._get_FM(filtre)
        r5=self._get_SF(filtre)
        product_ids=[]
        for row in (r1+r2+r3+r4+r5):
            product_id=str(row[5])
            if product_id not in product_ids:
                product_ids.append(product_id)
        #_logger.info('Fin '+_now(debut))
        #***********************************************************************

        SQL="""
            SELECT 
                (   select concat(rp2.is_code,'-',rp2.is_adr_code)
                    from product_supplierinfo ps inner join res_partner rp2 on ps.name=rp2.id   
                    where ps.product_tmpl_id=pt.id order by ps.sequence,ps.id limit 1
                ) code_fournisseur

            FROM product_product pp inner join product_template      pt   on pp.product_tmpl_id=pt.id
                                    left outer join is_mold          im   on pt.is_mold_id=im.id
                                    left outer join is_dossierf      id   on pt.is_dossierf_id=id.id
                                    inner join      is_gestionnaire  ig   on pt.is_gestionnaire_id=ig.id
                                    left outer join is_category      ic   on pt.is_category_id=ic.id
                                    left outer join is_mold_project  imp1 on im.project=imp1.id
                                    left outer join is_mold_project  imp2 on id.project=imp2.id
                                    left outer join res_partner      rp   on pt.is_client_id=rp.id
          WHERE pp.id>0 """+filtre+"""
        """
        if len(product_ids):
            SQL=SQL+" AND pp.id in ("+','.join(product_ids)+") "
        cr.execute(SQL)
        result = cr.fetchall()
        select_fournisseur=[]
        select_fournisseur.append('')
        for row in result:
            cle=row[0]
            if cle and cle not in select_fournisseur:
                select_fournisseur.append(cle)
        select_fournisseur.sort()
        return select_fournisseur


    @api.model
    def _get_TabSemaines(self,nb_semaines):
        date=datetime.datetime.now()
        jour=date.weekday()
        date = date - datetime.timedelta(days=jour)
        TabSemaines=[]
        for i in range(0,int(nb_semaines)):
            d=date.strftime('%Y%m%d')
            TabSemaines.append(d)
            date = date + datetime.timedelta(days=7)
        return TabSemaines


    @api.model
    def _get_Stocks(self,control_quality='f'):
        cr, uid, context = self.env.args
        SQL="""
            select sq.product_id, sum(sq.qty) as qt
            from stock_quant sq inner join stock_location sl on sq.location_id=sl.id 
            where 
                sl.usage='internal' and 
                sl.active='t' and 
                sl.control_quality='"""+control_quality+"""' 
            group by sq.product_id 
            order by sq.product_id
        """
        cr.execute(SQL)
        result = cr.fetchall()
        Stocks={}
        for row in result:
            Stocks[row[0]]=row[1]
        return Stocks


    @api.model
    def _get_StocksSecu(self):
        cr, uid, context = self.env.args
        SQL="""
            select pp.id, pt.is_stock_secu as qt
            from product_product pp inner join product_template pt on pp.product_tmpl_id=pt.id 
        """
        cr.execute(SQL)
        result = cr.fetchall()
        StocksSecu={}
        for row in result:
            StocksSecu[row[0]]=row[1]
        return StocksSecu


    @api.model
    def _get_Fournisseurs_Delai_Fournisseurs(self):
        cr, uid, context = self.env.args
        SQL="""
            select 
                a.id      as product_id, 
                c.is_code as is_code, 
                c.name    as name, 
                b.delay   as delay, 
                c.is_adr_code
            from product_product a, product_supplierinfo b, res_partner c 
            where a.product_tmpl_id=b.product_tmpl_id and b.name=c.id 
            order by b.sequence, b.id
        """
        cr.execute(SQL)
        result = cr.fetchall()
        Fournisseurs={}
        Delai_Fournisseurs={}
        for row in result:
            name=('0000'+row[1])[-4:]+'-'+row[4]
            if name=='':
                name=row[2]
            Fournisseurs[row[0]]=name
            Delai_Fournisseurs[row[0]]=row[3]
        return [Fournisseurs,Delai_Fournisseurs]


    @api.model
    def _get_FS_SA(self,filtre):
        cr, uid, context = self.env.args
        SQL="""
            SELECT 
                mp.id as numod, 
                mp.start_date as date_debut, 
                mp.start_date_cq as date_fin, 
                mp.quantity as qt, 
                mp.type as typeod, 
                mp.product_id,
                pt.is_code as code, 
                pp.name_template as designation, 
                pt.is_stock_secu, 
                pt.produce_delay, 
                pt.lot_mini, 
                pt.multiple,
                pt.is_mold_dossierf as moule,
                mp.name as name,
                ig.name as gest
            FROM mrp_prevision mp inner join product_product      pp   on mp.product_id=pp.id 
                                  inner join product_template     pt   on pp.product_tmpl_id=pt.id
                                  left outer join is_mold         im   on pt.is_mold_id=im.id
                                  left outer join is_dossierf     id   on pt.is_dossierf_id=id.id
                                  left outer join is_gestionnaire ig   on pt.is_gestionnaire_id=ig.id
                                  left outer join is_category     ic   on pt.is_category_id=ic.id
                                  left outer join is_mold_project imp1 on im.project=imp1.id
                                  left outer join is_mold_project imp2 on id.project=imp2.id
                                  left outer join res_partner     rp   on pt.is_client_id=rp.id
            WHERE mp.id>0 """+filtre+""" 
            ORDER BY mp.name
        """
        cr.execute(SQL)
        result = cr.fetchall()
        return result


    @api.model
    def _get_CF_CP(self,filtre):
        cr, uid, context = self.env.args
        SQL="""
            SELECT 
                so.id as numod, 
                sol.is_date_expedition as date_debut, 
                sol.is_date_expedition as date_fin, 
                sol.product_uom_qty as qt, 
                sol.is_type_commande as typeod, 
                sol.product_id, 
                pt.is_code as code, 
                pp.name_template as designation, 
                pt.is_stock_secu, 
                pt.produce_delay, 
                pt.lot_mini, 
                pt.multiple,
                pt.is_mold_dossierf as moule,
                so.name as name
            FROM sale_order_line sol inner join sale_order           so   on sol.order_id=so.id 
                               inner join product_product      pp   on sol.product_id=pp.id
                               inner join product_template     pt   on pp.product_tmpl_id=pt.id
                               left outer join is_mold         im   on pt.is_mold_id=im.id
                               left outer join is_dossierf     id   on pt.is_dossierf_id=id.id
                               left outer join is_gestionnaire ig   on pt.is_gestionnaire_id=ig.id
                               left outer join is_category     ic   on pt.is_category_id=ic.id
                               left outer join is_mold_project imp1 on im.project=imp1.id
                               left outer join is_mold_project imp2 on id.project=imp2.id
                               left outer join res_partner     rp   on pt.is_client_id=rp.id
            WHERE sol.id>0 """+filtre+""" and sol.state<>'done' and sol.state<>'cancel'
            ORDER BY sol.name
        """
        cr.execute(SQL)
        result = cr.fetchall()
        return result


    @api.model
    def _get_FL(self,filtre):
        cr, uid, context = self.env.args
        SQL="""
            SELECT 
                mp.id as numod, 
                mp.date_planned as date_debut, 
                mp.date_planned as date_fin, 
                sm.product_qty as qt, 
                'FL' as typeod, 
                sm.product_id, 
                pt.is_code as code, 
                pp.name_template as designation, 
                pt.is_stock_secu, 
                pt.produce_delay, 
                pt.lot_mini, 
                pt.multiple,
                pt.is_mold_dossierf as moule,
                mp.name as name
            FROM stock_move sm    inner join product_product       pp   on sm.product_id=pp.id
                                  inner join product_template      pt   on pp.product_tmpl_id=pt.id
                                   inner join mrp_production       mp   on mp.id=sm.production_id
                                    left outer join is_mold        im   on pt.is_mold_id=im.id
                                   left outer join is_dossierf     id   on pt.is_dossierf_id=id.id
                                   left outer join is_gestionnaire ig   on pt.is_gestionnaire_id=ig.id
                                   left outer join is_category     ic   on pt.is_category_id=ic.id and ic.name!='74'
                                   left outer join is_mold_project imp1 on im.project=imp1.id
                                   left outer join is_mold_project imp2 on id.project=imp2.id
                                   left outer join res_partner     rp   on pt.is_client_id=rp.id
            WHERE sm.id>0 """+filtre+""" and production_id>0 and sm.state<>'done' and sm.state<>'cancel'
            ORDER BY sm.name 
        """
        cr.execute(SQL)
        result = cr.fetchall()
        return result


    @api.model
    def _get_FM(self,filtre):
        cr, uid, context = self.env.args
        SQL="""
            SELECT 
                sm.id as numod, 
                sm.date_expected as date_debut, 
                sm.date_expected as date_fin, 
                sm.product_qty as qt, 
                'FM' as typeod, 
                sm.product_id, 
                pt.is_code as code, 
                pp.name_template as designation, 
                pt.is_stock_secu, 
                pt.produce_delay, 
                pt.lot_mini, 
                pt.multiple,
                pt.is_mold_dossierf as moule,
                sm.name as name
            FROM stock_move sm    inner join product_product      pp   on sm.product_id=pp.id
                            inner join product_template     pt   on pp.product_tmpl_id=pt.id
                            left outer join is_mold         im   on pt.is_mold_id=im.id
                            left outer join is_dossierf     id   on pt.is_dossierf_id=id.id
                            left outer join is_gestionnaire ig   on pt.is_gestionnaire_id=ig.id
                            left outer join is_category     ic   on pt.is_category_id=ic.id
                            left outer join is_mold_project imp1 on im.project=imp1.id
                            left outer join is_mold_project imp2 on id.project=imp2.id
                            left outer join res_partner     rp   on pt.is_client_id=rp.id

            WHERE sm.id>0 """+filtre+""" and raw_material_production_id>0 and sm.state<>'done' and sm.state<>'cancel' 
            ORDER BY sm.name
        """
        cr.execute(SQL)
        result = cr.fetchall()
        return result


    @api.model
    def _get_SF(self,filtre):
        cr, uid, context = self.env.args
        SQL="""
            SELECT 
                po.id as numod, 
                pol.date_planned as date_debut, 
                pol.date_planned as date_fin, 
                sm.product_qty as qt, 
                'SF' as typeod, 
                pol.product_id, 
                pt.is_code as code, 
                pp.name_template as designation, 
                pt.is_stock_secu, 
                pt.produce_delay, 
                pt.lot_mini, 
                pt.multiple,
                pt.is_mold_dossierf as moule,
                po.name as name
            FROM purchase_order_line pol left outer join purchase_order po    on pol.order_id=po.id 
                                     inner join product_product           pp    on pol.product_id=pp.id
                                     inner join product_template          pt    on pp.product_tmpl_id=pt.id
                                     inner join stock_move                sm    on pol.id=sm.purchase_line_id
                                     left outer join is_mold              im    on pt.is_mold_id=im.id
                                     left outer join is_dossierf          id    on pt.is_dossierf_id=id.id
                                     left outer join is_gestionnaire      ig    on pt.is_gestionnaire_id=ig.id
                                     left outer join is_category          ic    on pt.is_category_id=ic.id and ic.name not in ('70','72','73','74')
                                     left outer join is_mold_project      imp1  on im.project=imp1.id
                                     left outer join is_mold_project      imp2  on id.project=imp2.id
                                     left outer join res_partner          rp    on pt.is_client_id=rp.id
              WHERE pol.id>0 """+filtre+""" and pol.state<>'draft' and pol.state<>'done' and pol.state<>'cancel'
                    and sm.state in ('draft','waiting','confirmed','assigned')
              ORDER BY pol.name
        """
        cr.execute(SQL)
        result = cr.fetchall()
        return result


    @api.model
    def _get_stock(self,filtre):
        cr, uid, context = self.env.args
        SQL="""
            SELECT 
                pt.id as numod, 
                '' as date_debut, 
                '' as date_fin, 
                0 as qt, 
                'stock' as typeod, 
                pp.id as product_id, 
                pt.is_code as code, 
                pp.name_template as designation, 
                pt.is_stock_secu, 
                pt.produce_delay, 
                pt.lot_mini, 
                pt.multiple,
                pt.is_mold_dossierf as moule,
                pp.name_template as name
            FROM product_product pp inner join product_template         pt    on pp.product_tmpl_id=pt.id
                                   left outer join is_mold              im    on pt.is_mold_id=im.id
                                   left outer join is_dossierf          id    on pt.is_dossierf_id=id.id
                                   left outer join is_gestionnaire      ig    on pt.is_gestionnaire_id=ig.id
                                   left outer join is_category          ic    on pt.is_category_id=ic.id and ic.name not in ('70','72','73','74')
                                   left outer join is_mold_project      imp1  on im.project=imp1.id
                                   left outer join is_mold_project      imp2  on id.project=imp2.id
                                   left outer join res_partner          rp    on pt.is_client_id=rp.id
            WHERE pt.id>0 """+filtre+"""
            ORDER BY pt.is_code
        """
        cr.execute(SQL)
        result = cr.fetchall()
        return result




    @api.model
    def analyse_cbn2(self,filter=False,trcolor=False,trid=False):
        cr, uid, context = self.env.args
        debut=datetime.datetime.now()
        _logger.info('Début requête')
        product_id=filter.get('product_id',False)
        validation    = filter['validation']
        if validation=='ko':
            #** Lecture des critères enregistrés *******************************
            code_pg_debut = self.env['is.mem.var'].get(uid,'code_pg_debut')
            gest = self.env['is.mem.var'].get(uid,'gest')
            cat = self.env['is.mem.var'].get(uid,'cat')
            moule = self.env['is.mem.var'].get(uid,'moule')
            projet = self.env['is.mem.var'].get(uid,'projet')
            client = self.env['is.mem.var'].get(uid,'client')
            fournisseur = self.env['is.mem.var'].get(uid,'fournisseur')
            type_commande = self.env['is.mem.var'].get(uid,'type_commande')
            type_rapport  = self.env['is.mem.var'].get(uid,'type_rapport')
            calage = self.env['is.mem.var'].get(uid,'calage')
            nb_semaines   = self.env['is.mem.var'].get(uid,'nb_semaines')
            valorisation=''
        else:
            #** Lecture des filtres ********************************************
            code_pg_debut = filter['code_pg_debut']
            gest          = filter['gest']
            cat           = filter['cat']
            moule         = filter['moule']
            projet        = filter['projet']
            client        = filter['client']
            fournisseur   = filter['fournisseur']
            type_commande = filter['type_commande']
            type_rapport  = filter['type_rapport']
            calage        = filter['calage']
            nb_semaines   = filter['nb_semaines']
            valorisation  = filter['valorisation']
            #*******************************************************************


            #** Enregistrement des critères enregistrés ************************
            self.env['is.mem.var'].set(uid, 'code_pg_debut', code_pg_debut)
            self.env['is.mem.var'].set(uid, 'gest', gest)
            self.env['is.mem.var'].set(uid, 'cat', cat)
            self.env['is.mem.var'].set(uid, 'moule', moule)
            self.env['is.mem.var'].set(uid, 'projet', projet)
            self.env['is.mem.var'].set(uid, 'client', client)
            self.env['is.mem.var'].set(uid, 'fournisseur', fournisseur)
            self.env['is.mem.var'].set(uid, 'type_commande', type_commande)
            self.env['is.mem.var'].set(uid, 'type_rapport', type_rapport)
            self.env['is.mem.var'].set(uid, 'calage', calage)
            self.env['is.mem.var'].set(uid, 'nb_semaines', nb_semaines)
            #*******************************************************************


        #** Valeur par défaut **************************************************
        code_pg_debut = code_pg_debut  or ''
        gest          = gest           or ''
        cat           = cat            or ''
        moule         = moule          or ''
        projet        = projet         or ''
        client        = client         or ''
        fournisseur   = fournisseur    or ''
        type_commande = type_commande  or ''
        type_rapport  = type_rapport   or 'Fabrication'
        calage        = calage         or 'Date de fin'
        nb_semaines   = nb_semaines    or 18
        nb_semaines   = int(nb_semaines)
        height        = filter.get('height')
        #***********************************************************************


        # ** Filtre pour les requêtes ******************************************
        filtre="";

        if product_id:
            filtre=filtre+" and pp.id="+str(product_id)+" "

        if code_pg_debut:
            filtre=filtre+" and pt.is_code ilike '"+code_pg_debut+"%' "
        if type_rapport=="Achat":
            filtre=filtre+" and pt.purchase_ok=true "
        else:
            filtre=filtre+" and pt.purchase_ok<>true "
        if cat:
            filtre=filtre+" and ic.name='"+cat+"' "
        if moule:
            filtre=filtre+" and (im.name='"+moule+"' or id.name='"+moule+"' )"
        if projet:
            filtre=filtre+" and (imp1.name ilike '%"+projet+"%' or imp2.name ilike '%"+projet+"%') "
        if client:
            filtre=filtre+" and rp.is_code='"+client+"' "
        # **********************************************************************


        #** Listes de choix des filtres ****************************************
        select_nb_semaines=[4,8,12,16,18,20,30,40,60]
        select_type_commande=['','ferme_uniquement','ferme','ouverte','cadencée']
        select_type_rapport=['Fabrication','Achat']
        select_calage=['Date de fin','Date de début']
        #***********************************************************************


        titre              = self._get_titre(type_rapport,valorisation)  # Titre du rapport
        cat2id             = self._get_cat2id()                          # Catégories
        Couts              = self._get_Couts()                           # Coûts
        TypeCde            = self._get_TypeCde(type_rapport)             # Type de commande d'achat
        select_gest        = self._get_select_gest(filtre,fournisseur)   # Liste des gestionnaires
        select_fournisseur = self._get_select_fournisseur(filtre,gest)   # Liste des fournisseurs


        if validation=='ko':
            html='Indiquez vos critères de filtre et validez'
        else:
            # ** Filtre sur le fournisseur (partner_id) ****************************
            partner_id=False
            if fournisseur:
                tab=fournisseur.split('-')
                SQL="select id from res_partner where is_code='"+tab[0]+"' and is_adr_code='"+tab[1]+"' "
                cr.execute(SQL)
                result = cr.fetchall()
                for row in result:
                    partner_id=row[0]
            if gest:
                filtre=filtre+" and ig.name='"+gest+"' "
            if partner_id:
                filtre=filtre+""" 
                    and (
                            (   select rp2.id from product_supplierinfo ps inner join res_partner rp2 on ps.name=rp2.id   
                                where ps.product_tmpl_id=pt.id order by ps.sequence limit 1
                            )="""+str(partner_id)+"""
                        )
                """
            filtre=filtre+" AND ic.name!='80' "
            # **********************************************************************

            TabSemaines = self._get_TabSemaines(nb_semaines) # Tableau des semaines
            StocksA     = self._get_Stocks('f')              # StocksA (control_quality=f)
            StocksQ     = self._get_Stocks('t')              # StocksQ (control_quality=t)
            StocksSecu  = self._get_StocksSecu()             # StocksSecu
            Fournisseurs, Delai_Fournisseurs = self._get_Fournisseurs_Delai_Fournisseurs() # Fournisseurs + Delai_Fournisseurs

            # ** Recherche des Prévisions du CBN  ******************************
            TabIni={};
            result = self._get_FS_SA(filtre)
            TabIni=self.RemplitTab2(TabIni, result, TabSemaines, type_rapport, 
                StocksA, StocksQ, StocksSecu, Fournisseurs, Delai_Fournisseurs, 
                calage, valorisation, Couts, fournisseur, TypeCde, type_commande)
            # ******************************************************************

            # ** Recherche des commandes client ********************************
            result = self._get_CF_CP(filtre)
            TabIni=self.RemplitTab2(TabIni, result, TabSemaines, type_rapport, 
                StocksA, StocksQ, StocksSecu, Fournisseurs, Delai_Fournisseurs, 
                calage, valorisation, Couts, fournisseur, TypeCde, type_commande)
            # ******************************************************************

            # ** Recherche des OF **********************************************
            result = self._get_FL(filtre)
            TabIni=self.RemplitTab2(TabIni, result, TabSemaines, type_rapport, 
                StocksA, StocksQ, StocksSecu, Fournisseurs, Delai_Fournisseurs, 
                calage, valorisation, Couts, fournisseur, TypeCde, type_commande)
            # ******************************************************************

            # ** Recherche des composants des OF *******************************
            result = self._get_FM(filtre)
            TabIni=self.RemplitTab2(TabIni, result, TabSemaines, type_rapport, 
                StocksA, StocksQ, StocksSecu, Fournisseurs, Delai_Fournisseurs, 
                calage, valorisation, Couts, fournisseur, TypeCde, type_commande)
            # ******************************************************************

            # ** Recherche des commandes fournisseurs  *************************
            result = self._get_SF(filtre)
            TabIni=self.RemplitTab2(TabIni, result, TabSemaines, type_rapport, 
                StocksA, StocksQ, StocksSecu, Fournisseurs, Delai_Fournisseurs, 
                calage, valorisation, Couts, fournisseur, TypeCde, type_commande)
            # ******************************************************************

            # ** Recherche pour avoir tous les articles dans le résultat  ******
            if valorisation:
                result = self._get_stock(filtre)
                TabIni=self.RemplitTab2(TabIni, result, TabSemaines, type_rapport, 
                    StocksA, StocksQ, StocksSecu, Fournisseurs, Delai_Fournisseurs, 
                    calage, valorisation, Couts, fournisseur, TypeCde, type_commande)
            # ******************************************************************

            #** RemplitTab2Sho *************************************************
            TabSho={};
            lig=0;
            Tab=TabIni
            for key, val in Tab.iteritems():
                Type=Tab[key]['TYPE']
                if Type!='99-Stock':
                    color=self.color_cel(Type)
                    if 0 not in TabSho:
                        TabSho[0]={}
                    if 1 not in TabSho:
                        TabSho[1]={}
                    TabSho[0][lig]=Tab[key]["Code"]
                    TabSho[1][lig]=Type
                    Type=Type[3:]
                    for i in range(0, nb_semaines):
                        k=TabSemaines[i]
                        if k in Tab[key]:
                            Qt=round(Tab[key][k],2)
                        else:
                            Qt=0
                        Lien="#"
                        k=TabSemaines[i]+'OT'
                        if k in Tab[key]:
                            OT=Tab[key][k]
                            OT=OT[0:len(OT)-1]
                        else:
                            OT=''
                        k=TabSemaines[i]+'INFO'
                        if k in Tab[key]:
                            INFO=Tab[key][k]
                        else:
                            INFO=''
                        docid=''
                        if Type=='FS' or Type=='SA' or Type=='CF' or Type=='CP' or Type=='FL' or Type=='SF':
                            Lien="Modif_FS_Liste.php?zzTypeOD="+Type.lower()+"&zzNumOD="+str(OT)
                            docid=str(OT)
                        k=i+2
                        if k not in TabSho:
                            TabSho[k]={}

                        if Qt==0 and color!='Black':
                            val=''
                        else:
                            val="{0:10.0f}".format(Qt)
                        TabSho[k][lig]="<a style=\"color:"+color+";\" class=\"info\" type='"+Type+"' docid='"+str(docid)+"'>"+val+"<span>"+INFO+"</span></a>"

                        #** Calcul du stock theorique **************************
                        if Tab[key]['TYPE']=='90-Stock':
                            if i==0:
                                Stock=Tab[key][0]+Qt
                            else:
                                q=TabSho[1+i][lig]
                                Stock=TabSho[1+i][lig]+Qt
                            TabSho[2+i][lig]=Stock

                        #*******************************************************

                        #** Calcul du stock valorisé ***************************
                        if Tab[key]['TYPE']=='92-Stock Valorisé':
                            if i==0:
                                Stock=Tab[key][0]+Qt;
                            else:
                               Stock=TabSho[1+i][lig]+Qt;
                            TabSho[2+i][lig]=round(Stock,2)
                        #*******************************************************
                    lig+=1
            Tab=TabSho
            # ******************************************************************

            NomCol = ["Sécu / Délai / Lot / Multi / Stock A/Q", "Type"]
            Style  = ["NormalLN", "NormalCN"]
            Format = ["TEXT"    , "TEXT"    ]
            Total  = [0         , 0         ]
            Lien   = [""        , ""        ]
            Size   = [220       , 40        ]


            # ** Tableau des semaines ******************************************
            date=datetime.datetime.now()
            jour=date.weekday()
            date = date - datetime.timedelta(days=jour)
            TabSemaines=[]
            for i in range(0,int(nb_semaines)):
                s='S'+str(date.isocalendar()[1])+'<br />'+date.strftime('%d.%m')
                TabSemaines.append(s)
                date = date + datetime.timedelta(days=7)
            # ******************************************************************


            for i in range(0,int(nb_semaines)):
                NomCol.append(TabSemaines[i])
                Style.append("NormalRN")
                Format.append("TEXT")
                Total.append(0)
                Lien.append("")
                Size.append(48)
            width=220+40+nb_semaines*(48+2)+22


            #** Création des listes et de la clé de tri  ***********************
            lst={}
            lst['key']=[]
            for col, v1 in Tab.iteritems():
                lst[col]=[]
                for lig, v2 in v1.iteritems():
                    if col==1:
                        key=Tab[0][lig]+Tab[1][lig]
                        lst['key'].append(key)
                    lst[col].append(v2)
            #*******************************************************************


            #** Tri des listes *************************************************
            z=[]
            z.append(lst['key'])
            for col in range(0,len(Tab)):
                z.append(lst[col])
            NewTab=zip(*z)
            NewTab.sort()
            #*******************************************************************


            #** Reconsctuction du Tab ******************************************
            Tab={}
            lig=0
            for row in NewTab:
                col=0
                for cel in row:
                    if col>0:
                        if lig==0:
                            Tab[col-1]={}
                        Tab[col-1][lig]=cel
                    col+=1

                lig+=1
            #*******************************************************************


            #** Génération du fichier CSV **************************************
            attachment_id=''

            if valorisation and Tab:
                csv={};
                for lig in range(0,len(Tab[0])):
                    #** Recherche du CodePG et de la désignation ***************
                    Key=Tab[0][lig]
                    Key=Key.split('</b>')
                    Key=Key[0]
                    Key=Key.split('<b>')
                    Key=Key[1]
                    CodePG=Key
                    Key=Tab[0][lig]
                    Key=Key.split('<br />')
                    Key=Key[1]
                    Designation=Key
                    #***********************************************************

                    if CodePG not in csv:
                        csv[CodePG]={}
                    csv[CodePG][0]=CodePG
                    csv[CodePG][1]=Designation
                    Type=Tab[1][lig]
                    if Type=='90-Stock':
                        for col in range(2,len(Tab)):
                            csv[CodePG][col*1000+1]=Tab[col][lig]
                    if Type=='92-Stock Valorisé':
                        for col in range(2,len(Tab)):
                            csv[CodePG][col*1000+2]=Tab[col][lig]


                #** Ecriture fichier CSV  **************************************
                user  = self.env['res.users'].browse(uid)
                name  = 'analyse-cbn-'+user.login+'.csv'
                path='/tmp/'+name
                f = open(path,'wb')
                txt=[];
                txt.append('CodePG')
                txt.append('Désignation')
                date=datetime.datetime.now()
                jour=date.weekday()
                date = date - datetime.timedelta(days=jour)
                for i in range(0,int(nb_semaines)):
                    v='Stock S'+str(date.isocalendar()[1])+' '+date.strftime('%d.%m')
                    txt.append(v)
                    v='Valorisé S'+str(date.isocalendar()[1])+' '+date.strftime('%d.%m')
                    txt.append(v)
                    date = date + datetime.timedelta(days=7)

                f.write(u'\t'.join(txt)+'\r\n')
                for k, v in csv.iteritems():
                    v=self.ksort(v)
                    txt=[]
                    for k2, v2 in v:
                        txt.append(str(v2).replace('.',','))
                    f.write(u'\t'.join(txt)+'\r\n')
                f.close()
                #***************************************************************


                # ** Creation ou modification de la pièce jointe *******************
                attachment_obj = self.env['ir.attachment']
                attachments = attachment_obj.search([('res_id','=',user.id),('name','=',name)])
                csv = open(path,'rb').read()
                vals = {
                    'name':        name,
                    'datas_fname': name,
                    'type':        'binary',
                    'res_id':      user.id,
                    'datas':       csv.encode('base64'),
                }
                attachment_id=False
                if attachments:
                    for attachment in attachments:
                        attachment.write(vals)
                        attachment_id=attachment.id
                else:
                    attachment = attachment_obj.create(vals)
                    attachment_id=attachment.id
                #*******************************************************************


            #*******************************************************************


            #** Code HTML ******************************************************
            if len(Tab)==0:
                html='Aucune donnée !'
            else:
                html=''
                alt=1
                if not product_id:
                    head="<thead><tr class=\"TitreTabC\">\n"
                    for col in range(0,len(Tab)):
                        align='left'
                        if col>1:
                            align='right'

                        head+="<th style=\"width:"+str(Size[col])+"px;text-align:"+align+"\">"+NomCol[col]+"</th>\n"
                    head+="</tr></thead>\n"
                    html+="<div style=\"width:"+str(width+20)+"px;\" id=\"table_head\">\n"
                    html+="<table style=\"border-width:0px;border-spacing:0px;padding:0px;width:"+str(width)+"px;\">\n"
                    html+=head
                    html+="</table>\n"
                    html+="</div>\n"
                    html+="<div style=\"width:"+str(width+20)+"px;\" id=\"table_body\">\n";
                    html+="<table style=\"border-width:0px;border-spacing:0px;padding:0px;width:"+str(width)+"px;\">\n";
                    html+=head;
                    html+="<tbody class=\"tbody\">\n"
                for lig in range(0,len(Tab[0])):
                    if lig>0:
                        if Tab[0][lig]!=Tab[0][lig-1]:
                            alt=-alt
                    if alt==1:
                        bgcolor="ffdec0"
                    else:
                        bgcolor="fae9da"

                    if trcolor:
                        bgcolor=trcolor[-6:]

                    if trid:
                        idtr=trid
                    else:
                        idtr=str(lig)


                    onclick = "onclick=\"clicktr('id"+idtr+"','"+bgcolor+"','2')\""

                    html+="<tr trcolor=\""+bgcolor+"\" style=\"background-color:#"+bgcolor+";\" id=\"id"+idtr+\
                        "\"onmouseover=\"clicktr('id"+idtr+"','ffff00','1')\"onmouseout=\"clicktr('id"+idtr+\
                        "','"+bgcolor+"','1')\" "+onclick+">\n"

                    for col in range(0,len(Tab)):
                        cel=Tab[col][lig]
                        if(col==1):
                            cel=cel[3:] 
                        if lig>0:
                            if col==0:
                                if Tab[0][lig]==Tab[0][lig-1]:
                                    cel="&nbsp;"
                        #** Recherche du nombre de lignes ayant le même code ***********
                        rowspan=1
                        if col==0:
                            if lig==0 or (lig>0 and Tab[0][lig]!=Tab[0][lig-1]):
                                while (lig+rowspan) in Tab[0] and Tab[0][lig]==Tab[0][lig+rowspan]:
                                    rowspan+=1
                        #***************************************************************
                        color="black"
                        if col>0:
                            color=self.color_cel(Tab[1][lig],cel)
                        if col>1:
                            if type(cel)==float:
                                if cel==0 and color!='Black':
                                    cel=''
                                else:
                                    cel="{:10.0f}".format(cel)
                            cel="<b>"+str(cel)+"</b>"
                        align='left'
                        if col>1:
                            align='right'
                        if lig==0 or col>0 or (lig>0 and Tab[0][lig]!=Tab[0][lig-1]):
                            html+="<td style=\"width:"+str(Size[col])+"px;color:"+color+";text-align:"+align+";\" rowspan=\""+str(rowspan)+"\" class=\""+Style[col]+"\">"+str(cel)+"</td>\n"
                    html+="</tr>\n"

                if not product_id:
                    html+="</tbody>\n"
                    html+="</table>\n"
                    html+="</div>"
                    if valorisation:
                        html+="<a class=\"info\" type='stock-valorise' attachment_id='"+str(attachment_id)+"'>Stock valorisé</a>\n"

            #***********************************************************************


        vals={
            'titre'               : titre,
            'code_pg_debut'       : code_pg_debut,
            'moule'               : moule,
            'cat'                 : cat,
            'projet'              : projet,
            'client'              : client,
            'valorisation'        : valorisation,
            'select_gest'         : select_gest,
            'gest'                : gest,
            'select_fournisseur'  : select_fournisseur,
            'fournisseur'         : fournisseur,
            'select_nb_semaines'  : select_nb_semaines,
            'nb_semaines'         : nb_semaines,
            'select_type_commande': select_type_commande,
            'type_commande'       : type_commande,
            'select_type_rapport' : select_type_rapport,
            'type_rapport'        : type_rapport,
            'select_calage'       : select_calage,
            'calage'              : calage,
            'html'                : html,
        }
        _logger.info('Fin requête '+_now(debut))
        return vals


    @api.model
    def ksort(self,d):
        return [(k,d[k]) for k in sorted(d.keys())]


    @api.model
    def RemplitTab2(self,Tab, result, TabSemaines, type_rapport, StocksA, 
            StocksQ, StocksSecu, Fournisseurs, Delai_Fournisseurs, calage, 
            valorisation, Couts, fournisseur, TypeCde, type_commande):

        for row in result:
            numod         = row[0]
            date_debut    = row[1]
            date_fin      = row[2]
            qt            = row[3]
            typeod        = row[4].strip()
            product_id    = row[5]
            code_pg       = row[6]
            designation   = row[7]
            is_stock_secu = row[8]
            produce_delay = row[9]
            lot_mini      = row[10]
            multiple      = row[11]
            moule         = row[12] or ''
            name          = row[13]

            test=True
            if type_rapport=='Achat':
                is_code=''
                if product_id in Fournisseurs:
                    is_code    = Fournisseurs[product_id]
                cle        = is_code+'/'+str(product_id);
                t=''
                if cle in TypeCde:
                    t=TypeCde[cle]
                    Code=code_pg+' ('+t+')';
                if type_commande!='' and type_commande!=t:
                    test=False
            StockA=0;
            StockQ=0;
            if product_id in StocksA:
                StockA=StocksA[product_id]
            if product_id in StocksQ:
                StockQ=StocksQ[product_id]
            if typeod=='stock' and StockA==0 and StockQ==0:
                test=False

            if test:
                Tri=moule
                if type_rapport=='Achat':
                    if product_id in Fournisseurs:
                        Fournisseur=Fournisseurs[product_id]
                    else:
                        Fournisseur='0000'
                    Tri=Fournisseur
                if typeod=='':
                    typeod='ferme'
                Cle=code_pg+typeod


                Code=Tri+' / <b>'+code_pg+'</b> '
                if type_rapport=='Achat' and moule!='':
                    Code=Code+' / '+moule
                if type_rapport=='Achat':
                    k       = is_code+'/'+str(product_id);
                    if k in TypeCde:
                        t=TypeCde[k]
                        Code=Code+' ('+t+')';
                if type_rapport=='Achat':
                    Delai=0
                    if product_id in Delai_Fournisseurs:
                        Delai=Delai_Fournisseurs[product_id]
                else:
                    Delai=produce_delay

                Code=Code+'<a href="#" title="Rafraichir cette ligne"><img productid="'+str(product_id)+'" src="/is_plastigray/static/src/img/refresh-icon.png" style="max-height: 16px;"/></a>'
                Code=Code+\
                    '<br />'+\
                    designation+'<br />'+\
                    "{0:10.0f}".format(is_stock_secu)+' / '+\
                    "{0:10.0f}".format(Delai)+' / '+\
                    "{0:10.0f}".format(lot_mini)+' / '+\
                    "{0:10.0f}".format(multiple)+' / '+\
                    "{0:10.0f}".format(StockA)+' / '+\
                    "{0:10.0f}".format(StockQ)
                if Cle not in Tab:
                    Tab[Cle]={}
                Tab[Cle]["Code"] = Code

                #** Les chiffres permettent de trier les lignes ****************
                t={
                    "ferme"        : "10-CF",
                    "previsionnel" : "20-CP",
                    "FL"           : "30-FL",
                    "FM"           : "40-FM",
                    "SF"           : "50-SF",
                    "ft"           : "60-FT",
                    "fs"           : "70-FS",
                    "sa"           : "80-SA",
                    "stock"        : "99-Stock",
                }
                Tab[Cle]["TYPE"] = typeod
                if typeod in t:
                    Tab[Cle]["TYPE"] = t[typeod]
                #***************************************************************


                #** Permet de déterminer le sens dans le calcul du stock *******
                t={
                    "ferme"        : -1,
                    "previsionnel" : -1,
                    "FL"           : 1,
                    "FM"           : -1,
                    "SF"           : 1,
                    "fs"           : 1,
                    "ft"           : -1,
                    "sa"           : 1,
                    "stock"        : 1,
                }
                Sens=1
                if typeod in t:
                    Sens = t[typeod]
                #***************************************************************

                if calage=='' or calage=='Date de fin':
                    DateLundi=self.datelundi(date_fin, TabSemaines)
                else:
                    DateLundi=self.datelundi(date_debut, TabSemaines)
            
                if typeod=='FL' and qt<0:
                    qt=-0.01

                if DateLundi not in Tab[Cle]:
                    Tab[Cle][DateLundi]=0
                Tab[Cle][DateLundi]=Tab[Cle][DateLundi]+round(Sens*qt,2);

                if DateLundi+'OT' not in Tab[Cle]:
                    Tab[Cle][DateLundi+'OT']=''
                Tab[Cle][DateLundi+'OT']=Tab[Cle][DateLundi+'OT']+str(numod)+","

                if DateLundi+'INFO' not in Tab[Cle]:
                    Tab[Cle][DateLundi+'INFO']=''
                Tab[Cle][DateLundi+'INFO']=Tab[Cle][DateLundi+'INFO']+name+" : "+str(round(qt,2))+'<br />'

                #** Calcul du stock theorique **********************************
                Cle=code_pg+'90-Stock'
                if Cle not in Tab:
                    Tab[Cle]={}
                Tab[Cle]['Code'] = Code
                Tab[Cle]['TYPE'] = '90-Stock'
                StockSecu=0
                if product_id in StocksSecu:
                    StockSecu=StocksSecu[product_id]

                if valorisation:
                    Tab[Cle][0]=StockA+StockQ
                else:
                    Tab[Cle][0]=StockA-StockSecu

                if DateLundi not in Tab[Cle]:
                    Tab[Cle][DateLundi]=0
                Tab[Cle][DateLundi]=Tab[Cle][DateLundi]+round(Sens*qt,2);
                #***************************************************************

                #** Valorisation stock *****************************************
                if valorisation:
                    Cout=0
                    if product_id in Couts:
                        Cout=Couts[product_id]
                    Cle1=code_pg+u'90-Stock'
                    Cle2=code_pg+u'92-Stock Valorisé'
                    if Cle2 not in Tab:
                        Tab[Cle2]={}
                    Tab[Cle2]['Code'] = Code
                    Tab[Cle2]['TYPE']=u'92-Stock Valorisé'
                    Tab[Cle2][0]=Tab[Cle1][0]*Cout
                    Tab[Cle2][DateLundi]=Tab[Cle1][DateLundi]*Cout
                #***************************************************************

        return Tab


    @api.model
    def datelundi(self,date,TabSemaines): 
        if date=='':
            return TabSemaines[0]
        date=date[:10]
        date=datetime.datetime.strptime(date, '%Y-%m-%d')
        jour=date.weekday()
        date = date - datetime.timedelta(days=jour)
        date = date.strftime('%Y%m%d')
        if date<TabSemaines[0]:
            date=TabSemaines[0]
        return date


    @api.model
    def color_cel(self,TypeOD,cel=0): 
        TypeOD=TypeOD[3:]
        t={
            "CF"    : "DarkRed",
            "CP"    : "DarkGreen",
            "FL"    : "DarkMagenta",
            "FM"    : "#000000",
            "SF"    : "DarkMagenta",
            "FS"    : "DarkBlue",
            "FT"    : "#000000",
            "SA"    : "DarkBlue",
            "Stock" : "Black",
        }
        color="Gray"
        if TypeOD in t:
            color=t[TypeOD]
        if TypeOD=='Stock' and cel<0:
            color='Red'
        return color


