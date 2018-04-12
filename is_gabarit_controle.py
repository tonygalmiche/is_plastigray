# -*- coding: utf-8 -*-
from openerp import models,fields,api,tools,SUPERUSER_ID
from openerp.tools.translate import _
from openerp.exceptions import Warning
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.osv import osv
import xmlrpclib
from is_outillage import date_prochain_controle


class is_gabarit_controle(models.Model):
    _name='is.gabarit.controle'
    _order='code_pg'
    _rec_name='code_pg'
    _sql_constraints = [('code_pg_uniq','UNIQUE(code_pg)', u'Ce code existe déjà')]
    
    code_pg                = fields.Char("Code PG"    , required=True)
    designation            = fields.Char("Désignation", required=True)
    fabriquant             = fields.Char("Fabricant")
    date_reception         = fields.Date("Date de réception")
    reference_plan         = fields.Char("Référence plan")
    indice_plan            = fields.Char("Indice plan")
    moule_ids              = fields.Many2many('is.mold'    ,'is_gabarit_mold_rel'    ,'gabarit_id','mold_id'    , string="Moules affectés")
    dossierf_ids           = fields.Many2many('is.dossierf','is_gabarit_dossierf_rel','gabarit_id','dossierf_id', string="Dossiers F affectés")
    client_id              = fields.Many2one("res.partner","Client")
    site_id                = fields.Many2one('is.database', string='Site')
    lieu_stockage          = fields.Char("Lieu de stockage")

    #periodicite            = fields.Integer("Périodicité ( en mois )")
    periodicite            = fields.Selection([
                                    ('24','24 mois (standard)'),
                                    ('48','48 mois ( qté annuelle < 10000p)'),
                                ], string="Périodicité ( en mois )")

    type_controle          = fields.Many2one("is.type.controle.gabarit","Type de contrôle")
    date_prochain_controle = fields.Date("Date prochain contrôle", compute='_compute_date_prochain_controle', readonly=True, store=True)
    controle_ids           = fields.One2many('is.historique.controle', 'gabarit_id', string='Historique des contrôles')
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
    active                 = fields.Boolean('Active', default=True)


    @api.multi
    @api.depends('controle_ids','periodicite')
    def _compute_date_prochain_controle(self):
        for rec in self:
            date_prochain_controle(rec)
