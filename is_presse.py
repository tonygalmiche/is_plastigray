# -*- coding: utf-8 -*-
from openerp import models,fields,api,tools,SUPERUSER_ID
from openerp.tools.translate import _
from openerp.exceptions import Warning
from datetime import datetime
from openerp.osv import osv
import xmlrpclib


class is_presse_classe(models.Model):
    _name='is.presse.classe'
    _order='name'

    name = fields.Char(string='Classe commerciale')


class is_presse_puissance(models.Model):
    _name='is.presse.puissance'
    _order='name'

    name                   = fields.Char(string='Puissance')
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
    
    
    @api.multi
    def write(self, vals):
        try:
            res=super(is_presse_puissance, self).write(vals)
            for obj in self:
                obj.copy_other_database_presse_puissance()
            return res
        except Exception as e:
            raise osv.except_osv(_('Puissance!'),
                             _('(%s).') % str(e).decode('utf-8'))

    @api.model
    def create(self, vals):
        try:
            obj=super(is_presse_puissance, self).create(vals)
            obj.copy_other_database_presse_puissance()
            return obj
        except Exception as e:
            raise osv.except_osv(_('Puissance!'),
                             _('(%s).') % str(e).decode('utf-8'))
            
    @api.multi
    def copy_other_database_presse_puissance(self):
        cr , uid, context = self.env.args
        context = dict(context)
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for puissance in self:
            for database in database_lines:
                if not database.ip_server or not database.database or not database.port_server or not database.login or not database.password:
                    continue
                DB = database.database
                USERID = SUPERUSER_ID
                DBLOGIN = database.login
                USERPASS = database.password
                DB_SERVER = database.ip_server
                DB_PORT = database.port_server
                sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/object' % (DB_SERVER, DB_PORT))
                presse_puissance_vals = self.get_presse_puissance_vals(puissance, DB, USERID, USERPASS, sock)
                dest_presse_puissance_ids = sock.execute(DB, USERID, USERPASS, 'is.presse.puissance', 'search', [('is_database_origine_id', '=', puissance.id)], {})
                if not dest_presse_puissance_ids:
                    dest_presse_puissance_ids = sock.execute(DB, USERID, USERPASS, 'is.presse.puissance', 'search', [('name', '=', puissance.name)], {})
                if dest_presse_puissance_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.presse.puissance', 'write', dest_presse_puissance_ids, presse_puissance_vals, {})
                    presse_puissance_created_id = dest_presse_puissance_ids[0]
                else:
                    presse_puissance_created_id = sock.execute(DB, USERID, USERPASS, 'is.presse.puissance', 'create', presse_puissance_vals, {})
        return True

    @api.model
    def get_presse_puissance_vals(self, puissance, DB, USERID, USERPASS, sock):
        presse_puissance_vals ={
                     'name' : tools.ustr(puissance.name),
                     'is_database_origine_id':puissance.id,
                     }
        return presse_puissance_vals







class is_outillage_constructeur(models.Model):
    _name='is.outillage.constructeur'
    _order='name'

    name = fields.Char(string='Name')


