# -*- coding: utf-8 -*-

from openerp import models, fields, api,tools,SUPERUSER_ID
from openerp.tools.translate import _
from openerp.exceptions import Warning
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.osv import osv
import xmlrpclib


class is_instrument_mesure(models.Model):
    _name = 'is.instrument.mesure'
    _order = 'code_pg'
    _rec_name='code_pg'
    _sql_constraints = [('code_pg_uniq','UNIQUE(code_pg)', u'Ce code existe déjà')]

    @api.depends('famille_id', 'frequence')
    def _compute_periodicite(self):
        for obj in self:
            periodicite=False
            if obj.frequence=='intensive':
                periodicite=obj.famille_id.intensive
            if obj.frequence=='moyenne':
                periodicite=obj.famille_id.moyenne
            if obj.frequence=='faible':
                periodicite=obj.famille_id.faible
            obj.periodicite=periodicite

    code_pg            = fields.Char("Code PG", required=True)
    designation        = fields.Char("Désignation",required=True)
    famille_id         = fields.Many2one("is.famille.instrument", "Famille", required=True)
    fabriquant         = fields.Char("Fabricant")
    num_serie          = fields.Char("N° de série")
    date_reception     = fields.Date("Date de réception")
    type               = fields.Char("Type")
    etendue            = fields.Char("Etendue")
    resolution         = fields.Char("Résolution")
    type_boolean       = fields.Boolean('Is Type?', default=False)
    etendue_boolean    = fields.Boolean('Is Etendue?', default=False)
    resolution_boolean = fields.Boolean('Is Résolution?', default=False)
    site_id            = fields.Many2one("is.database", "Site", required=True)
    lieu_stockage      = fields.Char("Lieu de stockage")
    service_affecte    = fields.Char("Personne/Service auquel est affecté l'instrument")
    frequence = fields.Selection([
        ('intensive', 'utilisation quotidienne'), 
        ('moyenne', 'utilisation plusieurs jours par semaine'),
        ('faible', 'utilisation 1 fois par semaine ou moins')
    ], "Fréquence", required=True)
    periodicite            = fields.Char("Périodicité", store=True, compute='_compute_periodicite')
    date_prochain_controle = fields.Date("Date prochain contrôle", compute='_compute_date_prochain_controle', readonly=True, store=True)
    controle_ids           = fields.One2many('is.historique.controle', 'instrument_id', string='Historique des contrôles')
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
    active                 = fields.Boolean('Active', default=True)
    

    @api.multi
    @api.depends('controle_ids','periodicite')
    def _compute_date_prochain_controle(self):
        for rec in self:
            if rec.controle_ids:
                for row in rec.controle_ids:
                    if row.operation_controle_id.code!='arret':
                        date_controle=row.date_controle
                        if date_controle:
                            date_controle = datetime.strptime(date_controle, "%Y-%m-%d")
                            if rec.periodicite:
                                periodicite = int(rec.periodicite)
                            else:periodicite = 0
                            date_prochain_controle = date_controle + relativedelta(months=periodicite)
                            rec.date_prochain_controle = date_prochain_controle.strftime('%Y-%m-%d')
                    else:
                        rec.date_prochain_controle = False
                    break

                
    @api.onchange('famille_id')
    def onchange_famille_id(self):
        self.type_boolean = self.famille_id.afficher_type
        self.etendue_boolean = self.famille_id.afficher_type
        self.resolution_boolean = self.famille_id.afficher_type
        self.classe_boolean = self.famille_id.afficher_classe
        

    @api.multi
    def write(self, vals):
        try:
            res=super(is_instrument_mesure, self).write(vals)
            for obj in self:
                obj.copy_other_database_instrument_mesure()
            return res
        except Exception as e:
            raise osv.except_osv(_('Instrument!'),
                             _('(%s).') % str(e).decode('utf-8'))


    @api.model
    def create(self, vals):
        try:
            obj=super(is_instrument_mesure, self).create(vals)
            obj.copy_other_database_instrument_mesure()
            return obj
        except Exception as e:
            raise osv.except_osv(_('Instrument!'),
                             _('(%s).') % str(e).decode('utf-8'))
            
    @api.multi
    def copy_other_database_instrument_mesure(self):
        cr , uid, context = self.env.args
        context = dict(context)
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for mesure in self:
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
                instrument_mesure_vals = self.get_instrument_mesure_vals(mesure, DB, USERID, USERPASS, sock)
                dest_instrument_mesure_ids = sock.execute(DB, USERID, USERPASS, 'is.instrument.mesure', 'search', [('is_database_origine_id', '=', mesure.id),
                                                                                                '|',('active','=',True),('active','=',False)], {})
                if dest_instrument_mesure_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.instrument.mesure', 'write', dest_instrument_mesure_ids, instrument_mesure_vals, {})
                    instrument_mesure_created_id = dest_instrument_mesure_ids[0]
                else:
                    instrument_mesure_created_id = sock.execute(DB, USERID, USERPASS, 'is.instrument.mesure', 'create', instrument_mesure_vals, {})
        return True

    @api.model
    def get_instrument_mesure_vals(self, mesure, DB, USERID, USERPASS, sock):
        instrument_mesure_vals ={
            'code_pg' : tools.ustr(mesure.code_pg or ''),
            'designation':tools.ustr(mesure.designation or ''),
            'famille_id':self._get_famille_id(mesure, DB, USERID, USERPASS, sock),
            'fabriquant':tools.ustr(mesure.fabriquant or ''),
            'num_serie':tools.ustr(mesure.num_serie or ''),
            'date_reception':mesure.date_reception,
            'type':tools.ustr(mesure.type or ''),
            'etendue': tools.ustr(mesure.etendue or '') ,
            'resolution': tools.ustr(mesure.resolution or ''),
            'type_boolean': mesure.type_boolean ,
            'etendue_boolean': mesure.etendue_boolean ,
            'resolution_boolean':mesure.resolution_boolean,
            'lieu_stockage': tools.ustr(mesure.lieu_stockage or '') ,
            'service_affecte': tools.ustr(mesure.service_affecte or '') ,
            'frequence':mesure.frequence,
            'periodicite':tools.ustr(mesure.periodicite or ''),
            'site_id':self._get_site_id(mesure, DB, USERID, USERPASS, sock),
            'active':mesure.site_id and mesure.site_id.database == DB and True or False,
            'is_database_origine_id':mesure.id,
        }
        return instrument_mesure_vals
    


    @api.model
    def _get_site_id(self, mesure, DB, USERID, USERPASS, sock):
        if mesure.site_id:
            ids = sock.execute(DB, USERID, USERPASS, 'is.database', 'search', [('is_database_origine_id', '=', mesure.site_id.id)], {})
            if ids:
                return ids[0]
        return False


    @api.model
    def _get_famille_id(self, mesure, DB, USERID, USERPASS, sock):
        if mesure.famille_id:
            famille_ids = sock.execute(DB, USERID, USERPASS, 'is.famille.instrument', 'search', [('is_database_origine_id', '=', mesure.famille_id.id)], {})
            if not famille_ids:
                mesure.famille_id.copy_other_database_famille_instrument()
                famille_ids = sock.execute(DB, USERID, USERPASS, 'is.famille.instrument', 'search', [('is_database_origine_id', '=', mesure.famille_id.id)], {})
            if famille_ids:
                return famille_ids[0]
        return False
    
    @api.model
    def _get_fabriquant_id(self, mesure, DB, USERID, USERPASS, sock):
        if mesure.fabriquant_id:
            fabriquant_ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', mesure.fabriquant_id.id)], {})
            if fabriquant_ids:
                return fabriquant_ids[0]
        return False
    
    @api.model
    def _get_fournisseur_id(self, mesure, DB, USERID, USERPASS, sock):
        if mesure.fournisseur_id:
            fournisseur_ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', mesure.fournisseur_id.id)], {})
            if fournisseur_ids:
                return fournisseur_ids[0]
        return False
    
#    @api.model
#    def _get_controle_ids(self, mesure, DB, USERID, USERPASS, sock):
#        list_controle_ids =[]
#        for is_controle in mesure.controle_ids:
#            is_controle_ids = sock.execute(DB, USERID, USERPASS, 'is.historique.controle', 'search', [('is_database_origine_id', '=', is_controle.id)], {})
#            if is_controle_ids:
#                list_controle_ids.append(is_controle_ids[0])
#        
#        return [(6, 0, list_controle_ids)]




        
class is_famille_instrument(models.Model):
    _name = 'is.famille.instrument'
    
    name = fields.Char("Nom de la famille", required=True)
    intensive = fields.Char("INTENSIVE (fréquence f >= 1 fois / jour) en mois")
    moyenne = fields.Char("MOYENNE ( 1fois / 5 jours < f < 1fois / jour ) en mois")
    faible = fields.Char("FAIBLE (f <=1fois / 5 jours) en mois")
    tolerance = fields.Char("Tolérance")
    afficher_classe = fields.Boolean("Afficher le champ Classe", default=False)
    afficher_type = fields.Boolean("Afficher les champs Type, Etendue et Résolution", default=False)
    
    
