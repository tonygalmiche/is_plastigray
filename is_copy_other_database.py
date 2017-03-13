# -*- coding: utf-8 -*-

from openerp import api, fields, models, _
from openerp.exceptions import ValidationError
import xmlrpclib

class is_database(models.Model):
    _name = 'is.database'

    name        = fields.Char('Nom'            , required=True)
    ip_server   = fields.Char('Adresse IP'     , required=True)
    port_server = fields.Integer('Port'        , required=True)
    database    = fields.Char('Base de données', required=True)
    login       = fields.Char('Login'          , required=True)
    password    = fields.Char('Mot de passe'   , required=True)


    @api.multi
    def get_fields_model(self, model, exclude=[]):
        res = self.env['ir.model.fields'].search([
            ('model_id.model', '=',model),
            ('name','not in', ['create_date','create_uid','display_name','id','__last_update','write_date','write_uid']),
        ])
        champs=[]
        for champ in res:
            if champ.name not in exclude:
                champs.append(champ)
        return champs


class is_mold_project(models.Model):
    _inherit = 'is.mold.project'


    #TODO
    #- Rendre cette fonction plus générique et valables pour tous les modèles
    #- Executer cette fonction automatiquement lors de la création ou modification de l'objet
    #- Cela devra également fonctionner lors de la duplication d'un objet
    #- Ajouter un champ 'Société' pour indiquer les bases de données dans lesquelles cet objet sera copié
    #- Ajouter un champ 'active' pour désactier l'objet dans une société ou il n'apparait plus
    #- Si l'objet est renomé, il faudrait également le renomer dans les autres sociétés pour ne pas créer de doublons => Complexe !!!!
    #--> Pour cela, il faudra peut-être ajouter un champ pour indiquer la source (id et database de l'objet) pour pouvoir le retrouver


    @api.multi
    def copy_other_database(self):
        cr , uid, context = self.env.args
        champs=self.env['is.database'].get_fields_model('is.mold.project', exclude=['mold_ids','designation'])
        database_obj   = self.env['is.database']
        database_lines = database_obj.search([])
        for database in database_lines:
            DB           = database.database
            USERID       = uid
            DBLOGIN      = database.login
            USERPASS     = database.password
            DB_SERVER    = database.ip_server
            DB_PORT      = database.port_server
            sock         = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/object' % (DB_SERVER, DB_PORT))
            for obj in self:
                vals={}
                for champ in champs:
                    val=getattr(obj, champ.name) 
                    if champ.ttype=='many2one':
                        val=val.id
                    vals[champ.name]=val
                dest_ids = sock.execute(DB, USERID, USERPASS, 'is.mold.project', 'search', [('name', '=', obj.name)], {})
                if dest_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.mold.project', 'write', dest_ids, vals, {})
                    created_id = dest_ids[0]
                else:
                    created_id = sock.execute(DB, USERID, USERPASS, 'is.mold.project', 'create', vals, {})