class is_presse(models.Model):
    _name='is.presse'
    _order='name'
    _sql_constraints = [('name_uniq','UNIQUE(name)', u'Ce code existe déjà')]

    name        = fields.Char(string='Numéro de presse')
    designation = fields.Char(string='Désignation')
    classe = fields.Selection([
        ('1','1'),
        ('2','2'),
        ('3','3'),
        ('4','4'),
        ('5','5'),
        ('6','6'),
    ], string='Classe')
    emplacement        = fields.Many2one('is.emplacement.outillage', string='Emplacement ')
    classe_commerciale = fields.Many2one('is.presse.classe'        , string='Classe commerciale')
    puissance          = fields.Many2one('is.presse.puissance'     , string='Puissance')
    puissance_reelle   = fields.Char(string='Puissance réelle (T)')
    type_de_presse     = fields.Char(string='Type de presse')
    constructeur       = fields.Many2one('is.outillage.constructeur', string='Constructeur')
    num_construceur    = fields.Char(string='N° constructeur')
    type_commande      = fields.Char(string='Type de commande')
    annee              = fields.Char(string='Année')
    energie = fields.Selection([
        ('electrique' , 'Electrique'),
        ('hydraulique', 'Hydraulique'),
        ('hybride'    , 'Hybride'),
    ], string='Energie')
    volume_tremie       = fields.Char(string='Volume trémie')
    volume_alimentateur = fields.Char(string='Volume alimentateur')
    dimension_col_h     = fields.Char(string='Dimension entre col H')
    dimension_col_v     = fields.Char(string='Dimension entre col V')
    diametre_colonne    = fields.Char(string='Ø colonne')
    epaisseur_moule     = fields.Char(string='Épaisseur moule Mini presse')
    faux_plateau = fields.Selection([
        ('oui','Oui'),
        ('non','Non'),
    ], string='Faux plateau')
    epaisseur_faux_plateau   = fields.Char(string='Épaisseur faux plateau')
    epaisseur_moule_mini     = fields.Char(string='Épaisseur moule mini réel')
    epaisseur_moule_maxi     = fields.Char(string='Épaisseur moule Maxi')
    dimension_plateau_h      = fields.Char(string='Dimension demi plateau H')
    dimension_plateau_v      = fields.Char(string='Dimension demi plateau V')
    dimension_hors_tout_haut = fields.Char(string='Dimension hors tout Haut')
    dimension_hors_tout_bas  = fields.Char(string='Dimension hors tout Bas')
    coefficient_vis          = fields.Char(string='Coefficient de vis')
    diametre_vis             = fields.Char(string='Ø Vis')
    type_clapet = fields.Selection([
        ('clapet_bille','clapet à bille'),
        ('clapet_2_branches','clapet à bague 2 branches'),
        ('clapet_3_branches','clapet à bague 3 branches'),
        ('clapet_4_branches','clapet à bague 4 branches'),
    ], string='Type de clapet')
    volume_injectable        = fields.Char(string='Volume injectable (cm3)')
    presse_matiere           = fields.Char(string='Pression matière (bar)')
    course_ejection          = fields.Char(string='Course éjection')
    course_ouverture         = fields.Char(string='Course ouverture')
    diametre_centrage_moule  = fields.Char(string='Ø centrage moule')
    diametre_centrage_presse = fields.Char(string='Ø centrage presse')
    hauteur_porte_sol        = fields.Char(string='Hauteur porte / sol')
    bridage_rapide           = fields.Char(string='Bridage rapide entre axe')
    diametre_bridage         = fields.Char(string='Ø')
    pas_bridage              = fields.Char(string='Pas')
    type_huile_hydraulique = fields.Selection([
        ('RSL46','RSL46'),
        ('RSL68','RSL68'),
    ], string='Type huile hydraulique')
    volume_reservoir     = fields.Char(string='Volume réservoir')
    longueur             = fields.Integer(string='Longueur (mm)')
    largeur              = fields.Integer(string='Largeur (mm)')
    hauteur              = fields.Integer(string='Hauteur (mm)')
    puissance_electrique = fields.Char(string='Puissance électrique moteur')
    type_huile_graissage = fields.Selection([
        ('sans','sans'),
        ('RSL68SG','RSL68SG'),
        ('RSL150SG','RSL150SG'),
        ('RSL220SG','RSL220SG'),
        ('RSX220','RSX220'),
    ], string='Type huile graissage centralisé')
    puissance_electrique_chauffe = fields.Char(string='Puissance électrique chauffe')
    nombre_noyau                 = fields.Char(string='Nbre Noyau Total')
    compensation_cosinus = fields.Selection([
        ('oui','Oui'),
        ('non','Non'),
    ], string='Compensation cosinus')
    nb_noyau_pf           = fields.Char(string='Nbre Noyau PF')
    nb_noyau_pm           = fields.Char(string='Nbre Noyau PM')
    nombre_circuit_haut   = fields.Char(string='Nbre circuit Eau')
    diametre_passage_buse = fields.Char(string='Ø Passage Buse')
    zone_chauffe          = fields.Char(string='Zones de chauffe')
    poids                 = fields.Char(string='Poids')
    site_id               = fields.Many2one('is.database','Site')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4
