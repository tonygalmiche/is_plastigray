# -*- coding: utf-8 -*-
from openerp import tools
from openerp import api, fields, models, _
from openerp.exceptions import ValidationError, Warning
import xmlrpclib
from openerp.osv import osv
import unicodedata
from openerp import SUPERUSER_ID
import sys
reload(sys)
sys.setdefaultencoding("utf-8")

import logging
_logger = logging.getLogger(__name__)


#TODO
# Si le client ou le chef de projet n'existe pas, il faut le créer => Et mettre en relation les bons id ce qui n'est pas le cas actuellement

#- Cela devra également fonctionner lors de la duplication d'un objet
#- Ajouter un champ 'Société' pour indiquer les bases de données dans lesquelles cet objet sera copié
#- Ajouter un champ 'active' pour désactier l'objet dans une société ou il n'apparait plus


#test_recursive=0

class is_database(models.Model):
    _name = 'is.database'
    _order='name'

    name                   = fields.Char('Site'           , required=True)
    ip_server              = fields.Char('Adresse IP'     , required=False)
    port_server            = fields.Integer('Port'        , required=False)
    database               = fields.Char('Base de données', required=False)
    login                  = fields.Char('Login'          , required=False)
    password               = fields.Char('Mot de passe'   , required=False)
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)


    @api.multi
    def copy_other_database(self, obj):
        #global test_recursive 
        try:
            cr , uid, context = self.env.args
            class_name=obj.__class__.__name__
            database_lines = self.env['is.database'].search([])
            for database in database_lines:
                if database.database:
                    _logger.info(u'database='+str(database.database))
                    if class_name=='res.partner':
                        if obj.id==obj.is_adr_facturation.id:
                            raise osv.except_osv('Client recursif 2 !','')
                    DB = database.database
                    USERID = SUPERUSER_ID
                    DBLOGIN = database.login
                    USERPASS = database.password
                    DB_SERVER = database.ip_server
                    DB_PORT = database.port_server
                    sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/object' % (DB_SERVER, DB_PORT))
                    vals=False
                    if class_name=='res.partner':
                        vals = self.get_partner_vals(obj, DB, USERID, USERPASS, sock)
    #                     if database.id not in obj.is_database_line_ids.mapped('is_database_origine_id'):
    #                         vals.update({'active':False})
                    if vals:
                        ids = sock.execute(DB, USERID, USERPASS, class_name, 'search', [('is_database_origine_id', '=', obj.id),'|',('active','=',True),('active','=',False)], {})
    #                     if not ids:
    #                         ids = sock.execute(DB, USERID, USERPASS, class_name, 'search', [('name', '=', obj.name)], {})
                        if not ids:
                            if class_name=='res.partner':
                                search=[
                                    ('name'       , '=', obj.name),
                                    ('parent_id'  , '=', obj.parent_id.id or False),
                                    ('is_code'    , '=', obj.is_code),
                                    ('is_adr_code', '=', obj.is_adr_code),
                                    '|',('active','=',True),('active','=',False)
                                ]
                                ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', search, {})
                        if ids:
                            sock.execute(DB, USERID, USERPASS, class_name, 'write', ids, vals, {})
                            created_id = ids[0]
                        else:
                            created_id = sock.execute(DB, USERID, USERPASS, class_name, 'create', vals, {})
        except Exception as e:
            raise osv.except_osv('Client recursif !','')

#            raise osv.except_osv(_('Recursive Client!'),
#                             _('(%s).') % str(e).decode('utf-8'))


        return True

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
    def get_is_secteur_activite(self, obj , DB, USERID, USERPASS, sock):
        ids = sock.execute(DB, USERID, USERPASS, 'is.secteur.activite', 'search', [('is_database_origine_id', '=', obj.id)], {})
        if not ids:
            obj.copy_other_database_secteur_activite()
            ids = sock.execute(DB, USERID, USERPASS, 'is.secteur.activite', 'search', [('is_database_origine_id', '=', obj.id)], {})
        if ids:
            return ids[0]
        return False
            

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

    def _get_child_ids(self, child_ids, DB, USERID, USERPASS, sock):
        new_child_ids = []
        flag = False
        for child in child_ids:
            dest_child_ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', child.id),'|',('active','=',True),('active','=',False)], {})
            if dest_child_ids:
                new_child_ids.append(dest_child_ids[0])
            else:
                child_vals = self.get_partner_vals(child, DB, USERID, USERPASS, sock)
                child_created_id = sock.execute(DB, USERID, USERPASS, 'res.partner', 'create', child_vals, {})
                new_child_ids.append(child_created_id)
        return [(6,0,new_child_ids)]

    @api.model
    def get_partner_is_adr_facturation(self, partner, DB, USERID, USERPASS, sock):
        partner_obj = self.pool.get('res.partner')
        try:
            ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', partner.id),'|',('active','=',True),('active','=',False)], {})
            if not ids:
                self.copy_other_database(partner)
                ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', partner.id),'|',('active','=',True),('active','=',False)], {})
            if ids:
                return ids[0]
            return False
        except Exception as e:
            raise osv.except_osv('Client recursif !','')
#            raise osv.except_osv(_('Client!'),
#                             _('(%s).') % str(e).decode('utf-8'))

    @api.model
    def get_partner_parent_id(self, partner, DB, USERID, USERPASS, sock):

        ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', partner.id),'|',('active','=',True),('active','=',False)], {})
        if not ids:
            parent_id=False
            if partner.id:
                parent_id=self.get_partner_parent_id(partner, DB, USERID, USERPASS, sock)
            search=[
                ('name'       , '=', partner.name),
                ('parent_id'  , '=', parent_id),
                ('is_code'    , '=', partner.is_code),
                ('is_adr_code', '=', partner.is_adr_code),
                '|',('active','=',True),('active','=',False)
            ]
            ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', search, {})
        if ids:
            id=ids[0]
        else:
            vals = self.get_partner_vals(partner, DB, USERID, USERPASS, sock)
            id = sock.execute(DB, USERID, USERPASS, 'res.partner', 'create', vals, {})
        return id


    def get_is_transporteur_id(self, obj, DB, USERID, USERPASS, sock):
        ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', obj.id),'|',('active','=',True),('active','=',False)], {})
        if not ids:
            self.copy_other_database(obj)
            ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', obj.id),'|',('active','=',True),('active','=',False)], {})
        if ids:  
            return ids[0]
        return False
    
    def get_is_type_contact(self, obj , DB, USERID, USERPASS, sock):
        is_type_contact_ids = sock.execute(DB, USERID, USERPASS, 'is.type.contact', 'search', [('is_database_origine_id', '=', obj.id)], {})
        if is_type_contact_ids:
            return is_type_contact_ids[0]
        else:
            vals = {'name':tools.ustr(obj.name), 'is_database_origine_id':obj.id}
            is_type_contact = sock.execute(DB, USERID, USERPASS, 'is.type.contact', 'create', vals, {})
            return is_type_contact
        
    def get_is_incoterm(self, obj, DB, USERID, USERPASS, sock):
        is_incoterm_ids = sock.execute(DB, USERID, USERPASS, 'stock.incoterms', 'search', [('name', '=', tools.ustr(obj.name))], {})
        if is_incoterm_ids:
            return is_incoterm_ids[0]
        else:
            vals = {'name':tools.ustr(obj.name),'code':obj.code, 'active':obj.active}
            is_incoterm = sock.execute(DB, USERID, USERPASS, 'stock.incoterms', 'create', vals, {})
            return is_incoterm


    def get_is_rib_id(self, obj , DB, USERID, USERPASS, sock):
        is_rib_id = sock.execute(DB, USERID, USERPASS, 'res.partner.bank', 'search', [('acc_number', '=', obj.is_rib_id.acc_number)], {})
        if is_rib_id:
            return is_rib_id[0]
        return False

    def get_is_type_reglement(self, obj , DB, USERID, USERPASS, sock):
        _logger.info(u'get_is_type_reglement : code='+str(obj.is_type_reglement.code))
        res = sock.execute(DB, USERID, USERPASS, 'account.journal', 'search', [('code', '=', obj.is_type_reglement.code)], {})
        if res:
            return res[0]
        return False

    def get_user_id(self, obj , DB, USERID, USERPASS, sock):
        user_id = sock.execute(DB, USERID, USERPASS, 'res.users', 'search', [('login', '=', obj.user_id.login)], {})
        if user_id:
            return user_id[0]
        return False


    def get_is_segment_achat(self, obj , DB, USERID, USERPASS, sock):
        is_segment_achat_ids = sock.execute(DB, USERID, USERPASS, 'is.segment.achat', 'search', [('is_database_origine_id', '=', obj.id)], {})
        if is_segment_achat_ids:
            return is_segment_achat_ids[0]
        else:
            vals = {'name':tools.ustr(obj.name),'description':tools.ustr(obj.description), 'is_database_origine_id':obj.id}
            is_segment_achat = sock.execute(DB, USERID, USERPASS, 'is.segment.achat', 'create', vals, {})
            return is_segment_achat
        

    def get_is_famille_achat_ids(self, obj_ids , DB, USERID, USERPASS, sock):
        lst_is_famille_achat_ids = []
        for obj in obj_ids:
            famille_achat_ids = sock.execute(DB, USERID, USERPASS, 'is.famille.achat', 'search', [('is_database_origine_id', '=', obj.id)], {})
            if famille_achat_ids:
                lst_is_famille_achat_ids.append(famille_achat_ids[0])
            else:
                vals = {'is_database_origine_id':obj.id,'name':tools.ustr(obj.name),'description':obj.description, 'segment_id':self.get_is_segment_achat(obj.segment_id , DB, USERID, USERPASS, sock)}
                is_famille_achat = sock.execute(DB, USERID, USERPASS, 'is.famille.achat', 'create', vals, {})
                lst_is_famille_achat_ids.append(is_famille_achat)
        return [(6,0,lst_is_famille_achat_ids)]
        
    def get_is_site_livre_ids(self, obj_ids , DB, USERID, USERPASS, sock):
        lst_site_livre_ids = []
        for obj in obj_ids:
            is_site_livre_ids = sock.execute(DB, USERID, USERPASS, 'is.site', 'search', [('is_database_origine_id', '=', obj.id)], {})
            if is_site_livre_ids:
                lst_site_livre_ids.append(is_site_livre_ids[0])
            else:
                vals = {'name':tools.ustr(obj.name), 'is_database_origine_id':obj.id}
                lst_site_livre_id = sock.execute(DB, USERID, USERPASS, 'is.site', 'create', vals, {})
                lst_site_livre_ids.append(lst_site_livre_id)
        return [(6,0,lst_site_livre_ids)]
    
    def get_is_transmission_cde(self, obj, DB, USERID, USERPASS, sock):
        is_transmission_cde_ids = sock.execute(DB, USERID, USERPASS, 'is.transmission.cde', 'search', [('is_database_origine_id', '=', obj.id)], {})
        if is_transmission_cde_ids:
            return is_transmission_cde_ids[0]
        else:
            vals = {'name':tools.ustr(obj.name), 'is_database_origine_id':obj.id}
            is_transmission_cde = sock.execute(DB, USERID, USERPASS, 'is.transmission.cde', 'create', vals, {})
            return is_transmission_cde
            return False
    
    def get_is_norme(self, obj, DB, USERID, USERPASS, sock):
        is_norme_ids = sock.execute(DB, USERID, USERPASS, 'is.norme.certificats', 'search', [('is_database_origine_id', '=', obj.id)], {})
        if is_norme_ids:
            return is_norme_ids[0]
        else:
            vals = {'name':tools.ustr(obj.name), 'is_database_origine_id':obj.id}
            is_norme = sock.execute(DB, USERID, USERPASS, 'is.norme.certificats', 'create', vals, {})
            return is_norme
            return False
    
    def get_is_certifications(self, obj_ids, DB, USERID, USERPASS, sock):
        lst_is_certifications = []
        for obj in obj_ids:
            is_certifications_ids = sock.execute(DB, USERID, USERPASS, 'is.certifications.qualite', 'search', [('is_database_origine_id', '=', obj.id)], {})
            if is_certifications_ids:
                lst_is_certifications.append(is_certifications_ids[0])
            else:
                vals = {'is_norme':obj.is_norme and self.get_is_norme(obj.is_norme, DB, USERID, USERPASS, sock) or False,
                        'is_date_validation':obj.is_date_validation,
                        'is_database_origine_id':obj.id,
#                         'is_certificat':obj.is_certificat,
#                         'partner_id':obj.partner_id and  self.get_is_transporteur_id(obj.partner_id, DB, USERID, USERPASS, sock) or False
                        }
                is_certifications = sock.execute(DB, USERID, USERPASS, 'is.certifications.qualite', 'create', vals, {})
                lst_is_certifications.append(is_certifications)
        return [(6,0,lst_is_certifications)]
    
    def get_is_database_line_ids(self, partner , DB, USERID, USERPASS, sock):
        lst_is_database_line_ids = []
        obj_ids = partner.is_database_line_ids
