# -*- coding: utf-8 -*-

from openerp import models,fields,api,tools,SUPERUSER_ID
from openerp.tools.translate import _
from openerp.osv import osv
import xmlrpclib


class is_moyen_fabrication_autre(models.Model):
    _name='is.moyen.fabrication.autre'
    _sql_constraints = [('name_uniq','UNIQUE(name)', u'Ce code existe déjà')]

    name                   = fields.Char(string='Code', required=True)
    type_equipement        = fields.Many2one('is.type.equipement', string='Type équipement', required=True)
    designation            = fields.Char(string='Désignation', required=False)
    mold_id                = fields.Many2one('is.mold'    , string='Moule')
    dossierf_id            = fields.Many2one('is.dossierf', string='Dossier F')
    site_id                = fields.Many2one('is.database', string='Site')
    emplacement            = fields.Char(string='Emplacement')
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
    active                 = fields.Boolean('Active', default=True)
    

    @api.multi
    def write(self, vals):
        try:
            res=super(is_moyen_fabrication_autre, self).write(vals)
            for obj in self:
                obj.copy_other_database_fabrication_autre()
            return res
        except Exception as e:
            raise osv.except_osv(_('Autre!'),
                             _('(%s).') % str(e).decode('utf-8'))


    @api.model
    def create(self, vals):
        try:
            obj=super(is_moyen_fabrication_autre, self).create(vals)
            obj.copy_other_database_fabrication_autre()
            return obj
        except Exception as e:
            raise osv.except_osv(_('Autre!'),
                             _('(%s).') % str(e).decode('utf-8'))
            
    @api.multi
    def copy_other_database_fabrication_autre(self):
        cr , uid, context = self.env.args
        context = dict(context)
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for autre in self:
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
                fabrication_autre_vals = self.get_fabrication_autre_vals(autre, DB, USERID, USERPASS, sock)
                dest_fabrication_autre_ids = sock.execute(DB, USERID, USERPASS, 'is.moyen.fabrication.autre', 'search', [('is_database_origine_id', '=', autre.id),
                                                                                                '|',('active','=',True),('active','=',False)], {})
                if dest_fabrication_autre_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.moyen.fabrication.autre', 'write', dest_fabrication_autre_ids, fabrication_autre_vals, {})
                    fabrication_autre_created_id = dest_fabrication_autre_ids[0]
                else:
                    fabrication_autre_created_id = sock.execute(DB, USERID, USERPASS, 'is.moyen.fabrication.autre', 'create', fabrication_autre_vals, {})
        return True

    @api.model
    def get_fabrication_autre_vals(self, autre, DB, USERID, USERPASS, sock):
        fabrication_autre_vals ={
            'name' : tools.ustr(autre.name or ''),
            'type_equipement'       : self._get_type_equipement(autre, DB, USERID, USERPASS, sock),
            'designation'           : tools.ustr(autre.designation or ''),
            'mold_id'               : self._get_mold_id(autre , DB, USERID, USERPASS, sock),
            'dossierf_id'           : self._get_dossierf_id(autre , DB, USERID, USERPASS, sock),
            'emplacement'           : tools.ustr(autre.emplacement or ''),
            'site_id'               : self._get_site_id(autre, DB, USERID, USERPASS, sock),
            'active'                : autre.site_id and autre.site_id.database == DB and True or False,
            'is_database_origine_id': autre.id,
        }
        return fabrication_autre_vals
    

    @api.model
    def _get_site_id(self, autre, DB, USERID, USERPASS, sock):
        if autre.site_id:
            ids = sock.execute(DB, USERID, USERPASS, 'is.database', 'search', [('is_database_origine_id', '=', autre.site_id.id)], {})
            if ids:
                return ids[0]
        return False


    @api.model
    def _get_type_equipement(self, autre, DB, USERID, USERPASS, sock):
        if autre.type_equipement:
            type_equipement_ids = sock.execute(DB, USERID, USERPASS, 'is.type.equipement', 'search', [('is_database_origine_id', '=', autre.type_equipement.id)], {})
            if not type_equipement_ids:
                autre.type_equipement.copy_other_database_type_equipement()
                type_equipement_ids = sock.execute(DB, USERID, USERPASS, 'is.type.equipement', 'search', [('is_database_origine_id', '=', autre.type_equipement.id)], {})
            if type_equipement_ids:
                return type_equipement_ids[0]
        return False

    @api.model
    def _get_mold_id(self, autre, DB, USERID, USERPASS, sock):
        if autre.mold_id:
            is_mold_ids = sock.execute(DB, USERID, USERPASS, 'is.mold', 'search', [('is_database_origine_id', '=', autre.mold_id.id)], {})
            if not is_mold_ids:
                autre.mold_id.copy_other_database_mold()
                is_mold_ids = sock.execute(DB, USERID, USERPASS, 'is.mold', 'search', [('is_database_origine_id', '=', autre.mold_id.id)], {})
            if is_mold_ids:
                return is_mold_ids[0]
        return False


    @api.model
    def _get_dossierf_id(self, autre, DB, USERID, USERPASS, sock):
        if autre.dossierf_id:
            ids = sock.execute(DB, USERID, USERPASS, 'is.dossierf', 'search', [('is_database_origine_id', '=', autre.dossierf_id.id)], {})
            if ids:
                return ids[0]
        return False
    



    
