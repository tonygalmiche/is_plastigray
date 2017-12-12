# -*- coding: utf-8 -*-
from openerp import models,fields,api,tools,SUPERUSER_ID
from openerp.tools.translate import _
import time
from datetime import datetime
from openerp.osv import osv
import xmlrpclib


class is_type_equipement(models.Model):
    _name='is.type.equipement'
    _order='name'

    name = fields.Char("Name", required=True)


class is_moyen_fabrication(models.Model):
    _name='is.moyen.fabrication'
    _order='name'
    _sql_constraints = [('name_uniq','UNIQUE(name)', u'Ce code existe déjà')]

    name                   = fields.Char("Code", required=True)
    type_equipement        = fields.Many2one('is.type.equipement', string='Type équipement', required=True)
    type_equipement_name   = fields.Char('Type équipement name' , related='type_equipement.name', readonly=True)
    lieu_changement        = fields.Selection([('presse', 'sur presse'), ('mecanique', 'en mécanique')], "Lieu changement")
    designation            = fields.Char("Désignation", required=False)
    mold_ids               = fields.Many2many('is.mold'    ,'is_moyen_fabrication_id'         , 'is_mold_id_fabric'    , string='Moule')
    dossierf_ids           = fields.Many2many('is.dossierf','is_moyen_fabrication_dossierf_id', 'is_dossierf_id_fabric', string='Dossier F')
    base_capacitaire       = fields.Char("Base capacitaire")
    site_id                = fields.Many2one('is.database', string='Site')
    emplacement            = fields.Char("Emplacement")
    fournisseur_id         = fields.Many2one('res.partner', string='Fournisseur', domain=[('supplier','=',True),('is_company','=',True)])
    ref_fournisseur        = fields.Char("Réf fournisseur")
    date_creation          = fields.Date('Date de création')
    date_fin               = fields.Date('Date de fin')
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
    active                 = fields.Boolean('Active', default=True)
    

    @api.multi
    def write(self, vals):
        try:
            res=super(is_moyen_fabrication, self).write(vals)
            for obj in self:
                obj.copy_other_database_moyen_fabrication()
            return res
        except Exception as e:
            raise osv.except_osv(_('Fabrication!'),
                             _('(%s).') % str(e).decode('utf-8'))


    @api.model
    def create(self, vals):
        try:
            obj=super(is_moyen_fabrication, self).create(vals)
            obj.copy_other_database_moyen_fabrication()
            return obj
        except Exception as e:
            raise osv.except_osv(_('Fabrication!'),
                             _('(%s).') % str(e).decode('utf-8'))
            
    @api.multi
    def copy_other_database_moyen_fabrication(self):
        cr , uid, context = self.env.args
        context = dict(context)
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for fabrication in self:
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
                moyen_fabrication_vals = self.get_moyen_fabrication_vals(fabrication, DB, USERID, USERPASS, sock)
                dest_moyen_fabrication_ids = sock.execute(DB, USERID, USERPASS, 'is.moyen.fabrication', 'search', [('is_database_origine_id', '=', fabrication.id),
                                                                                                '|',('active','=',True),('active','=',False)], {})
                if dest_moyen_fabrication_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.moyen.fabrication', 'write', dest_moyen_fabrication_ids, moyen_fabrication_vals, {})
                    moyen_fabrication_created_id = dest_moyen_fabrication_ids[0]
                else:
                    moyen_fabrication_created_id = sock.execute(DB, USERID, USERPASS, 'is.moyen.fabrication', 'create', moyen_fabrication_vals, {})
        return True

    @api.model
    def get_moyen_fabrication_vals(self, fabrication, DB, USERID, USERPASS, sock):
        moyen_fabrication_vals ={
            'name'                  : tools.ustr(fabrication.name or ''),
            'type_equipement'       : self._get_type_equipement(fabrication, DB, USERID, USERPASS, sock),
            'lieu_changement'       : tools.ustr(fabrication.lieu_changement or ''),
            'designation'           : tools.ustr(fabrication.designation or ''),
            'mold_ids'              : self._get_mold_ids(fabrication , DB, USERID, USERPASS, sock),
            'dossierf_ids'          : self._get_dossierf_ids(fabrication , DB, USERID, USERPASS, sock),
            'base_capacitaire'      : tools.ustr(fabrication.base_capacitaire or ''),
            'emplacement'           : tools.ustr(fabrication.emplacement or '') ,
            'fournisseur_id'        : self._get_fournisseur_id(fabrication, DB, USERID, USERPASS, sock),
            'ref_fournisseur'       : tools.ustr(fabrication.ref_fournisseur or ''),
            'date_creation'         : fabrication.date_creation,
            'date_fin'              : fabrication.date_fin,
            'site_id'               : self._get_site_id(fabrication, DB, USERID, USERPASS, sock),
            'active'                : fabrication.site_id and fabrication.site_id.database == DB and True or False,
            'is_database_origine_id': fabrication.id,
        }
        return moyen_fabrication_vals


    @api.model
    def _get_site_id(self, fabrication, DB, USERID, USERPASS, sock):
        if fabrication.site_id:
            ids = sock.execute(DB, USERID, USERPASS, 'is.database', 'search', [('is_database_origine_id', '=', fabrication.site_id.id)], {})
            if ids:
                return ids[0]
        return False


    @api.model
    def _get_type_equipement(self, fabrication, DB, USERID, USERPASS, sock):
        if fabrication.type_equipement:
            type_equipement_ids = sock.execute(DB, USERID, USERPASS, 'is.type.equipement', 'search', [('is_database_origine_id', '=', fabrication.type_equipement.id)], {})
            if not type_equipement_ids:
                fabrication.type_equipement.copy_other_database_type_equipement()
                type_equipement_ids = sock.execute(DB, USERID, USERPASS, 'is.type.equipement', 'search', [('is_database_origine_id', '=', fabrication.type_equipement.id)], {})
            if type_equipement_ids:
                return type_equipement_ids[0]
        return False


    
    @api.model
    def _get_mold_ids(self, fabrication , DB, USERID, USERPASS, sock):
        lst_moule_ids = []
        for moule in fabrication.mold_ids:
            is_mold_ids = sock.execute(DB, USERID, USERPASS, 'is.mold', 'search', [('is_database_origine_id', '=', moule.id)], {})
            if is_mold_ids:
                lst_moule_ids.append(is_mold_ids[0])
        return [(6,0,lst_moule_ids)]


    @api.model
    def _get_dossierf_ids(self, fabrication , DB, USERID, USERPASS, sock):
        ids = []
        for dossierf in fabrication.dossierf_ids:
            res = sock.execute(DB, USERID, USERPASS, 'is.dossierf', 'search', [('is_database_origine_id', '=', dossierf.id)], {})
            if res:
                ids.append(res[0])
        return [(6,0,ids)]


    @api.model
    def _get_fournisseur_id(self, fabrication, DB, USERID, USERPASS, sock):
        if fabrication.fournisseur_id:
            fournisseur_ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', fabrication.fournisseur_id.id)], {})
            if fournisseur_ids:
                return fournisseur_ids[0]
        return False