#         if not obj_ids:
#             obj_ids = partner.parent_id and partner.parent_id.is_database_line_ids
        for obj in obj_ids:
            is_database_line_ids = sock.execute(DB, USERID, USERPASS, 'is.database', 'search', [('is_database_origine_id', '=', obj.id)], {})
            if is_database_line_ids:
                lst_is_database_line_ids.append(is_database_line_ids[0])
            else:
                vals = {'name':obj.name,
                        'is_database_origine_id':obj.id,
                        }
                is_database_line_id = sock.execute(DB, USERID, USERPASS, 'is.database', 'create', vals, {})
                lst_is_database_line_ids.append(is_database_line_id)
        return [(6,0,lst_is_database_line_ids)]
        
    @api.model
    def get_partner_vals(self, partner, DB, USERID, USERPASS, sock):
        partner_vals = {
            'name': tools.ustr(partner.name),
            #'parent_id'          : partner.parent_id and self.get_partner_parent_id(partner.parent_id, DB, USERID, USERPASS, sock) or False,
            'is_raison_sociale2' : partner.is_raison_sociale2,
            'is_code'            : partner.is_code,
            'is_adr_code'        : partner.is_adr_code,
            'category_id'        : partner.category_id and self._get_category_id(partner.category_id, DB, USERID, USERPASS, sock)or [],
            'is_company'         : partner.is_company,
            'street'             : partner.street,
            'street2'            : partner.street2,
            'is_rue3'            : partner.is_rue3,
            'city'               : partner.city,
            'state_id'           : partner.state_id and self.get_state_id(partner.state_id, DB, USERID, USERPASS, sock) or False,
            'zip'                : partner.zip,
            'country_id'         : partner.country_id.id or False,
            'is_adr_facturation' : partner.is_adr_facturation and self.get_partner_is_adr_facturation(partner.is_adr_facturation, DB, USERID, USERPASS, sock) or False,
            'website'            : partner.website,
            'function'           : partner.function,
            'phone'              : partner.phone,
            'mobile'             : partner.mobile,
            'fax'                : partner.fax,
            'email'              : partner.email,
            'title'              : partner.title and self.get_title(partner.title , DB, USERID, USERPASS, sock) or False,
            'is_secteur_activite': partner.is_secteur_activite and self.get_is_secteur_activite(partner.is_secteur_activite , DB, USERID, USERPASS, sock) or False,
            'customer'           : partner.customer,
            'supplier'           : partner.supplier,
            'is_database_origine_id': partner.id,
            
            
            #'is_transporteur_id' : partner.is_transporteur_id and self.get_is_transporteur_id(partner.is_transporteur_id, DB, USERID, USERPASS, sock) or False,
            #'is_delai_transport':partner.is_delai_transport,
            #'is_certificat_matiere' :  partner.is_certificat_matiere,
            #'is_import_function'    :  partner.is_import_function,
            'is_raison_sociale2'    :  partner.is_raison_sociale2,
            'is_code'               :  partner.is_code,
            'is_adr_code'           :  partner.is_adr_code,
            'is_rue3'               :  partner.is_rue3,
            'is_type_contact'       :  partner.is_type_contact and self.get_is_type_contact(partner.is_type_contact , DB, USERID, USERPASS, sock) or False,
            'is_adr_groupe'         :  partner.is_adr_groupe,
            'is_cofor'              :  partner.is_cofor,
            #'is_incoterm'           :  partner.is_incoterm and self.get_is_incoterm(partner.is_incoterm , DB, USERID, USERPASS, sock) or False,        
            'is_num_siret'          :  partner.is_num_siret,
            'is_code_client'        :  partner.is_code_client,
            'is_segment_achat'      :  partner.is_segment_achat and self.get_is_segment_achat(partner.is_segment_achat , DB, USERID, USERPASS, sock) or False,
            'is_famille_achat_ids'  :  partner.is_famille_achat_ids and self.get_is_famille_achat_ids(partner.is_famille_achat_ids , DB, USERID, USERPASS, sock) or False,
            'is_fournisseur_imp'    :  partner.is_fournisseur_imp,
            'is_site_livre_ids'     :  partner.is_site_livre_ids and self.get_is_site_livre_ids(partner.is_site_livre_ids , DB, USERID, USERPASS, sock) or False,
            'is_groupage'           :  partner.is_groupage,
            'is_tolerance_delai'    :  partner.is_tolerance_delai,
            'is_nb_jours_tolerance' :  partner.is_nb_jours_tolerance,
            'is_tolerance_quantite' :  partner.is_tolerance_quantite,
            'is_transmission_cde'   :  partner.is_transmission_cde and self.get_is_transmission_cde(partner.is_transmission_cde , DB, USERID, USERPASS, sock) or False,
            'is_certifications'     :  partner.is_certifications and self.get_is_certifications(partner.is_certifications , DB, USERID, USERPASS, sock) or False,
            'is_adr_liv_sur_facture' : partner.is_adr_liv_sur_facture,
            'is_num_autorisation_tva': partner.is_num_autorisation_tva,
            'is_caracteristique_bl'  : partner.is_caracteristique_bl,
            'is_mode_envoi_facture'  : partner.is_mode_envoi_facture,
            #'is_type_cde_fournisseur': partner.is_type_cde_fournisseur,
            'is_database_line_ids'   : self.get_is_database_line_ids(partner, DB, USERID, USERPASS, sock) or False,

            'vat'                            : partner.vat,
            'property_account_position'      : partner.property_account_position.id,
            'property_payment_term'          : partner.property_payment_term.id,
            'property_supplier_payment_term' : partner.property_supplier_payment_term.id,
            'is_escompte'                    : partner.is_escompte.id,

            'is_type_reglement'              : partner.is_type_reglement and self.get_is_type_reglement(partner, DB, USERID, USERPASS, sock) or False,

            'is_rib_id'                      : partner.is_rib_id and self.get_is_rib_id(partner, DB, USERID, USERPASS, sock) or False,
            'user_id'                        : partner.user_id and self.get_user_id(partner, DB, USERID, USERPASS, sock) or False,


            'active'                 : True,
        }
        db_ids = self.env['is.database'].search([('database','=',DB)])
        if db_ids:
            is_database_line_ids = partner_vals.get('is_database_line_ids',[]) and partner_vals.get('is_database_line_ids',[])[0][2]
            database_rec = sock.execute(DB, USERID, USERPASS, 'is.database', 'read', is_database_line_ids,['is_database_origine_id','name'], {})
            origin_db_ids = []
            if database_rec:
                for db_rec in database_rec:
                    if db_rec.get('is_database_origine_id',False):
                        origin_db_ids.append(db_rec.get('is_database_origine_id'))
            if db_ids[0].id not in origin_db_ids:
                partner_vals.update({'active':False})
        if partner.is_company:
            partner_vals.update({'child_ids':partner.child_ids and self._get_child_ids(partner.child_ids, DB, USERID, USERPASS, sock) or [] })
        return partner_vals



    @api.multi
    def write(self, vals):
        try:
            res=super(is_database, self).write(vals)
            for obj in self:
                if obj.database:
                    obj.copy_other_database_is_database()
            return res
        except Exception as e:
            raise osv.except_osv(_('database!'),
                             _('(%s).') % str(e).decode('utf-8'))

    @api.model
    def create(self, vals):
        try:
            obj=super(is_database, self).create(vals)
            obj.copy_other_database_is_database()
            return obj
        except Exception as e:
            raise osv.except_osv(_('database!'),
                             _('(%s).') % str(e).decode('utf-8'))

    
    @api.multi
    def copy_other_database_is_database(self):
        cr , uid, context = self.env.args
        context = dict(context)
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for obj in self:
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
                vals = self.get_is_database_vals(obj, DB, USERID, USERPASS, sock)
                ids = sock.execute(DB, USERID, USERPASS, 'is.database', 'search', [('is_database_origine_id', '=', obj.id)], {})
                if not ids:
                    ids = sock.execute(DB, USERID, USERPASS, 'is.database', 'search', [('name', '=', obj.name)], {})
                if ids:
                    sock.execute(DB, USERID, USERPASS, 'is.database', 'write', ids, vals, {})
                    created_id = ids[0]
                else:
                    created_id = sock.execute(DB, USERID, USERPASS, 'is.database', 'create', vals, {})
        return True


    @api.model
    def get_is_database_vals(self, obj, DB, USERID, USERPASS, sock):
        vals ={
            'name'                   : tools.ustr(obj.name),
            'is_database_origine_id' : obj.id,
        }
        return vals


#    @api.multi
#    def write(self, vals):
#        for obj in self:
#            res=super(is_database, self).write(vals)
#            class_name=self.__class__.__name__
#            champs=self.get_fields_model(class_name, include=['name'])
#            self.copy_other_database(obj, champs)
#            return res

#    @api.model
#    def create(self, vals):
#        obj=super(is_database, self).create(vals)
#        class_name=self.__class__.__name__
#        champs=self.get_fields_model(class_name, include=['name'])
#        self.copy_other_database(obj, champs)
#        return obj


class res_partner(models.Model):
    _inherit = 'res.partner'

    is_database_origine_id = fields.Integer("Id d'origine", readonly=True, select=True)
    is_database_line_ids = fields.Many2many('is.database','partner_database_rel','partner_id','database_id', string="Sites")

    @api.multi
    def write(self, vals):
        for obj in self:
            _logger.info(u'write : partner='+str(obj.is_code)+u'/'+str(obj.is_adr_code))
            if 'is_adr_facturation' in vals:
                if vals['is_adr_facturation']==obj.id:
                    vals['is_adr_facturation']=False
            else:
                if obj.is_adr_facturation.id==obj.id:
                    vals['is_adr_facturation']=False
        try:
            for obj in self:
                res=super(res_partner, self).write(vals)
                self.env['is.database'].copy_other_database(obj)
                #global test_recursive
                #test_recursive=0
                return res
        except Exception as e:
            raise osv.except_osv('Client recursif !','')
#            raise osv.except_osv(_('Client!'),
#                             _('(%s).') % tools.ustr(e).decode('utf-8'))

    @api.model
    def create(self, vals):
        try:
            obj=super(res_partner, self).create(vals)
            self.env['is.database'].copy_other_database(obj)
        except Exception as e:
            raise osv.except_osv('Client recursif !','')