class is_copy_partner(models.Model):
    _name = 'is.copy.partner'

    @api.model
    def get_state_id(self, state , DB, USERID, USERPASS, sock):
        state_ids = sock.execute(DB, USERID, USERPASS, 'res.country.state', 'search', [('name', '=', state.name)], {})
        if state_ids:
            return state_ids[0]
        else:
            state_vals = {'name':state.name, 'code':state.code, 'country_id':state.country_id and state.country_id.id or False}
            new_state_id = sock.execute(DB, USERID, USERPASS, 'res.country.state', 'create', state_vals, {})
            return new_state_id

    @api.model
    def get_title(self, title , DB, USERID, USERPASS, sock):
        title_ids = sock.execute(DB, USERID, USERPASS, 'res.partner.title', 'search', [('name', '=', title.name)], {})
        if title_ids:
            return title_ids[0]
        else:
            title_vals = {'name':title.name, 'shortcut':title.shortcut}
            new_title_id = sock.execute(DB, USERID, USERPASS, 'res.partner.title', 'create', title_vals, {})
            return new_title_id

    @api.model
    def create_check_categ(self, category, DB, USERID, USERPASS, sock):
        category_ids = sock.execute(DB, USERID, USERPASS, 'res.partner.category', 'search', [('name', '=', category.name)], {})
        if category_ids:
            return category_ids[0]
        else:
            category_vals = {'name':category.name, 'parent_id':category.parent_id and self.create_check_categ(category.parent_id, DB, USERID, USERPASS, sock) or False}
            categoty_id = sock.execute(DB, USERID, USERPASS, 'res.partner.category', 'create', category_vals, {})
            return categoty_id

    @api.model
    def _get_category_id(self, category_line_ids, DB, USERID, USERPASS, sock):
        categ_lst = []
        for category in category_line_ids:
            n_categ_id = self.create_check_categ(category, DB, USERID, USERPASS, sock)
            categ_lst.append(n_categ_id)
        return [(6, 0, categ_lst)]

    @api.model
    def _get_perent_partner(self, partner, DB, USERID, USERPASS, sock):
        partner_obj = self.pool.get('res.partner')
        dest_partner_ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('name', '=', partner.name)], {})
        if dest_partner_ids:
            return dest_partner_ids[0]
        else:
            vals = self.get_partner_vals(partner, DB, USERID, USERPASS, sock)
            partner_created_id = sock.execute(DB, USERID, USERPASS, 'res.partner', 'create', vals, {})
            return partner_created_id

    def _get_child_ids(self, child_ids, DB, USERID, USERPASS, sock):
        new_child_ids = []
        for child in child_ids:
            dest_child_ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('name', '=', child.name)], {})
            if dest_child_ids:
                new_child_ids.append(dest_child_ids[0])
            else:
                child_vals = self.get_partner_vals(child, DB, USERID, USERPASS, sock)
                child_created_id = sock.execute(DB, USERID, USERPASS, 'res.partner', 'create', child_vals, {})
                new_child_ids.append(child_created_id)
        return [(6, 0, new_child_ids)]

    @api.model
    def get_partner_vals(self, partner, DB, USERID, USERPASS, sock):
        partner_vals = {
            'name': partner.name,
            'category_id': partner.category_id and self._get_category_id(partner.category_id, DB, USERID, USERPASS, sock)or [],
            'is_company':partner.is_company,
            'street':partner.street,
            'street2':partner.street2,
            'city':partner.city,
            'state_id':partner.state_id and self.get_state_id(partner.state_id, DB, USERID, USERPASS, sock) or False,
            'zip':partner.zip,
            'country_id':partner.country_id.id or False,
            'website':partner.website,
            'function':partner.function,
            'phone':partner.phone,
            'mobile':partner.mobile,
            'fax':partner.fax,
            'email':partner.email,
            'title': partner.title and self.get_title(partner.title , DB, USERID, USERPASS, sock) or False,
            'customer':partner.customer,
            'supplier':partner.supplier,
        }
        if partner.is_company:
            partner_vals.update({'child_ids':partner.child_ids and self._get_child_ids(partner.child_ids, DB, USERID, USERPASS, sock) or [] })
        return partner_vals

    @api.multi
    def call_rpc_to_copy_partner(self):
        cr , uid, context = self.env.args
        context = dict(context)
        if context.get('active_model', '') != 'res.partner':
            return True
        partner_obj = self.env['res.partner']
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        partner_id = context.get('active_id', False)
        for database in database_lines:
            DB = database.database
            USERID = uid
            DBLOGIN = database.login
            USERPASS = database.password
            DB_SERVER = database.ip_server
            DB_PORT = database.port_server
            sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/object' % (DB_SERVER, DB_PORT))
            partner = partner_obj.browse(partner_id)
            partner_vals = self.get_partner_vals(partner, DB, USERID, USERPASS, sock)
            dest_partner_ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('name', '=', partner.name)], {})
            if dest_partner_ids:
                sock.execute(DB, USERID, USERPASS, 'res.partner', 'write', dest_partner_ids, partner_vals, {})
                partner_created_id = dest_partner_ids[0]
            else:
                partner_created_id = sock.execute(DB, USERID, USERPASS, 'res.partner', 'create', partner_vals, {})
        return True

