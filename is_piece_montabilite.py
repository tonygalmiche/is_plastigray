# -*- coding: utf-8 -*-
from openerp import models,fields,api,tools,SUPERUSER_ID
from openerp.tools.translate import _
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.osv import osv
import xmlrpclib
from is_outillage import date_prochain_controle


class is_piece_montabilite(models.Model):
    _name='is.piece.montabilite'
    _rec_name = 'code_pg'
    _sql_constraints = [('code_pg_uniq','UNIQUE(code_pg)', u'Ce code existe déjà')]
    
    @api.depends('moule_ids')
    def compute_client_id(self):
        for rec in self:
            client_id = False
            for moule in rec.moule_ids:
                if moule.client_id:
                    client_id = moule.client_id.id
                    break;
            rec.client_id = client_id
    
    code_pg                = fields.Char("Code PG", required=True)
    designation            = fields.Char("Désignation")
    fabriquant             = fields.Selection([('client','Client'),
                                   ('plastigray','Plastigray'),
                                   ('autre','Autre')
                                   ], string="Fabricant")
    fabricant_client_id    = fields.Many2one('res.partner', string='Fabricant (Client)', domain=[('supplier','=',True),('is_company','=',True)])
    fabriquant_mold_id     = fields.Many2one('is.mold', string='Fabricant (Moule)')
    fabriquant_autre       = fields.Char("Fabricant (Autre)")
    date_reception         = fields.Date("Date de réception")
    moule_ids              = fields.Many2many('is.mold','is_piece_montabilite_id', 'is_mold_id_piece_mont', string='Moules affectés')
    client_id              = fields.Many2one('res.partner', string='Client', compute="compute_client_id", store=True)
    site_id                = fields.Many2one('is.database', string='Site')
    lieu_stockage          = fields.Char("Lieu de stockage")

    #periodicite            = fields.Integer("Périodicité ( en mois )")
    periodicite            = fields.Selection([
                                    ('24','24 mois (standard)'),
                                    ('48','48 mois ( qté annuelle < 10000p)'),
                                ], string="Périodicité ( en mois )")

    type_controle          = fields.Many2one('is.type.controle.gabarit', string='Type de contrôle')
    date_prochain_controle = fields.Date("Date prochain contrôle", compute='_compute_date_prochain_controle', readonly=True, store=True)
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
    active                 = fields.Boolean('Active', default=True)
    controle_ids           = fields.One2many('is.historique.controle', 'piece_id', string='Historique des contrôles')


    @api.multi
    @api.depends('controle_ids','periodicite')
    def _compute_date_prochain_controle(self):
        for rec in self:
            date_prochain_controle(rec)


    @api.multi
    def write(self, vals):
        try:
            res=super(is_piece_montabilite, self).write(vals)
            for obj in self:
                obj.copy_other_database_piece_montabilite()
            return res
        except Exception as e:
            raise osv.except_osv(_('Montabilite!'),
                             _('(%s).') % str(e).decode('utf-8'))


    @api.model
    def create(self, vals):
        try:
            obj=super(is_piece_montabilite, self).create(vals)
            obj.copy_other_database_piece_montabilite()
            return obj
        except Exception as e:
            raise osv.except_osv(_('Montabilite!'),
                             _('(%s).') % str(e).decode('utf-8'))
            
    @api.multi
    def copy_other_database_piece_montabilite(self):
        cr , uid, context = self.env.args
        context = dict(context)
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for piece in self:
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
                piece_montabilite_vals = self.get_piece_montabilite_vals(piece, DB, USERID, USERPASS, sock)
                dest_piece_montabilite_ids = sock.execute(DB, USERID, USERPASS, 'is.piece.montabilite', 'search', [('is_database_origine_id', '=', piece.id),
                                                                                                '|',('active','=',True),('active','=',False)], {})
                if dest_piece_montabilite_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.piece.montabilite', 'write', dest_piece_montabilite_ids, piece_montabilite_vals, {})
                    piece_montabilite_created_id = dest_piece_montabilite_ids[0]
                else:
                    piece_montabilite_created_id = sock.execute(DB, USERID, USERPASS, 'is.piece.montabilite', 'create', piece_montabilite_vals, {})
        return True

    @api.model
    def get_piece_montabilite_vals(self, piece, DB, USERID, USERPASS, sock):
        piece_montabilite_vals ={
            'code_pg':tools.ustr(piece.code_pg or ''),
            'designation'           : tools.ustr(piece.designation or ''),
            'fabriquant'            : tools.ustr(piece.fabriquant or ''),
            'fabricant_client_id'   : self._get_fabricant_client_id(piece, DB, USERID, USERPASS, sock),
            'fabriquant_mold_id'    : self._get_fabriquant_mold_id(piece, DB, USERID, USERPASS, sock),
            'fabriquant_autre'      : tools.ustr(piece.fabriquant_autre or ''),
            'date_reception'        : piece.date_reception,
            'moule_ids'             : self._get_moule_ids(piece, DB, USERID, USERPASS, sock),
            'client_id'             : self._get_client_id(piece, DB, USERID, USERPASS, sock),
            'lieu_stockage'         : tools.ustr(piece.lieu_stockage or ''),
            'periodicite'           : piece.periodicite,
            'type_controle'         : self._get_type_controle(piece, DB, USERID, USERPASS, sock),
            'site_id'               : self._get_site_id(piece, DB, USERID, USERPASS, sock),
            'active'                : piece.site_id and piece.site_id.database == DB and True or False,
            'is_database_origine_id': piece.id,
        }
        return piece_montabilite_vals


    @api.model
    def _get_site_id(self, piece, DB, USERID, USERPASS, sock):
        if piece.site_id:
            ids = sock.execute(DB, USERID, USERPASS, 'is.database', 'search', [('is_database_origine_id', '=', piece.site_id.id)], {})
            if ids:
                return ids[0]
        return False


    @api.model
    def _get_fabricant_client_id(self, piece, DB, USERID, USERPASS, sock):
        if piece.fabricant_client_id:
            fabricant_client_ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', piece.fabricant_client_id.id)], {})
            if fabricant_client_ids:
                return fabricant_client_ids[0]
        return False
    
    
    @api.model
    def _get_fabriquant_mold_id(self, piece, DB, USERID, USERPASS, sock):
        if piece.fabriquant_mold_id:
            fabriquant_mold_ids = sock.execute(DB, USERID, USERPASS, 'is.mold', 'search', [('is_database_origine_id', '=', piece.fabriquant_mold_id.id)], {})
            if not fabriquant_mold_ids:
                piece.fabriquant_mold_id.copy_other_database_mold()
                fabriquant_mold_ids = sock.execute(DB, USERID, USERPASS, 'is.mold', 'search', [('is_database_origine_id', '=', controle.fabriquant_mold_id.id)], {})
            if fabriquant_mold_ids:
                return fabriquant_mold_ids[0]
        return False
    
    @api.model
    def _get_moule_ids(self, piece, DB, USERID, USERPASS, sock):
        lst_moule_ids = []
        for moule in piece.moule_ids:
            is_moule_ids = sock.execute(DB, USERID, USERPASS, 'is.mold', 'search', [('is_database_origine_id', '=', moule.id)], {})
            if is_moule_ids:
                lst_moule_ids.append(is_moule_ids[0])
        return [(6,0,lst_moule_ids)]
    
    @api.model
    def _get_client_id(self, piece, DB, USERID, USERPASS, sock):
        if piece.client_id:
            client_ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', piece.client_id.id)], {})
            if client_ids:
                return client_ids[0]
        return False
    
    @api.model
    def _get_type_controle(self, piece, DB, USERID, USERPASS, sock):
        if piece.type_controle:
            type_controle_ids = sock.execute(DB, USERID, USERPASS, 'is.type.controle.gabarit', 'search', [('is_database_origine_id', '=', piece.type_controle.id)], {})
            if not type_controle_ids:
                piece.type_controle.copy_other_database_controle_gabarit()
                type_controle_ids = sock.execute(DB, USERID, USERPASS, 'is.type.controle.gabarit', 'search', [('is_database_origine_id', '=', piece.type_controle.id)], {})
            if type_controle_ids:
                return type_controle_ids[0]
        return False
    
    @api.model
    def _get_fournisseur_id(self, piece, DB, USERID, USERPASS, sock):
        if piece.fournisseur_id:
            fournisseur_ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', piece.fournisseur_id.id)], {})
            if fournisseur_ids:
                return fournisseur_ids[0]
        return False
    
    def _get_piece_controle_ids(self, piece, DB, USERID, USERPASS, sock):
        list_controle_ids =[]
        for is_controle in piece.piece_controle_ids:
            piece_controle_ids = sock.execute(DB, USERID, USERPASS, 'is.historique.controle', 'search', [('is_database_origine_id', '=', is_controle.id)], {})
            if piece_controle_ids:
                list_controle_ids.append(piece_controle_ids[0])
        
        return [(6, 0, list_controle_ids)]
    