#            raise osv.except_osv(_('Client!'),
#                             _('(%s).') % str(e).decode('utf-8'))
        #global test_recursive
        #test_recursive=0

        return obj


class is_mold_project(models.Model):
    _inherit = 'is.mold.project'
 
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)

    @api.multi
    def write(self, vals):
        try:
            res=super(is_mold_project, self).write(vals)
            for obj in self:
                obj.copy_other_database_project()
            return res
        except Exception as e:
            raise osv.except_osv(_('Project!'),
                             _('(%s).') % str(e).decode('utf-8'))

    @api.model
    def create(self, vals):
        try:
            obj=super(is_mold_project, self).create(vals)
            obj.copy_other_database_project()
            return obj
        except Exception as e:
            raise osv.except_osv(_('Project!'),
                             _('(%s).') % str(e).decode('utf-8'))
    
    @api.multi
    def copy_other_database_project(self):
        cr , uid, context = self.env.args
        context = dict(context)
        project_obj = self.env['is.mold.project']
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for project in self:
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
                project_vals = self.get_project_vals(project, DB, USERID, USERPASS, sock)
                ids = sock.execute(DB, USERID, USERPASS, 'is.mold.project', 'search', [('is_database_origine_id', '=', project.id)], {})
                if not ids:
                    ids = sock.execute(DB, USERID, USERPASS, 'is.mold.project', 'search', [('name', '=', project.name)], {})
                if ids:
                    sock.execute(DB, USERID, USERPASS, 'is.mold.project', 'write', ids, project_vals, {})
                    created_id = ids[0]
                else:
                    created_id = sock.execute(DB, USERID, USERPASS, 'is.mold.project', 'create', project_vals, {})
        return True


    @api.model
    def get_project_vals(self, project, DB, USERID, USERPASS, sock):
        project_vals = {
            'name': project.name,
            'client_id'             : self._get_client_id(project, DB, USERID, USERPASS, sock),
            'chef_projet_id'        : self._get_chef_projet_id(project, DB, USERID, USERPASS, sock),
            'mold_ids'              : self._get_mold_ids(project, DB, USERID, USERPASS, sock),
            'is_database_origine_id': project.id,
            'commentaire'           : project.commentaire
        }
        return project_vals

    @api.model
    def _get_client_id(self, project, DB, USERID, USERPASS, sock):
        if project.client_id:
            client_ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', project.client_id.id),'|',('active','=',True),('active','=',False)], {})
            #if not client_ids:
            #    self.env['is.database'].copy_other_database( project.client_id)
            #    client_ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', project.client_id.id),'|',('active','=',True),('active','=',False)], {})
            if client_ids:
                return client_ids[0]
        return False
        
    @api.model
    def _get_chef_projet_id(self, project, DB, USERID, USERPASS, sock):
        if project.chef_projet_id:
            chef_projet_ids = sock.execute(DB, USERID, USERPASS, 'res.users', 'search', [('login', '=', project.chef_projet_id.login)], {})
            if chef_projet_ids:
                return chef_projet_ids[0]
        return False
    
    def _get_mold_ids(self, project, DB, USERID, USERPASS, sock):
        list_mold_ids =[]
        for mold in project.mold_ids:
            dest_mold_ids = sock.execute(DB, USERID, USERPASS, 'is.mold', 'search', [('is_database_origine_id', '=', mold.id)], {})
#             if not dest_mold_ids:
#                 mold.copy_other_database_mold()
#                 dest_mold_ids = sock.execute(DB, USERID, USERPASS, 'is.mold', 'search', [('is_database_origine_id', '=', mold.id)], {})
            if dest_mold_ids:
                list_mold_ids.append(dest_mold_ids[0])
        
        return [(6, 0, list_mold_ids)]
        

class is_dossierf(models.Model):
    _inherit='is.dossierf'
    
    is_database_id         = fields.Many2one('is.database', "Site")
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)

    @api.multi
    def write(self, vals):
        res=super(is_dossierf, self).write(vals)
        for obj in self:
            obj.copy_other_database_dossierf()
        return res

    @api.model
    def create(self, vals):
        obj=super(is_dossierf, self).create(vals)
        obj.copy_other_database_dossierf()
        return obj
    
    @api.multi
    def copy_other_database_dossierf(self):
        cr , uid, context = self.env.args
        context = dict(context)
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for dossierf in self:
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
                dossierf_vals = self.get_dossierf_vals(dossierf, DB, USERID, USERPASS, sock)
                ids = sock.execute(DB, USERID, USERPASS, 'is.dossierf', 'search', [('is_database_origine_id', '=', dossierf.id)], {})
                if not ids:
                    ids = sock.execute(DB, USERID, USERPASS, 'is.dossierf', 'search', [('name', '=', dossierf.name)], {})
                if ids:
                    sock.execute(DB, USERID, USERPASS, 'is.dossierf', 'write', ids, dossierf_vals, {})
                    created_id = ids[0]
                else:
                    created_id = sock.execute(DB, USERID, USERPASS, 'is.dossierf', 'create', dossierf_vals, {})
        return True
    
    
    @api.model
    def get_dossierf_vals(self, dossierf, DB, USERID, USERPASS, sock):
        dossierf_vals = {
            'name': dossierf.name,
            'designation':dossierf.designation,
            'project':self._get_project(dossierf, DB, USERID, USERPASS, sock),
            'mold_ids': self._get_mold_ids(dossierf, DB, USERID, USERPASS, sock),
            'is_database_origine_id':dossierf.id,
            'is_database_id':self._get_is_database_id(dossierf, DB, USERID, USERPASS, sock),
        }
        return dossierf_vals
    
    @api.model    
    def _get_project(self, dossierf, DB, USERID, USERPASS, sock):
        if dossierf.project:
            project_ids = sock.execute(DB, USERID, USERPASS, 'is.mold.project', 'search', [('is_database_origine_id', '=', dossierf.project.id)], {})
            if not project_ids:
                dossierf.project.copy_other_database_project()
                project_ids = sock.execute(DB, USERID, USERPASS, 'is.mold.project', 'search', [('is_database_origine_id', '=', dossierf.project.id)], {})
            if project_ids:
                return project_ids[0]
        return False
    
    def _get_mold_ids(self, dossierf, DB, USERID, USERPASS, sock):
        list_mold_ids =[]
        for mold in dossierf.mold_ids:
            dest_mold_ids = sock.execute(DB, USERID, USERPASS, 'is.mold', 'search', [('is_database_origine_id', '=', mold.id)], {})
#             if not dest_mold_ids:
#                 mold.copy_other_database_mold()
#                 dest_mold_ids = sock.execute(DB, USERID, USERPASS, 'is.mold', 'search', [('is_database_origine_id', '=', mold.id)], {})
            if dest_mold_ids:
                list_mold_ids.append(dest_mold_ids[0])
        
        return [(6, 0, list_mold_ids)]


    @api.model
    def _get_is_database_id(self, dossierf, DB, USERID, USERPASS, sock):
        if dossierf.is_database_id:
            ids = sock.execute(DB, USERID, USERPASS, 'is.database', 'search', [('is_database_origine_id', '=', dossierf.is_database_id.id)], {})
            if ids:
                return ids[0]
        return False






class is_mold(models.Model):
    _inherit = 'is.mold'

    is_database_id         = fields.Many2one('is.database', "Site")
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)


    @api.multi
    def write(self, vals):
        res=super(is_mold, self).write(vals)
        for obj in self:
            obj.copy_other_database_mold()
        return res

    @api.model
    def create(self, vals):
        obj=super(is_mold, self).create(vals)
        obj.copy_other_database_mold()
        return obj
    
    @api.multi
    def copy_other_database_mold(self):
        cr , uid, context = self.env.args
        context = dict(context)
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for mold in self:
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
                mold_vals = self.get_mold_vals(mold, DB, USERID, USERPASS, sock)

                ids = sock.execute(DB, USERID, USERPASS, 'is.mold', 'search', [('is_database_origine_id', '=', mold.id)], {})
                if not ids:
                    ids = sock.execute(DB, USERID, USERPASS, 'is.mold', 'search', [('name', '=', mold.name)], {})
                if ids:
                    sock.execute(DB, USERID, USERPASS, 'is.mold', 'write', ids, mold_vals, {})
                    created_id = ids[0]
                else:
                    created_id = sock.execute(DB, USERID, USERPASS, 'is.mold', 'create', mold_vals, {})
        return True


    @api.model
    def get_mold_vals(self, mold, DB, USERID, USERPASS, sock):
        mold_vals = {
        'name'             : mold.name,
        'designation'      : mold.designation,
        'project'          : self._get_project(mold, DB, USERID, USERPASS, sock),
        'dossierf_id'      : self._get_dossierf_id(mold, DB, USERID, USERPASS, sock),
        'nb_empreintes'    : mold.nb_empreintes,
        'moule_a_version'  : mold.moule_a_version,
        'lieu_changement'  : mold.lieu_changement,
        'temps_changement' : mold.temps_changement,
        'date_creation'    : mold.date_creation,
        'date_fin'         : mold.date_fin,
        'mouliste_id'      : self._get_mouliste_id(mold, DB, USERID, USERPASS, sock),
        'carcasse'         : mold.carcasse,
        'type_dateur'      : mold.type_dateur,
        'dateur_specifique': mold.dateur_specifique,
        'date_peremption'  : mold.date_peremption,
        'qt_dans_moule'    : mold.qt_dans_moule,
        'diametre_laiton'  : mold.diametre_laiton,
        'diametre_fleche'  : mold.diametre_fleche,
        'is_database_origine_id': mold.id,
        'is_database_id'        : self._get_is_database_id(mold, DB, USERID, USERPASS, sock),
        }
        return mold_vals

    @api.model
    def _get_dossierf_id(self, mold, DB, USERID, USERPASS, sock):
        if mold.dossierf_id:
            dossierf_ids = sock.execute(DB, USERID, USERPASS, 'is.dossierf', 'search', [('is_database_origine_id', '=', mold.dossierf_id.id)], {})
            if dossierf_ids:
                mold.dossierf_id.copy_other_database_dossierf()
                dossierf_ids = sock.execute(DB, USERID, USERPASS, 'is.dossierf', 'search', [('is_database_origine_id', '=', mold.dossierf_id.id)], {})
            if dossierf_ids:
                return dossierf_ids[0]
        return False
        
    @api.model    
    def _get_project(self, mold, DB, USERID, USERPASS, sock):
        if mold.project:
            project_ids = sock.execute(DB, USERID, USERPASS, 'is.mold.project', 'search', [('is_database_origine_id', '=', mold.project.id)], {})
            if not project_ids:
                mold.project.copy_other_database_project()
                project_ids = sock.execute(DB, USERID, USERPASS, 'is.mold.project', 'search', [('is_database_origine_id', '=', mold.project.id)], {})
            if project_ids:
                return project_ids[0]
        return False
    
    @api.model
    def _get_mouliste_id(self, mold, DB, USERID, USERPASS, sock):
        if mold.mouliste_id:
            mouliste_ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', mold.mouliste_id.id),'|',('active','=',True),('active','=',False)], {})
            if not mouliste_ids:
                self.env['is.database'].copy_other_database(mold.mouliste_id)
                mouliste_ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', mold.mouliste_id.id),'|',('active','=',True),('active','=',False)], {})
            if mouliste_ids:
                return mouliste_ids[0]
        return False


    @api.model
    def _get_is_database_id(self, mold, DB, USERID, USERPASS, sock):
        if mold.is_database_id:
            ids = sock.execute(DB, USERID, USERPASS, 'is.database', 'search', [('is_database_origine_id', '=', mold.is_database_id.id)], {})
            if ids:
                return ids[0]
        return False