#            date_prochain_controle=False
#            if rec.controle_ids:
#                for row in rec.controle_ids:
#                    if row.operation_controle_id.code!='arret' and row.operation_controle_id.code!='maintenance':
#                        date_controle=row.date_controle
#                        if date_controle:
#                            date_controle = datetime.strptime(date_controle, "%Y-%m-%d")
#                            periodicite=0
#                            if rec.periodicite:
#                                try:
#                                    periodicite = int(rec.periodicite)
#                                except ValueError:
#                                    continue
#                            date_prochain_controle = date_controle + relativedelta(months=periodicite)
#                            date_prochain_controle = date_prochain_controle.strftime('%Y-%m-%d')
#                            break
#            rec.date_prochain_controle = date_prochain_controle

    
    @api.multi
    def write(self, vals):
        try:
            res=super(is_gabarit_controle, self).write(vals)
            for obj in self:
                obj.copy_other_database_gabarit_controle()
            return res
        except Exception as e:
            raise osv.except_osv(_('Controle!'),
                             _('(%s).') % str(e).decode('utf-8'))


    @api.model
    def create(self, vals):
        try:
            obj=super(is_gabarit_controle, self).create(vals)
            obj.copy_other_database_gabarit_controle()
            return obj
        except Exception as e:
            raise osv.except_osv(_('Controle!'),
                             _('(%s).') % str(e).decode('utf-8'))
            
    @api.multi
    def copy_other_database_gabarit_controle(self):
        cr , uid, context = self.env.args
        context = dict(context)
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for controle in self:
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
                gabarit_controle_vals = self.get_gabarit_controle_vals(controle, DB, USERID, USERPASS, sock)
                dest_gabarit_controle_ids = sock.execute(DB, USERID, USERPASS, 'is.gabarit.controle', 'search', [('is_database_origine_id', '=', controle.id),
                                                                                                '|',('active','=',True),('active','=',False)], {})
                if dest_gabarit_controle_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.gabarit.controle', 'write', dest_gabarit_controle_ids, gabarit_controle_vals, {})
                    gabarit_controle_created_id = dest_gabarit_controle_ids[0]
                else:
                    gabarit_controle_created_id = sock.execute(DB, USERID, USERPASS, 'is.gabarit.controle', 'create', gabarit_controle_vals, {})
        return True

    @api.model
    def get_gabarit_controle_vals(self, controle, DB, USERID, USERPASS, sock):
        is_controle_vals ={
            'code_pg'               : tools.ustr(controle.code_pg or ''),
            'designation'           : tools.ustr(controle.designation or ''),
            'fabriquant'            : tools.ustr(controle.fabriquant or ''),
            'date_reception'        : controle.date_reception ,
            'reference_plan'        : tools.ustr(controle.reference_plan or ''),
            'indice_plan'           : controle.indice_plan,
            'moule_ids'             : self._get_moule_ids(controle , DB, USERID, USERPASS, sock),
            'dossierf_ids'          : self._get_dossierf_ids(controle , DB, USERID, USERPASS, sock),
            'client_id'             : self._get_client_id(controle, DB, USERID, USERPASS, sock),
            'site_id'               : self._get_site_id(controle, DB, USERID, USERPASS, sock),
            'lieu_stockage'         : tools.ustr(controle.lieu_stockage or ''),
            'periodicite'           : controle.periodicite ,
            'type_controle'         : self._get_type_controle(controle, DB, USERID, USERPASS, sock),
            'is_database_origine_id': controle.id,
            'active'                : controle.site_id and controle.site_id.database == DB and True or False,
        }
        return is_controle_vals

    
    @api.model
    def _get_fabriquant_id(self, controle, DB, USERID, USERPASS, sock):
        if controle.fabriquant_id:
            fabriquant_ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', controle.fabriquant_id.id)], {})
            if fabriquant_ids:
                return fabriquant_ids[0]
        return False


    @api.model
    def _get_dossierf_ids(self, controle , DB, USERID, USERPASS, sock):
        ids = []
        for obj in controle.dossierf_ids:
            res = sock.execute(DB, USERID, USERPASS, 'is.dossierf', 'search', [('is_database_origine_id', '=', obj.id)], {})
            if res:
                ids.append(res[0])
        return [(6,0,ids)]
   

    @api.model
    def _get_moule_ids(self, controle , DB, USERID, USERPASS, sock):
        lst_moule_ids = []
        for moule in controle.moule_ids:
            is_moule_ids = sock.execute(DB, USERID, USERPASS, 'is.mold', 'search', [('is_database_origine_id', '=', moule.id)], {})
            if is_moule_ids:
                lst_moule_ids.append(is_moule_ids[0])
        return [(6,0,lst_moule_ids)]


 
    @api.model
    def _get_client_id(self, controle, DB, USERID, USERPASS, sock):
        if controle.client_id:
            client_ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', controle.client_id.id)], {})
            if client_ids:
                return client_ids[0]
        return False


    @api.model
    def _get_site_id(self, controle, DB, USERID, USERPASS, sock):
        if controle.site_id:
            site_ids = sock.execute(DB, USERID, USERPASS, 'is.database', 'search', [('is_database_origine_id', '=', controle.site_id.id)], {})
            if site_ids:
                return site_ids[0]
        return False

    @api.model
    def _get_type_controle(self, controle, DB, USERID, USERPASS, sock):
        if controle.type_controle:
            type_controle_ids = sock.execute(DB, USERID, USERPASS, 'is.type.controle.gabarit', 'search', [('is_database_origine_id', '=', controle.type_controle.id)], {})
            if not type_controle_ids:
                controle.type_controle.copy_other_database_controle_gabarit()
                type_controle_ids = sock.execute(DB, USERID, USERPASS, 'is.type.controle.gabarit', 'search', [('is_database_origine_id', '=', controle.type_controle.id)], {})
            if type_controle_ids:
                return type_controle_ids[0]
        return False

    @api.model
    def _get_fournisseur_id(self, controle, DB, USERID, USERPASS, sock):
        if controle.fournisseur_id:
            fournisseur_ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', controle.fournisseur_id.id)], {})
            if fournisseur_ids:
                return fournisseur_ids[0]
        return False
    
    @api.model
    def _get_controle_ids(self, controle, DB, USERID, USERPASS, sock):
        list_controle_ids =[]
        for is_controle in controle.controle_ids:
            is_controle_ids = sock.execute(DB, USERID, USERPASS, 'is.historique.controle', 'search', [('is_database_origine_id', '=', is_controle.id)], {})
            if is_controle_ids:
                list_controle_ids.append(is_controle_ids[0])
        
        return [(6, 0, list_controle_ids)]
   









        
class is_emplacement_outillage(models.Model):
    _name = "is.emplacement.outillage"
    
    name = fields.Char("Name")
    
    
class is_type_controle_gabarit(models.Model):
    _name = "is.type.controle.gabarit"
    
    name = fields.Char("Name")
    
    
    
