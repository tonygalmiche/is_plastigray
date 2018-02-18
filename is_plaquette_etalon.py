# -*- coding: utf-8 -*-

from openerp import models,fields,api,tools,SUPERUSER_ID
from openerp.tools.translate import _
from openerp.exceptions import Warning
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.osv import osv
import xmlrpclib


class is_plaquette_etalon(models.Model):
    _name='is.plaquette.etalon'
    _order='code_pg'
    _rec_name='code_pg'
    _sql_constraints = [('code_pg_uniq','UNIQUE(code_pg)', u'Ce code existe déjà')]

    code_pg                = fields.Char("Code PG", required=True)
    designation            = fields.Char("Désignation", required=True)
    fabriquant             = fields.Char("Fabricant")
    date_reception         = fields.Date("Date de réception")
    site_id                = fields.Many2one("is.database", "Site")
    lieu_stockage          = fields.Char("Lieu de stockage")
    periodicite            = fields.Integer("Périodicité (en mois)")
    type_controle          = fields.Selection([('colorimetre','colorimètre'),('visuel','visuel')],string="Type de contrôle")
    date_prochain_controle = fields.Date("Date prochain contrôle", compute='_compute_date_prochain_controle', readonly=True, store=True)
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
    active                 = fields.Boolean('Active', default=True)
    controle_ids           = fields.One2many('is.historique.controle', 'plaquette_id', string='Historique des contrôles')


    @api.multi
    @api.depends('controle_ids','periodicite')
    def _compute_date_prochain_controle(self):
        for rec in self:
            date_prochain_controle=False
            if rec.controle_ids:
                for row in rec.controle_ids:
                    if row.operation_controle_id.code!='arret' and row.operation_controle_id.code!='maintenance':
                        date_controle=row.date_controle
                        if date_controle:
                            date_controle = datetime.strptime(date_controle, "%Y-%m-%d")
                            periodicite=0
                            if rec.periodicite:
                                try:
                                    periodicite = int(rec.periodicite)
                                except ValueError:
                                    continue
                            date_prochain_controle = date_controle + relativedelta(months=periodicite)
                            date_prochain_controle = date_prochain_controle.strftime('%Y-%m-%d')
                            break
            rec.date_prochain_controle = date_prochain_controle


    @api.multi
    def write(self, vals):
        try:
            res=super(is_plaquette_etalon, self).write(vals)
            for obj in self:
                obj.copy_other_database_plaquette_etalon()
            return res
        except Exception as e:
            raise osv.except_osv(_('Plaquette!'),
                             _('(%s).') % str(e).decode('utf-8'))


    @api.model
    def create(self, vals):
        try:
            obj=super(is_plaquette_etalon, self).create(vals)
            obj.copy_other_database_plaquette_etalon()
            return obj
        except Exception as e:
            raise osv.except_osv(_('Plaquette!'),
                             _('(%s).') % str(e).decode('utf-8'))
            
    @api.multi
    def copy_other_database_plaquette_etalon(self):
        cr , uid, context = self.env.args
        context = dict(context)
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for etalon in self:
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
                plaquette_etalon_vals = self.get_plaquette_etalon_vals(etalon, DB, USERID, USERPASS, sock)
                dest_plaquette_etalon_ids = sock.execute(DB, USERID, USERPASS, 'is.plaquette.etalon', 'search', [('is_database_origine_id', '=', etalon.id),
                                                                                                '|',('active','=',True),('active','=',False)], {})
                if dest_plaquette_etalon_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.plaquette.etalon', 'write', dest_plaquette_etalon_ids, plaquette_etalon_vals, {})
                    plaquette_etalon_created_id = dest_plaquette_etalon_ids[0]
                else:
                    plaquette_etalon_created_id = sock.execute(DB, USERID, USERPASS, 'is.plaquette.etalon', 'create', plaquette_etalon_vals, {})
        return True

    @api.model
    def get_plaquette_etalon_vals(self, etalon, DB, USERID, USERPASS, sock):
        plaquette_etalon_vals ={
            'code_pg'               : tools.ustr(etalon.code_pg or ''),
            'designation'           : tools.ustr(etalon.designation or ''),
            'fabriquant'            : tools.ustr(etalon.fabriquant or ''),
            'date_reception'        : etalon.date_reception,
            'lieu_stockage'         : tools.ustr(etalon.lieu_stockage or ''),
            'periodicite'           : etalon.periodicite ,
            'type_controle'         : etalon.type_controle ,
            'site_id'               : self._get_site_id(etalon, DB, USERID, USERPASS, sock),
            'active'                : etalon.site_id and etalon.site_id.database == DB and True or False,
            'is_database_origine_id': etalon.id,
        }
        return plaquette_etalon_vals


    @api.model
    def _get_site_id(self, etalon, DB, USERID, USERPASS, sock):
        if etalon.site_id:
            ids = sock.execute(DB, USERID, USERPASS, 'is.database', 'search', [('is_database_origine_id', '=', etalon.site_id.id)], {})
            if ids:
                return ids[0]
        return False


    @api.model
    def _get_fabriquant_id(self, etalon, DB, USERID, USERPASS, sock):
        if etalon.fabriquant_id:
            fabriquant_ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', etalon.fabriquant_id.id)], {})
            if fabriquant_ids:
                return fabriquant_ids[0]
        return False
    
    @api.model
    def _get_fournisseur_id(self, etalon, DB, USERID, USERPASS, sock):
        if etalon.fournisseur_id:
            fournisseur_ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', etalon.fournisseur_id.id)], {})
            if fournisseur_ids:
                return fournisseur_ids[0]
        return False
    
#    @api.model
#    def _get_controle_ids(self, etalon, DB, USERID, USERPASS, sock):
#        list_controle_ids =[]
#        for is_controle in etalon.controle_ids:
#            is_controle_ids = sock.execute(DB, USERID, USERPASS, 'is.historique.controle', 'search', [('is_database_origine_id', '=', is_controle.id)], {})
#            if is_controle_ids:
#                list_controle_ids.append(is_controle_ids[0])
#        
#        return [(6, 0, list_controle_ids)]
    