#class is_copy_partner(models.Model):
#    _name = 'is.copy.partner'



#    @api.multi
#    def get_fields_model(self, model, exclude=[], include=False):
#        search=[
#            ('model_id.model', '=',model),
#            ('name','not in', ['create_date','create_uid','display_name','id','__last_update','write_date','write_uid']),
#        ]
#        if include:
#            search.append(('name','in', include))
#        res = self.env['ir.model.fields'].search(search)
#        champs=[]
#        for champ in res:
#            if champ.name not in exclude:
#                champs.append(champ)
#        return champs

#    @api.multi
#    def copy_other_database(self, obj, champs):
#        cr , uid, context = self.env.args
#        class_name=obj.__class__.__name__
#        database_obj   = self.env['is.database']
#        database_lines = database_obj.search([])
#        for database in database_lines:
#            if database.database:
#                DB           = database.database
#                USERID       = uid
#                DBLOGIN      = database.login
#                USERPASS     = database.password
#                DB_SERVER    = database.ip_server
#                DB_PORT      = database.port_server
#                sock         = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/object' % (DB_SERVER, DB_PORT))
#                vals={}
#                for champ in champs:
#                    val=getattr(obj, champ.name) 
#                    if champ.ttype=='many2one':
#                        val=val.id
#                    vals[champ.name]=val
#                vals['is_database_origine_id']=obj.id
#                dest_ids = sock.execute(DB, USERID, USERPASS, class_name, 'search', [('is_database_origine_id', '=', obj.id)], {})
#                if not dest_ids:
#                    dest_ids = sock.execute(DB, USERID, USERPASS, class_name, 'search', [('name', '=', obj.name)], {})
#                if dest_ids:
#                    sock.execute(DB, USERID, USERPASS, class_name, 'write', dest_ids, vals, {})
#                    created_id = dest_ids[0]
#                else:
#                    created_id = sock.execute(DB, USERID, USERPASS, class_name, 'create', vals, {})


class is_segment_achat(models.Model):
    _inherit = 'is.segment.achat'

    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)

    @api.multi
    def write(self, vals):
        try:
            res=super(is_segment_achat, self).write(vals)
            for obj in self:
                obj.copy_other_database_segment_achat()
            return res
        except Exception as e:
            raise osv.except_osv(_('Segment!'),
                             _('(%s).') % str(e).decode('utf-8'))


    @api.model
    def create(self, vals):
        try:
            obj=super(is_segment_achat, self).create(vals)
            obj.copy_other_database_segment_achat()
            return obj
        except Exception as e:
            raise osv.except_osv(_('Segment!'),
                             _('(%s).') % str(e).decode('utf-8'))

    
    
    @api.multi
    def copy_other_database_segment_achat(self):
        cr , uid, context = self.env.args
        context = dict(context)
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for segment in self:
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
                segment_achat_vals = self.get_segment_achat_vals(segment, DB, USERID, USERPASS, sock)
                dest_segment_achat_ids = sock.execute(DB, USERID, USERPASS, 'is.segment.achat', 'search', [('is_database_origine_id', '=', segment.id)], {})
                if not dest_segment_achat_ids:
                    dest_segment_achat_ids = sock.execute(DB, USERID, USERPASS, 'is.segment.achat', 'search', [('name', '=', segment.name)], {})
                if dest_segment_achat_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.segment.achat', 'write', dest_segment_achat_ids, segment_achat_vals, {})
                    segment_achat_created_id = dest_segment_achat_ids[0]
                else:
                    segment_achat_created_id = sock.execute(DB, USERID, USERPASS, 'is.segment.achat', 'create', segment_achat_vals, {})
        return True

    def _get_family_line(self, segment, DB, USERID, USERPASS, sock):
        lines = []
        for family_line in segment.family_line:
            lines.append(((0, 0, {'name':tools.ustr(family_line.name), 'description': family_line.description,})))
#             family_line_ids = sock.execute(DB, USERID, USERPASS, 'is.famille.achat', 'search', [('is_database_origine_id', '=', family_line.id)], {})
#             if not family_line_ids:
#                 family_line.copy_other_database_famille_achat()
#                 family_line_ids = sock.execute(DB, USERID, USERPASS, 'is.famille.achat', 'search', [('is_database_origine_id', '=', family_line.id)], {})
#             if family_line_ids:
#                 lines.append(family_line_ids[0]) 
        return lines
    
    @api.model
    def get_segment_achat_vals(self, segment, DB, USERID, USERPASS, sock):
        segment_achat_vals ={
                             'name'       : tools.ustr(segment.name),
                             'description': tools.ustr(segment.description),
                             'is_database_origine_id':segment.id,
#                             'family_line': self._get_family_line(segment, DB, USERID, USERPASS, sock)
                             
                             }
        return segment_achat_vals
        
class is_famille_achat(models.Model):
    _inherit = 'is.famille.achat'
  
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
 
    @api.multi
    def write(self, vals):
        try:
            res=super(is_famille_achat, self).write(vals)
            for obj in self:
                obj.copy_other_database_famille_achat()
            return res
        except Exception as e:
            raise osv.except_osv(_('Famille!'),
                             _('(%s).') % str(e).decode('utf-8'))
 
    @api.model
    def create(self, vals):
        try:
            obj=super(is_famille_achat, self).create(vals)
            obj.copy_other_database_famille_achat()
            return obj
        except Exception as e:
            raise osv.except_osv(_('Famille!'),
                             _('(%s).') % str(e).decode('utf-8'))
#     
#     
    @api.multi
    def copy_other_database_famille_achat(self):
        cr , uid, context = self.env.args
        context = dict(context)
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for famille in self:
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
                famille_achat_vals = self.get_famille_achat_vals(famille, DB, USERID, USERPASS, sock)
                dest_famille_achat_ids = sock.execute(DB, USERID, USERPASS, 'is.famille.achat', 'search', [('is_database_origine_id', '=', famille.id)], {})
                if not dest_famille_achat_ids:
                    dest_famille_achat_ids = sock.execute(DB, USERID, USERPASS, 'is.famille.achat', 'search', [('name', '=', famille.name)], {})
                if dest_famille_achat_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.famille.achat', 'write', dest_famille_achat_ids, famille_achat_vals, {})
                    famille_achat_created_id = dest_famille_achat_ids[0]
                else:
                    famille_achat_created_id = sock.execute(DB, USERID, USERPASS, 'is.famille.achat', 'create', famille_achat_vals, {})
        return True
# 
 
    @api.model
    def get_segment_id(self, famille, DB, USERID, USERPASS, sock):
        if famille.segment_id:
            segment_ids = sock.execute(DB, USERID, USERPASS, 'is.segment.achat', 'search', [('is_database_origine_id', '=', famille.segment_id.id)], {})
            if not segment_ids:
                famille.segment_id.copy_other_database_segment_achat()
                segment_ids = sock.execute(DB, USERID, USERPASS, 'is.segment.achat', 'search', [('is_database_origine_id', '=', famille.segment_id.id)], {})
            if segment_ids:
                return segment_ids[0]
        return False
#         
    @api.model
    def get_famille_achat_vals(self, famille, DB, USERID, USERPASS, sock):
        famille_achat_vals ={
                             'name'       : tools.ustr(famille.name),
                             'description': tools.ustr(famille.description),
                            'segment_id' : self.get_segment_id(famille, DB, USERID, USERPASS, sock),
                              'is_database_origine_id':famille.id,
                             }
         
        return famille_achat_vals
    
    
class is_site(models.Model):
    _inherit = 'is.site'
 
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)

    @api.multi
    def write(self, vals):
        try:
            res=super(is_site, self).write(vals)
            for obj in self:
                obj.copy_other_database_is_site()
            return res
        except Exception as e:
            raise osv.except_osv(_('Site!'),
                             _('(%s).') % str(e).decode('utf-8'))
            
    @api.model
    def create(self, vals):
        try:
            obj=super(is_site, self).create(vals)
            obj.copy_other_database_is_site()
            return obj
        except Exception as e:
            raise osv.except_osv(_('Site!'),
                             _('(%s).') % str(e).decode('utf-8'))
    
    
    @api.multi
    def copy_other_database_is_site(self):
        cr , uid, context = self.env.args
        context = dict(context)
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for is_site in self:
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
                is_site_vals = self.get_is_site_vals(is_site, DB, USERID, USERPASS, sock)
                dest_is_site_ids = sock.execute(DB, USERID, USERPASS, 'is.site', 'search', [('is_database_origine_id', '=', is_site.id)], {})
                if not dest_is_site_ids:
                    dest_is_site_ids = sock.execute(DB, USERID, USERPASS, 'is.site', 'search', [('name', '=', is_site.name)], {})
                if dest_is_site_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.site', 'write', dest_is_site_ids, is_site_vals, {})
                    is_site_created_id = dest_is_site_ids[0]
                else:
                    is_site_created_id = sock.execute(DB, USERID, USERPASS, 'is.site', 'create', is_site_vals, {})
        return True

        
    @api.model
    def get_is_site_vals(self, is_site, DB, USERID, USERPASS, sock):
        is_site_vals ={
                     'name' : tools.ustr(is_site.name),
                     'is_database_origine_id':is_site.id
                     }
        return is_site_vals
    
    
class is_transmission_cde(models.Model):
    _inherit = 'is.transmission.cde'

    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)

    @api.multi
    def write(self, vals):
        try:
            res=super(is_transmission_cde, self).write(vals)
            for obj in self:
                obj.copy_other_database_transmission_cde()
            return res
        except Exception as e:
            raise osv.except_osv(_('Transmission!'),
                             _('(%s).') % str(e).decode('utf-8'))

    @api.model
    def create(self, vals):
        try:
            obj=super(is_transmission_cde, self).create(vals)
            obj.copy_other_database_transmission_cde()
            return obj
        except Exception as e:
            raise osv.except_osv(_('Transmission!'),
                             _('(%s).') % str(e).decode('utf-8'))
    
    
    @api.multi
    def copy_other_database_transmission_cde(self):
        cr , uid, context = self.env.args
        context = dict(context)
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for is_transmission in self:
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
                is_transmission_vals = self.get_is_transmission_vals(is_transmission, DB, USERID, USERPASS, sock)
                dest_is_transmission_ids = sock.execute(DB, USERID, USERPASS, 'is.transmission.cde', 'search', [('is_database_origine_id', '=', is_transmission.id)], {})
                if not dest_is_transmission_ids:
                    dest_is_transmission_ids = sock.execute(DB, USERID, USERPASS, 'is.transmission.cde', 'search', [('name', '=', is_transmission.name)], {})
                if dest_is_transmission_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.transmission.cde', 'write', dest_is_transmission_ids, is_transmission_vals, {})
                    is_transmission_created_id = dest_is_transmission_ids[0]
                else:
                    is_transmission_created_id = sock.execute(DB, USERID, USERPASS, 'is.transmission.cde', 'create', is_transmission_vals, {})
        return True

        
    @api.model
    def get_is_transmission_vals(self, is_transmission, DB, USERID, USERPASS, sock):
        is_transmission_vals ={
                     'name' : tools.ustr(is_transmission.name),
                     'is_database_origine_id':is_transmission.id,
                     }
        return is_transmission_vals
    


class is_norme_certificats(models.Model):
    _inherit = 'is.norme.certificats'

    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)

    @api.multi
    def write(self, vals):
        try:
            res=super(is_norme_certificats, self).write(vals)
            for obj in self:
                obj.copy_other_database_norme_certificats()
            return res
        except Exception as e:
            raise osv.except_osv(_('Norme!'),
                             _('(%s).') % str(e).decode('utf-8'))

    @api.model
    def create(self, vals):
        try:
            obj=super(is_norme_certificats, self).create(vals)
            obj.copy_other_database_norme_certificats()
            return obj
        except Exception as e:
            raise osv.except_osv(_('Norme!'),
                             _('(%s).') % str(e).decode('utf-8'))
    
    
    @api.multi
    def copy_other_database_norme_certificats(self):
        cr , uid, context = self.env.args
        context = dict(context)
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for norme_certificats in self:
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
                norme_certificats_vals = self.get_is_norme_certificats_vals(norme_certificats, DB, USERID, USERPASS, sock)
                dest_norme_certificats_ids = sock.execute(DB, 1, USERPASS, 'is.norme.certificats', 'search', [('is_database_origine_id', '=', norme_certificats.id)], {})
                if not dest_norme_certificats_ids:
                    dest_norme_certificats_ids = sock.execute(DB, USERID, USERPASS, 'is.norme.certificats', 'search', [('name', '=', norme_certificats.name)], {})
                if dest_norme_certificats_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.norme.certificats', 'write', dest_norme_certificats_ids, norme_certificats_vals, {})
                    norme_certificats_created_id = dest_norme_certificats_ids[0]
                else:
                    norme_certificats_created_id = sock.execute(DB, USERID, USERPASS, 'is.norme.certificats', 'create', norme_certificats_vals, {})
        return True

        
    @api.model
    def get_is_norme_certificats_vals(self, norme_certificats, DB, USERID, USERPASS, sock):
        norme_certificats_vals ={
                     'name' : tools.ustr(norme_certificats.name),
                     'is_database_origine_id':norme_certificats.id,
                     }
        return norme_certificats_vals
    
    
class is_certifications_qualite(models.Model):
    _inherit = 'is.certifications.qualite'
    
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
    
    @api.multi
    def write(self, vals):
        try:
            res=super(is_certifications_qualite, self).write(vals)
            for obj in self:
                obj.copy_other_database_certifications_qualite()
            return res
        except Exception as e:
            raise osv.except_osv(_('Qualite!'),
                             _('(%s).') % str(e).decode('utf-8'))


    @api.model
    def create(self, vals):
        try:
            obj=super(is_certifications_qualite, self).create(vals)
            obj.copy_other_database_certifications_qualite()
            return obj
        except Exception as e:
            raise osv.except_osv(_('Qualite!'),
                             _('(%s).') % str(e).decode('utf-8'))

    
    @api.multi
    def copy_other_database_certifications_qualite(self):
        cr , uid, context = self.env.args
        context = dict(context)
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for certifications_qualite in self:
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
                certifications_qualite_vals = self.get_is_certifications_qualite_vals(certifications_qualite, DB, USERID, USERPASS, sock)
                dest_certifications_qualite_ids = sock.execute(DB, USERID, USERPASS, 'is.certifications.qualite', 'search', [('is_database_origine_id', '=', certifications_qualite.id)], {})
#                 if not dest_certifications_qualite_ids:
#                     dest_certifications_qualite_ids = sock.execute(DB, USERID, USERPASS, 'is.certifications.qualite', 'search', [('is_norme', '=', certifications_qualite.is_norme.id)], {})
                if dest_certifications_qualite_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.certifications.qualite', 'write', dest_certifications_qualite_ids, certifications_qualite_vals, {})
                    certifications_qualite_created_id = dest_certifications_qualite_ids[0]
                else:
                    certifications_qualite_created_id = sock.execute(DB, USERID, USERPASS, 'is.certifications.qualite', 'create', certifications_qualite_vals, {})
        return True


    @api.model
    def _get_is_norme(self, certifications_qualite, DB, USERID, USERPASS, sock):
        if certifications_qualite.is_norme:
            is_norme_ids = sock.execute(DB, USERID, USERPASS, 'is.norme.certificats', 'search', [('is_database_origine_id', '=', certifications_qualite.is_norme.id)], {})
            if not is_norme_ids:
                certifications_qualite.is_norme.copy_other_database_norme_certificats()
                is_norme_ids = sock.execute(DB, USERID, USERPASS, 'is.norme.certificats', 'search', [('is_database_origine_id', '=', certifications_qualite.is_norme.id)], {})
            if is_norme_ids:
                return is_norme_ids[0]
        return False

    @api.model
    def _get_certificat_ids(self, certifications_qualite, DB, USERID, USERPASS, sock):
        certificat_data = []
        for  certificat in certifications_qualite.is_certificat_ids:
            certificat_data.append(((0, 0, {'name':tools.ustr(certificat.name), 'datas':certificat.datas, 'res_model':certificat.res_model})))
        return certificat_data
    @api.model
    def get_is_certifications_qualite_vals(self, certifications_qualite, DB, USERID, USERPASS, sock):
        certifications_qualite_vals ={
                     'is_norme' : self._get_is_norme(certifications_qualite, DB, USERID, USERPASS, sock),
                     'is_date_validation':certifications_qualite.is_date_validation,
                     'is_certificat_ids':self._get_certificat_ids(certifications_qualite, DB, USERID, USERPASS, sock),
                     'is_database_origine_id':certifications_qualite.id,
                     }
        return certifications_qualite_vals
    
    
class is_facturation_fournisseur_justification(models.Model):
    _inherit='is.facturation.fournisseur.justification'

    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
    
    @api.multi
    def write(self, vals):
        try:
            res=super(is_facturation_fournisseur_justification, self).write(vals)
            for obj in self:
                obj.copy_other_database_fournisseur_justification()
            return res
        except Exception as e:
            raise osv.except_osv(_('Justification!'),
                             _('(%s).') % str(e).decode('utf-8'))


    @api.model
    def create(self, vals):
        try:
            obj=super(is_facturation_fournisseur_justification, self).create(vals)
            obj.copy_other_database_fournisseur_justification()
            return obj
        except Exception as e:
            raise osv.except_osv(_('Justification!'),
                             _('(%s).') % str(e).decode('utf-8'))

    
    @api.multi
    def copy_other_database_fournisseur_justification(self):
        cr , uid, context = self.env.args
        context = dict(context)
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for justification in self:
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
                justification_vals = self.get_justification_vals(justification, DB, USERID, USERPASS, sock)
                dest_justification_ids = sock.execute(DB, USERID, USERPASS, 'is.facturation.fournisseur.justification', 'search', [('is_database_origine_id', '=', justification.id)], {})
                if not dest_justification_ids:
                    dest_justification_ids = sock.execute(DB, USERID, USERPASS, 'is.facturation.fournisseur.justification', 'search', [('name', '=', justification.name)], {})
                if dest_justification_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.facturation.fournisseur.justification', 'write', dest_justification_ids, justification_vals, {})
                    justification_created_id = dest_justification_ids[0]
                else:
                    justification_created_id = sock.execute(DB, USERID, USERPASS, 'is.facturation.fournisseur.justification', 'create', justification_vals, {})
        return True

    @api.model
    def get_justification_vals(self, justification, DB, USERID, USERPASS, sock):
        justification_vals ={
                     'name' : tools.ustr(justification.name),
                     'is_database_origine_id':justification.id,
                     }
        return justification_vals
    
    
class is_secteur_activite(models.Model):
    _inherit='is.secteur.activite'
 
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
    
    @api.multi
    def write(self, vals):
        try:
            res=super(is_secteur_activite, self).write(vals)
            for obj in self:
                obj.copy_other_database_secteur_activite()
            return res
        except Exception as e:
            raise osv.except_osv(_('Secteur!'),
                             _('(%s).') % str(e).decode('utf-8'))


    @api.model
    def create(self, vals):
        try:
            obj=super(is_secteur_activite, self).create(vals)
            obj.copy_other_database_secteur_activite()
            return obj
        except Exception as e:
            raise osv.except_osv(_('Secteur!'),
                             _('(%s).') % str(e).decode('utf-8'))
    
    @api.multi
    def copy_other_database_secteur_activite(self):
        cr , uid, context = self.env.args
        context = dict(context)
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for activite in self:
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
                activite_vals = self.get_activite_vals(activite, DB, USERID, USERPASS, sock)
                dest_activite_ids = sock.execute(DB, USERID, USERPASS, 'is.secteur.activite', 'search', [('is_database_origine_id', '=', activite.id)], {})
                if not dest_activite_ids:
                    dest_activite_ids = sock.execute(DB, USERID, USERPASS, 'is.secteur.activite', 'search', [('name', '=', activite.name)], {})
                if dest_activite_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.secteur.activite', 'write', dest_activite_ids, activite_vals, {})
                    activite_created_id = dest_activite_ids[0]
                else:
                    activite_created_id = sock.execute(DB, USERID, USERPASS, 'is.secteur.activite', 'create', activite_vals, {})
        return True

    @api.model
    def get_activite_vals(self, activite, DB, USERID, USERPASS, sock):
        activite_vals ={
                     'name' : tools.ustr(activite.name),
                     'is_database_origine_id':activite.id,
                     }
        return activite_vals
    

class is_type_contact(models.Model):
    _inherit='is.type.contact'
    
    
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
    
    @api.multi
    def write(self, vals):
        try:
            res=super(is_type_contact, self).write(vals)
            for obj in self:
                obj.copy_other_database_type_contact()
            return res
        except Exception as e:
            raise osv.except_osv(_('Contact!'),
                             _('(%s).') % str(e).decode('utf-8'))


    @api.model
    def create(self, vals):
        try:
            obj=super(is_type_contact, self).create(vals)
            obj.copy_other_database_type_contact()
            return obj
        except Exception as e:
            raise osv.except_osv(_('Contact!'),
                             _('(%s).') % str(e).decode('utf-8'))

    
    @api.multi
    def copy_other_database_type_contact(self):
        cr , uid, context = self.env.args
        context = dict(context)
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for type_contact in self:
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
                type_contact_vals = self.get_type_contact_vals(type_contact, DB, USERID, USERPASS, sock)
                dest_type_contact_ids = sock.execute(DB, USERID, USERPASS, 'is.type.contact', 'search', [('is_database_origine_id', '=', type_contact.id)], {})
                if not dest_type_contact_ids:
                    dest_type_contact_ids = sock.execute(DB, USERID, USERPASS, 'is.type.contact', 'search', [('name', '=', type_contact.name)], {})
                if dest_type_contact_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.type.contact', 'write', dest_type_contact_ids, type_contact_vals, {})
                    type_contact_created_id = dest_type_contact_ids[0]
                else:
                    type_contact_created_id = sock.execute(DB, USERID, USERPASS, 'is.type.contact', 'create', type_contact_vals, {})
        return True

    @api.model
    def get_type_contact_vals(self, type_contact, DB, USERID, USERPASS, sock):
        type_contact_vals ={
                     'name' : tools.ustr(type_contact.name),
                     'is_database_origine_id':type_contact.id,
                     }
        return type_contact_vals
    
class is_escompte(models.Model):
    _inherit='is.escompte'

    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
    
    @api.multi
    def write(self, vals):
        try:
            res=super(is_escompte, self).write(vals)
            for obj in self:
                obj.copy_other_database_is_escompte()
            return res
        except Exception as e:
            raise osv.except_osv(_('escompte!'),
                             _('(%s).') % str(e).decode('utf-8'))

    @api.model
    def create(self, vals):
        try:
            obj=super(is_escompte, self).create(vals)
            obj.copy_other_database_is_escompte()
            return obj
        except Exception as e:
            raise osv.except_osv(_('escompte!'),
                             _('(%s).') % str(e).decode('utf-8'))

    
    @api.multi
    def copy_other_database_is_escompte(self):
        cr , uid, context = self.env.args
        context = dict(context)
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for is_escompte in self:
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
                is_escompte_vals = self.get_is_escompte_vals(is_escompte, DB, USERID, USERPASS, sock)
                dest_is_escompte_ids = sock.execute(DB, USERID, USERPASS, 'is.escompte', 'search', [('is_database_origine_id', '=', is_escompte.id)], {})
                if not dest_is_escompte_ids:
                    dest_is_escompte_ids = sock.execute(DB, USERID, USERPASS, 'is.escompte', 'search', [('name', '=', is_escompte.name)], {})
                if dest_is_escompte_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.escompte', 'write', dest_is_escompte_ids, is_escompte_vals, {})
                    is_escompte_created_id = dest_is_escompte_ids[0]
                else:
                    is_escompte_created_id = sock.execute(DB, USERID, USERPASS, 'is.escompte', 'create', is_escompte_vals, {})
        return True

    @api.model
    def _get_is_escompte_compte(self, is_escompte, DB, USERID, USERPASS, sock):
        if is_escompte.compte:
            dest_compte_ids = sock.execute(DB, USERID, USERPASS, 'account.account', 'search', [('code', '=', is_escompte.compte.code)], {})
            if dest_compte_ids:
                return dest_compte_ids[0]
        return False
            
    
    @api.model
    def get_is_escompte_vals(self, is_escompte, DB, USERID, USERPASS, sock):
        is_escompte_vals ={
                     'name' : tools.ustr(is_escompte.name),
                     'taux' : is_escompte.taux,
                     'compte': self._get_is_escompte_compte(is_escompte, DB, USERID, USERPASS, sock),
                     'is_database_origine_id':is_escompte.id
                     }
        return is_escompte_vals

    
class is_type_controle_gabarit(models.Model):
    _inherit = "is.type.controle.gabarit"
    
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)

    @api.multi
    def write(self, vals):
        try:
            res=super(is_type_controle_gabarit, self).write(vals)
            for obj in self:
                obj.copy_other_database_controle_gabarit()
            return res
        except Exception as e:
            raise osv.except_osv(_('Gabarit!'),
                             _('(%s).') % str(e).decode('utf-8'))


    @api.model
    def create(self, vals):
        try:
            obj=super(is_type_controle_gabarit, self).create(vals)
            obj.copy_other_database_controle_gabarit()
            return obj
        except Exception as e:
            raise osv.except_osv(_('Gabarit!'),
                             _('(%s).') % str(e).decode('utf-8'))
            
    @api.multi
    def copy_other_database_controle_gabarit(self):
        cr , uid, context = self.env.args
        context = dict(context)
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for gabarit in self:
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
                controle_gabarit_vals = self.get_type_controle_gabarit_vals(gabarit, DB, USERID, USERPASS, sock)
                dest_controle_gabarit_ids = sock.execute(DB, USERID, USERPASS, 'is.type.controle.gabarit', 'search', [('is_database_origine_id', '=', gabarit.id)], {})
                if not dest_controle_gabarit_ids:
                    dest_controle_gabarit_ids = sock.execute(DB, USERID, USERPASS, 'is.type.controle.gabarit', 'search', [('name', '=', gabarit.name)], {})
                if dest_controle_gabarit_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.type.controle.gabarit', 'write', dest_controle_gabarit_ids, controle_gabarit_vals, {})
                    controle_gabarit_created_id = dest_controle_gabarit_ids[0]
                else:
                    controle_gabarit_created_id = sock.execute(DB, USERID, USERPASS, 'is.type.controle.gabarit', 'create', controle_gabarit_vals, {})
        return True

    @api.model
    def get_type_controle_gabarit_vals(self, gabarit, DB, USERID, USERPASS, sock):
        controle_gabarit_vals ={
                     'name' : tools.ustr(gabarit.name),
                     'is_database_origine_id':gabarit.id,
                     }
        return controle_gabarit_vals
    

class is_presse_classe(models.Model):
    _inherit='is.presse.classe'
    
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
   
    @api.multi
    def write(self, vals):
        try:
            res=super(is_presse_classe, self).write(vals)
            for obj in self:
                obj.copy_other_database_presse_classe()
            return res
        except Exception as e:
            raise osv.except_osv(_('Classe!'),
                             _('(%s).') % str(e).decode('utf-8'))


    @api.model
    def create(self, vals):
        try:
            obj=super(is_presse_classe, self).create(vals)
            obj.copy_other_database_presse_classe()
            return obj
        except Exception as e:
            raise osv.except_osv(_('Classe!'),
                             _('(%s).') % str(e).decode('utf-8'))
            
    @api.multi
    def copy_other_database_presse_classe(self):
        cr , uid, context = self.env.args
        context = dict(context)
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for classe in self:
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
                presse_classe_vals = self.get_presse_classe_vals(classe, DB, USERID, USERPASS, sock)
                dest_presse_classe_ids = sock.execute(DB, USERID, USERPASS, 'is.presse.classe', 'search', [('is_database_origine_id', '=', classe.id)], {})
                if not dest_presse_classe_ids:
                    dest_presse_classe_ids = sock.execute(DB, USERID, USERPASS, 'is.presse.classe', 'search', [('name', '=', classe.name)], {})
                if dest_presse_classe_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.presse.classe', 'write', dest_presse_classe_ids, presse_classe_vals, {})
                    presse_classe_created_id = dest_presse_classe_ids[0]
                else:
                    presse_classe_created_id = sock.execute(DB, USERID, USERPASS, 'is.presse.classe', 'create', presse_classe_vals, {})
        return True

    @api.model
    def get_presse_classe_vals(self, classe, DB, USERID, USERPASS, sock):
        controle_gabarit_vals ={
                     'name' : tools.ustr(classe.name),
                     'is_database_origine_id':classe.id,
                     }
        return controle_gabarit_vals
   
    
class is_outillage_constructeur(models.Model):
    _inherit='is.outillage.constructeur'

    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
    
    @api.multi
    def write(self, vals):
        try:
            res=super(is_outillage_constructeur, self).write(vals)
            for obj in self:
                obj.copy_other_database_outillage_constructeur()
            return res
        except Exception as e:
            raise osv.except_osv(_('Constructeur!'),
                             _('(%s).') % str(e).decode('utf-8'))


    @api.model
    def create(self, vals):
        try:
            obj=super(is_outillage_constructeur, self).create(vals)
            obj.copy_other_database_outillage_constructeur()
            return obj
        except Exception as e:
            raise osv.except_osv(_('Constructeur!'),
                             _('(%s).') % str(e).decode('utf-8'))
            
    @api.multi
    def copy_other_database_outillage_constructeur(self):
        cr , uid, context = self.env.args
        context = dict(context)
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for constructeur in self:
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
                outillage_constructeur_vals = self.get_outillage_constructeur_vals(constructeur, DB, USERID, USERPASS, sock)
                dest_outillage_constructeur_ids = sock.execute(DB, USERID, USERPASS, 'is.outillage.constructeur', 'search', [('is_database_origine_id', '=', constructeur.id)], {})
                if not dest_outillage_constructeur_ids:
                    dest_outillage_constructeur_ids = sock.execute(DB, USERID, USERPASS, 'is.outillage.constructeur', 'search', [('name', '=', constructeur.name)], {})
                if dest_outillage_constructeur_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.outillage.constructeur', 'write', dest_outillage_constructeur_ids, outillage_constructeur_vals, {})
                    outillage_constructeur_created_id = dest_outillage_constructeur_ids[0]
                else:
                    outillage_constructeur_created_id = sock.execute(DB, USERID, USERPASS, 'is.outillage.constructeur', 'create', outillage_constructeur_vals, {})
        return True

    @api.model
    def get_outillage_constructeur_vals(self, constructeur, DB, USERID, USERPASS, sock):
        outillage_constructeur_vals ={
                     'name' : tools.ustr(constructeur.name),
                     'is_database_origine_id':constructeur.id,
                     }
        return outillage_constructeur_vals

class is_famille_instrument(models.Model):
    _inherit = 'is.famille.instrument'

    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
    
    @api.multi
    def write(self, vals):
        try:
            res=super(is_famille_instrument, self).write(vals)
            for obj in self:
                obj.copy_other_database_famille_instrument()
            return res
        except Exception as e:
            raise osv.except_osv(_('Instrument!'),
                             _('(%s).') % str(e).decode('utf-8'))


    @api.model
    def create(self, vals):
        try:
            obj=super(is_famille_instrument, self).create(vals)
            obj.copy_other_database_famille_instrument()
            return obj
        except Exception as e:
            raise osv.except_osv(_('Instrument!'),
                             _('(%s).') % str(e).decode('utf-8'))
            
    @api.multi
    def copy_other_database_famille_instrument(self):
        cr , uid, context = self.env.args
        context = dict(context)
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for instrument in self:
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
                famille_instrument_vals = self.get_famille_instrument_vals(instrument, DB, USERID, USERPASS, sock)
                dest_famille_instrument_ids = sock.execute(DB, USERID, USERPASS, 'is.famille.instrument', 'search', [('is_database_origine_id', '=', instrument.id)], {})
                if not dest_famille_instrument_ids:
                    dest_famille_instrument_ids = sock.execute(DB, USERID, USERPASS, 'is.famille.instrument', 'search', [('name', '=', instrument.name)], {})
                if dest_famille_instrument_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.famille.instrument', 'write', dest_famille_instrument_ids, famille_instrument_vals, {})
                    famille_instrument_created_id = dest_famille_instrument_ids[0]
                else:
                    famille_instrument_created_id = sock.execute(DB, USERID, USERPASS, 'is.famille.instrument', 'create', famille_instrument_vals, {})
        return True

    @api.model
    def get_famille_instrument_vals(self, instrument, DB, USERID, USERPASS, sock):
        famille_instrument_vals ={
                     'name' : tools.ustr(instrument.name or ''),
                     'intensive': tools.ustr(instrument.intensive or ''),
                     'moyenne': tools.ustr(instrument.moyenne or ''),
                     'faible': tools.ustr(instrument.faible or ''),
                     'tolerance': tools.ustr(instrument.tolerance or ''),
                     'afficher_classe':instrument.afficher_classe,
                     'afficher_type':instrument.afficher_type,
                     'is_database_origine_id':instrument.id,
                     }
        return famille_instrument_vals
    
    
class is_type_equipement(models.Model):
    _inherit='is.type.equipement'

    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
    
    
    @api.multi
    def write(self, vals):
        try:
            res=super(is_type_equipement, self).write(vals)
            for obj in self:
                obj.copy_other_database_type_equipement()
            return res
        except Exception as e:
            raise osv.except_osv(_('Equipement!'),
                             _('(%s).') % str(e).decode('utf-8'))


    @api.model
    def create(self, vals):
        try:
            obj=super(is_type_equipement, self).create(vals)
            obj.copy_other_database_type_equipement()
            return obj
        except Exception as e:
            raise osv.except_osv(_('Equipement!'),
                             _('(%s).') % str(e).decode('utf-8'))
            
    @api.multi
    def copy_other_database_type_equipement(self):
        cr , uid, context = self.env.args
        context = dict(context)
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for equipement in self:
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
                type_equipement_vals = self.get_type_equipement_vals(equipement, DB, USERID, USERPASS, sock)
                dest_type_equipement_ids = sock.execute(DB, USERID, USERPASS, 'is.type.equipement', 'search', [('is_database_origine_id', '=', equipement.id)], {})
                if not dest_type_equipement_ids:
                    dest_type_equipement_ids = sock.execute(DB, USERID, USERPASS, 'is.type.equipement', 'search', [('name', '=', equipement.name)], {})
                if dest_type_equipement_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.type.equipement', 'write', dest_type_equipement_ids, type_equipement_vals, {})
                    type_equipement_created_id = dest_type_equipement_ids[0]
                else:
                    type_equipement_created_id = sock.execute(DB, USERID, USERPASS, 'is.type.equipement', 'create', type_equipement_vals, {})
        return True

    @api.model
    def get_type_equipement_vals(self, equipement, DB, USERID, USERPASS, sock):
        type_equipement_vals ={
                     'name' : tools.ustr(equipement.name),
                     'is_database_origine_id':equipement.id,
                     }
        return type_equipement_vals





class is_emplacement_outillage(models.Model):
    _inherit = "is.emplacement.outillage"
    
    
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
    
    
    @api.multi
    def write(self, vals):
        try:
            res=super(is_emplacement_outillage, self).write(vals)
            for obj in self:
                obj.copy_other_database_emplacement_outillage()
            return res
        except Exception as e:
            raise osv.except_osv(_('Outillage!'),
                             _('(%s).') % str(e).decode('utf-8'))


    @api.model
    def create(self, vals):
        try:
            obj=super(is_emplacement_outillage, self).create(vals)
            obj.copy_other_database_emplacement_outillage()
            return obj
        except Exception as e:
            raise osv.except_osv(_('Outillage!'),
                             _('(%s).') % str(e).decode('utf-8'))
            
    @api.multi
    def copy_other_database_emplacement_outillage(self):
        cr , uid, context = self.env.args
        context = dict(context)
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for outillage in self:
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
                emplacement_outillage_vals = self.get_emplacement_outillage_vals(outillage, DB, USERID, USERPASS, sock)
                dest_emplacement_outillage_ids = sock.execute(DB, USERID, USERPASS, 'is.emplacement.outillage', 'search', [('is_database_origine_id', '=', outillage.id)], {})
                if not dest_emplacement_outillage_ids:
                    dest_emplacement_outillage_ids = sock.execute(DB, USERID, USERPASS, 'is.emplacement.outillage', 'search', [('name', '=', outillage.name)], {})
                if dest_emplacement_outillage_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.emplacement.outillage', 'write', dest_emplacement_outillage_ids, emplacement_outillage_vals, {})
                    emplacement_outillage_created_id = dest_emplacement_outillage_ids[0]
                else:
                    emplacement_outillage_created_id = sock.execute(DB, USERID, USERPASS, 'is.emplacement.outillage', 'create', emplacement_outillage_vals, {})
        return True

    @api.model
    def get_emplacement_outillage_vals(self, outillage, DB, USERID, USERPASS, sock):
        emplacement_outillage_vals ={
                     'name' : tools.ustr(outillage.name),
                     'is_database_origine_id':outillage.id,
                     }
        return emplacement_outillage_vals

class is_presse(models.Model):
    _inherit='is.presse'
    
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
    active = fields.Boolean('Active', default=True)
    
    @api.multi
    def write(self, vals):
        try:
            res=super(is_presse, self).write(vals)
            for obj in self:
                obj.copy_other_database_is_presse()
            return res
        except Exception as e:
            raise osv.except_osv(_('Presse!'),
                             _('(%s).') % str(e).decode('utf-8'))


    @api.model
    def create(self, vals):
        try:
            obj=super(is_presse, self).create(vals)
            obj.copy_other_database_is_presse()
            return obj
        except Exception as e:
            raise osv.except_osv(_('Presse!'),
                             _('(%s).') % str(e).decode('utf-8'))
            
    @api.multi
    def copy_other_database_is_presse(self):
        cr , uid, context = self.env.args
        context = dict(context)
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for presse in self:
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
                is_presse_vals = self.get_is_presse_vals(presse, DB, USERID, USERPASS, sock)
                dest_is_presse_ids = sock.execute(DB, USERID, USERPASS, 'is.presse', 'search', [('is_database_origine_id', '=', presse.id),
                                                                                                '|',('active','=',True),('active','=',False)], {})
                if dest_is_presse_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.presse', 'write', dest_is_presse_ids, is_presse_vals, {})
                    is_presse_created_id = dest_is_presse_ids[0]
                else:
                    is_presse_created_id = sock.execute(DB, USERID, USERPASS, 'is.presse', 'create', is_presse_vals, {})
        return True

    @api.model
    def get_is_presse_vals(self, presse, DB, USERID, USERPASS, sock):
        is_presse_vals ={
                     'name' : tools.ustr(presse.name or ''),
                     'designation':tools.ustr(presse.designation or ''),
                     'classe':tools.ustr(presse.classe or ''),
                    'emplacement':self._get_emplacement(presse, DB, USERID, USERPASS, sock),
                    'classe_commerciale':self._get_classe_commerciale(presse, DB, USERID, USERPASS, sock),
                    'puissance' : self._get_puissance(presse, DB, USERID, USERPASS, sock),
                     'puissance_reelle':tools.ustr(presse.puissance_reelle or ''),
                     'type_de_presse':tools.ustr(presse.type_de_presse or ''),
                    'constructeur': self._get_constructeur(presse, DB, USERID, USERPASS, sock),
                     'num_construceur':tools.ustr(presse.num_construceur or ''),
                     'type_commande':tools.ustr(presse.type_commande or ''),
                     'annee':tools.ustr(presse.annee or ''),
                     'energie':presse.energie,
                     'volume_tremie':tools.ustr(presse.volume_tremie or ''),
                     'volume_alimentateur':tools.ustr(presse.volume_alimentateur or ''),
                     'dimension_col_h':tools.ustr(presse.dimension_col_h or ''),
                     'dimension_col_v':tools.ustr(presse.dimension_col_v or ''),
                     'diametre_colonne':tools.ustr(presse.diametre_colonne or ''),
                     'epaisseur_moule':tools.ustr(presse.epaisseur_moule or ''),
                     'faux_plateau':presse.faux_plateau,
                     'epaisseur_faux_plateau': tools.ustr(presse.epaisseur_faux_plateau or ''),
                     'epaisseur_moule_mini':tools.ustr(presse.epaisseur_moule_mini or ''),
                     'epaisseur_moule_maxi':tools.ustr(presse.epaisseur_moule_maxi or ''),
                     'dimension_plateau_h':tools.ustr(presse.dimension_plateau_h or ''),
                     'dimension_plateau_v':tools.ustr(presse.dimension_plateau_v or ''),
                     'dimension_hors_tout_haut':tools.ustr(presse.dimension_hors_tout_haut or ''),
                     'dimension_hors_tout_bas':tools.ustr(presse.dimension_hors_tout_bas or ''),
                     'coefficient_vis':tools.ustr(presse.coefficient_vis or ''),
                     'diametre_vis':tools.ustr(presse.diametre_vis or ''),
                     'type_clapet':tools.ustr(presse.type_clapet or ''),
                     'volume_injectable':tools.ustr(presse.volume_injectable or ''),
                     'presse_matiere':tools.ustr(presse.presse_matiere or ''),
                     'course_ejection':tools.ustr(presse.course_ejection or ''),
                     'course_ouverture':tools.ustr(presse.course_ouverture or ''),
                     'diametre_centrage_moule':tools.ustr(presse.diametre_centrage_moule or ''),
                     'diametre_centrage_presse':tools.ustr(presse.diametre_centrage_presse or ''),
                     'hauteur_porte_sol':tools.ustr(presse.hauteur_porte_sol or ''),
                     'bridage_rapide':tools.ustr(presse.bridage_rapide or ''),
                     'diametre_bridage':tools.ustr(presse.diametre_bridage or ''),
                     'pas_bridage':tools.ustr(presse.pas_bridage or ''),
                     'type_huile_hydraulique':tools.ustr(presse.type_huile_hydraulique or ''),
                     'volume_reservoir':tools.ustr(presse.volume_reservoir or ''),
                     'longueur':presse.longueur,
                     'largeur':presse.largeur,
                     'hauteur':presse.hauteur,
                     'puissance_electrique': tools.ustr(presse.puissance_electrique or ''),
                     'type_huile_graissage':presse.type_huile_graissage,
                     'puissance_electrique_chauffe':tools.ustr(presse.puissance_electrique_chauffe or ''),
                     'nombre_noyau':tools.ustr(presse.nombre_noyau or ''),
                     'compensation_cosinus': presse.compensation_cosinus,
                     'nb_noyau_pf':tools.ustr(presse.nb_noyau_pf or ''),
                     'nb_noyau_pm':tools.ustr(presse.nb_noyau_pm or ''),
                     'nombre_circuit_haut':tools.ustr(presse.nombre_circuit_haut or ''),
                     'diametre_passage_buse':tools.ustr(presse.diametre_passage_buse or ''),
                     'zone_chauffe':tools.ustr(presse.zone_chauffe or ''),
                     'poids':tools.ustr(presse.poids or ''),
                     'site_id':self._get_site_id(presse, DB, USERID, USERPASS, sock),
                     'active':presse.site_id and presse.site_id.database == DB and True or False,
                     'is_database_origine_id':presse.id,
                     }
        return is_presse_vals


    @api.model
    def _get_site_id(self, presse, DB, USERID, USERPASS, sock):
        if presse.site_id:
            ids = sock.execute(DB, USERID, USERPASS, 'is.database', 'search', [('is_database_origine_id', '=', presse.site_id.id)], {})
            if ids:
                return ids[0]
        return False



    @api.model
    def _get_emplacement(self, presse, DB, USERID, USERPASS, sock):
        if presse.emplacement:
            emplacement_ids = sock.execute(DB, USERID, USERPASS, 'is.emplacement.outillage', 'search', [('is_database_origine_id', '=', presse.emplacement.id)], {})
            if not emplacement_ids:
                presse.emplacement.copy_other_database_emplacement_outillage()
                emplacement_ids = sock.execute(DB, USERID, USERPASS, 'is.emplacement.outillage', 'search', [('is_database_origine_id', '=', presse.emplacement.id)], {})
            if emplacement_ids:
                return emplacement_ids[0]
        return False
    
    @api.model
    def _get_classe_commerciale(self, presse, DB, USERID, USERPASS, sock):
        if presse.classe_commerciale:
            classe_commerciale_ids = sock.execute(DB, USERID, USERPASS, 'is.presse.classe', 'search', [('is_database_origine_id', '=', presse.classe_commerciale.id)], {})
            if not classe_commerciale_ids:
                presse.classe_commerciale.copy_other_database_presse_classe()
                classe_commerciale_ids = sock.execute(DB, USERID, USERPASS, 'is.presse.classe', 'search', [('is_database_origine_id', '=', presse.classe_commerciale.id)], {})
            if classe_commerciale_ids:
                return classe_commerciale_ids[0]
        return False

    @api.model
    def _get_puissance(self, presse, DB, USERID, USERPASS, sock):
        if presse.puissance:
            puissance_ids = sock.execute(DB, USERID, USERPASS, 'is.presse.puissance', 'search', [('is_database_origine_id', '=', presse.puissance.id)], {})
            if not puissance_ids:
                presse.puissance.copy_other_database_presse_puissance()
                puissance_ids = sock.execute(DB, USERID, USERPASS, 'is.presse.puissance', 'search', [('is_database_origine_id', '=', presse.puissance.id)], {})
            if puissance_ids:
                return puissance_ids[0]
        return False

    @api.model
    def _get_constructeur(self, presse, DB, USERID, USERPASS, sock):
        if presse.constructeur:
            constructeur_ids = sock.execute(DB, USERID, USERPASS, 'is.outillage.constructeur', 'search', [('is_database_origine_id', '=', presse.constructeur.id)], {})
            if not constructeur_ids:
                presse.constructeur.copy_other_database_outillage_constructeur()
                constructeur_ids = sock.execute(DB, USERID, USERPASS, 'is.outillage.constructeur', 'search', [('is_database_origine_id', '=', presse.constructeur.id)], {})
            if constructeur_ids:
                return constructeur_ids[0]
        return False


class is_prechauffeur(models.Model):
    _inherit='is.prechauffeur'
    
    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
    active = fields.Boolean('Active', default=True)
    
    @api.multi
    def write(self, vals):
        try:
            res=super(is_prechauffeur, self).write(vals)
            for obj in self:
                obj.copy_other_database_is_prechauffeur()
            return res
        except Exception as e:
            raise osv.except_osv(_('Prechauffeur!'),
                             _('(%s).') % str(e).decode('utf-8'))


    @api.model
    def create(self, vals):
        try:
            obj=super(is_prechauffeur, self).create(vals)
            obj.copy_other_database_is_prechauffeur()
            return obj
        except Exception as e:
            raise osv.except_osv(_('Prechauffeur!'),
                             _('(%s).') % str(e).decode('utf-8'))
            
    @api.multi
    def copy_other_database_is_prechauffeur(self):
        cr , uid, context = self.env.args
        context = dict(context)
        database_obj = self.env['is.database']
        database_lines = database_obj.search([])
        for prechauffeur in self:
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
                is_prechauffeur_vals = self.get_is_prechauffeur_vals(prechauffeur, DB, USERID, USERPASS, sock)
                dest_is_prechauffeur_ids = sock.execute(DB, USERID, USERPASS, 'is.prechauffeur', 'search', [('is_database_origine_id', '=', prechauffeur.id),
                                                                                                '|',('active','=',True),('active','=',False)], {})
                if dest_is_prechauffeur_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.prechauffeur', 'write', dest_is_prechauffeur_ids, is_prechauffeur_vals, {})
                    is_prechauffeur_created_id = dest_is_prechauffeur_ids[0]
                else:
                    is_prechauffeur_created_id = sock.execute(DB, USERID, USERPASS, 'is.prechauffeur', 'create', is_prechauffeur_vals, {})
        return True

    @api.model
    def get_is_prechauffeur_vals(self, prechauffeur, DB, USERID, USERPASS, sock):
        is_prechauffeur_vals ={
            'name' : tools.ustr(prechauffeur.name or ''),
            'presse_id':self._get_presse_id(prechauffeur, DB, USERID, USERPASS, sock), 
            'constructeur':tools.ustr(prechauffeur.constructeur or ''),
            'marque':tools.ustr(prechauffeur.marque or ''),
            'type_prechauffeur':tools.ustr(prechauffeur.type_prechauffeur or ''),
            'num_serie':tools.ustr(prechauffeur.num_serie or ''),
            'date_fabrication':prechauffeur.date_fabrication,
            'poids':prechauffeur.poids,
            'longueur':prechauffeur.longueur,
            'largeur': prechauffeur.largeur ,
            'hauteur':prechauffeur.hauteur,
            'type_fluide': prechauffeur.type_fluide ,
            'temperature_maxi': prechauffeur.temperature_maxi ,
            'puissance_installee': prechauffeur.puissance_installee ,
            'puissance_chauffe': prechauffeur.puissance_chauffe ,
            'puissance_refroidissement': prechauffeur.puissance_refroidissement ,
            'debit_maximum': prechauffeur.debit_maximum ,
            'pression_maximum':prechauffeur.pression_maximum,
            'commande_deportee': prechauffeur.commande_deportee ,
            'option_depression': prechauffeur.option_depression ,
            'mesure_debit': prechauffeur.mesure_debit ,
            'site_id':self._get_site_id(prechauffeur, DB, USERID, USERPASS, sock),
            'moule_ids':self._get_moule_ids(prechauffeur, DB, USERID, USERPASS, sock), 
            'active':prechauffeur.site_id and prechauffeur.site_id.database == DB and True or False,
            'is_database_origine_id':prechauffeur.id,
        }
        return is_prechauffeur_vals
    
    
    @api.model
    def _get_moule_ids(self, prechauffeur , DB, USERID, USERPASS, sock):
        ids = []
        for moule in prechauffeur.moule_ids:
            res = sock.execute(DB, USERID, USERPASS, 'is.mold', 'search', [('is_database_origine_id', '=', moule.id)], {})
            if res:
                ids.append(res[0])
        return [(6,0,ids)]


    @api.model
    def _get_presse_id(self, prechauffeur, DB, USERID, USERPASS, sock):
        if prechauffeur.presse_id:
            ids = sock.execute(DB, USERID, USERPASS, 'is.presse', 'search', [('is_database_origine_id', '=', prechauffeur.presse_id.id)], {})
            if ids:
                return ids[0]
        return False


    @api.model
    def _get_site_id(self, prechauffeur, DB, USERID, USERPASS, sock):
        if prechauffeur.site_id:
            ids = sock.execute(DB, USERID, USERPASS, 'is.database', 'search', [('is_database_origine_id', '=', prechauffeur.site_id.id)], {})
            if ids:
                return ids[0]
        return False

    
    @api.model
    def _get_mold_id(self, prechauffeur, DB, USERID, USERPASS, sock):
        if prechauffeur.mold_id:
            is_mold_ids = sock.execute(DB, USERID, USERPASS, 'is.mold', 'search', [('is_database_origine_id', '=', prechauffeur.mold_id.id)], {})
            if not is_mold_ids:
                prechauffeur.mold_id.copy_other_database_mold()
                is_mold_ids = sock.execute(DB, USERID, USERPASS, 'is.mold', 'search', [('is_database_origine_id', '=', prechauffeur.mold_id.id)], {})
            if is_mold_ids:
                return is_mold_ids[0]
        return False
    
 

#class is_historique_controle(models.Model):
#    _inherit='is.historique.controle'
#    
#    is_database_origine_id = fields.Integer("Id d'origine", readonly=True)
#    active = fields.Boolean('Active', default=True)
#    
#    @api.multi
#    def write(self, vals):
#        try:
#            res=super(is_historique_controle, self).write(vals)
#            for obj in self:
#                obj.copy_other_database_historique_controle()
#            return res
#        except Exception as e:
#            raise osv.except_osv(_('Historique Controle!'),
#                             _('(%s).') % str(e).decode('utf-8'))


#    @api.model
#    def create(self, vals):
#        try:
#            obj=super(is_historique_controle, self).create(vals)
#            obj.copy_other_database_historique_controle()
#            return obj
#        except Exception as e:
#            raise osv.except_osv(_('Historique Controle!'),
#                             _('(%s).') % str(e).decode('utf-8'))
#            
#    @api.multi
#    def copy_other_database_historique_controle(self):
#        cr , uid, context = self.env.args
#        context = dict(context)
#        database_obj = self.env['is.database']
#        database_lines = database_obj.search([])
#        for controle in self:
#            for database in database_lines:
#                if not database.ip_server or not database.database or not database.port_server or not database.login or not database.password:
#                    continue
#                DB = database.database
#                USERID = SUPERUSER_ID
#                DBLOGIN = database.login
#                USERPASS = database.password
#                DB_SERVER = database.ip_server
#                DB_PORT = database.port_server
#                sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/object' % (DB_SERVER, DB_PORT))
#                historique_controle_vals = self.get_historique_controle_vals(controle, DB, USERID, USERPASS, sock)
#                dest_historique_controle_ids = sock.execute(DB, USERID, USERPASS, 'is.historique.controle', 'search', [('is_database_origine_id', '=', controle.id),
#                                                                                                '|',('active','=',True),('active','=',False)], {})
#                if dest_historique_controle_ids:
#                    sock.execute(DB, USERID, USERPASS, 'is.historique.controle', 'write', dest_historique_controle_ids, historique_controle_vals, {})
#                    historique_controle_created_id = dest_historique_controle_ids[0]
#                else:
#                    historique_controle_created_id = sock.execute(DB, USERID, USERPASS, 'is.historique.controle', 'create', historique_controle_vals, {})
#        return True

#    @api.model
#    def get_historique_controle_vals(self, controle, DB, USERID, USERPASS, sock):
#        historique_controle_vals ={
#                    'plaquette_id':self._get_plaquette_id(controle, DB, USERID, USERPASS, sock),
#                    'instrument_id':self._get_instrument_id(controle, DB, USERID, USERPASS, sock),
#                    'gabarit_id':self._get_gabarit_id(controle, DB, USERID, USERPASS, sock),
#                    'date_controle':controle.date_controle,
#                    'affectation':tools.ustr(controle.affectation or ''),
#                    'operation':controle.operation,
#                    'organisme' : tools.ustr(controle.organisme or ''),
#                    'resultat':tools.ustr(controle.resultat or ''),
#                    'commentaire': tools.ustr(controle.commentaire or ''),
#                    'classe': tools.ustr(controle.classe or ''),
#                    
#                    'active':controle.site_id and controle.site_id.database == DB and True or False,
#                    'is_database_origine_id':controle.id,
#                     }
#        return historique_controle_vals
    
#    @api.model
#    def _get_plaquette_id(self, controle, DB, USERID, USERPASS, sock):
#        if controle.plaquette_id:
#            is_plaquette_ids = sock.execute(DB, USERID, USERPASS, 'is.plaquette.etalon', 'search', [('is_database_origine_id', '=', controle.plaquette_id.id)], {})
#            if not is_plaquette_ids:
#                controle.plaquette_id.copy_other_database_plaquette_etalon()
#                is_plaquette_ids = sock.execute(DB, USERID, USERPASS, 'is.plaquette.etalon', 'search', [('is_database_origine_id', '=', controle.plaquette_id.id)], {})
#            if is_plaquette_ids:
#                return is_plaquette_ids[0]
#        return False

#    @api.model
#    def _get_instrument_id(self, controle, DB, USERID, USERPASS, sock):
#        if controle.instrument_id:
#            is_instrument_ids = sock.execute(DB, USERID, USERPASS, 'is.instrument.mesure', 'search', [('is_database_origine_id', '=', controle.instrument_id.id)], {})
#            if not is_instrument_ids:
#                controle.instrument_id.copy_other_database_instrument_mesure()
#                is_instrument_ids = sock.execute(DB, USERID, USERPASS, 'is.instrument.mesure', 'search', [('is_database_origine_id', '=', controle.instrument_id.id)], {})
#            if is_instrument_ids:
#                return is_instrument_ids[0]
#        return False
#    
#    @api.model
#    def _get_gabarit_id(self, controle, DB, USERID, USERPASS, sock):
#        if controle.gabarit_id:
#            is_gabarit_ids = sock.execute(DB, USERID, USERPASS, 'is.gabarit.controle', 'search', [('is_database_origine_id', '=', controle.gabarit_id.id)], {})
#            if not is_gabarit_ids:
#                controle.gabarit_id.copy_other_database_gabarit_controle()
#                is_gabarit_ids = sock.execute(DB, USERID, USERPASS, 'is.gabarit.controle', 'search', [('is_database_origine_id', '=', controle.gabarit_id.id)], {})
#            if is_gabarit_ids:
#                return is_gabarit_ids[0]
#        return False


