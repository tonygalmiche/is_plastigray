# -*- coding: utf-8 -*-

from openerp import api, fields, models, _
from openerp.exceptions import ValidationError, Warning
import xmlrpclib
from openerp.osv import osv


#TODO
# Si le client ou le chef de projet n'existe pas, il faut le créer => Et mettre en relation les bons id ce qui n'est pas le cas actuellement

#- Cela devra également fonctionner lors de la duplication d'un objet
#- Ajouter un champ 'Société' pour indiquer les bases de données dans lesquelles cet objet sera copié
#- Ajouter un champ 'active' pour désactier l'objet dans une société ou il n'apparait plus


class is_database(models.Model):
    _name = 'is.database'
    _order='name'

    name                   = fields.Char('Site'           , required=True)
    ip_server              = fields.Char('Adresse IP'     , required=False)
    port_server            = fields.Integer('Port'        , required=False)
    database               = fields.Char('Base de données', required=False)
    login                  = fields.Char('Login'          , required=False)
    password               = fields.Char('Mot de passe'   , required=False)
    is_database_origine_id = fields.Integer("Id d'origine (is.database)", readonly=True)

    @api.multi
    def copy_other_database(self, obj):
        try:
            cr , uid, context = self.env.args
            class_name=obj.__class__.__name__
            database_lines = self.env['is.database'].search([])
            for database in database_lines:
                if database.database:
                    DB = database.database
                    USERID = uid
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
                        if ids:
                            sock.execute(DB, USERID, USERPASS, class_name, 'write', ids, vals, {})
                            created_id = ids[0]
                        else:
                            created_id = sock.execute(DB, USERID, USERPASS, class_name, 'create', vals, {})
        except Exception as e:
            raise osv.except_osv(_('Recursive Client!'),
                             _('(%s).') % e)
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
        ids = sock.execute(DB, USERID, USERPASS, 'is.secteur.activite', 'search', [('name', '=', obj.name)], {})
        if ids:
            return ids[0]
        else:
            vals = {'name':obj.name}
            new_id = sock.execute(DB, USERID, USERPASS, 'is.secteur.activite', 'create', vals, {})
            return new_id

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
            raise osv.except_osv(_('Client!'),
                             _('(%s).') % e)

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
        is_type_contact_ids = sock.execute(DB, USERID, USERPASS, 'is.type.contact', 'search', [('name', '=', obj.name)], {})
        if is_type_contact_ids:
            return is_type_contact_ids[0]
        else:
            vals = {'name':obj.name}
            is_type_contact = sock.execute(DB, USERID, USERPASS, 'is.type.contact', 'create', vals, {})
            return is_type_contact
        
    def get_is_incoterm(self, obj, DB, USERID, USERPASS, sock):
        is_incoterm_ids = sock.execute(DB, USERID, USERPASS, 'stock.incoterms', 'search', [('name', '=', obj.name)], {})
        if is_incoterm_ids:
            return is_incoterm_ids[0]
        else:
            vals = {'name':obj.name,'code':obj.code, 'active':obj.active}
            is_incoterm = sock.execute(DB, USERID, USERPASS, 'stock.incoterms', 'create', vals, {})
            return is_incoterm
        
    def get_is_segment_achat(self, obj , DB, USERID, USERPASS, sock):
        is_segment_achat_ids = sock.execute(DB, USERID, USERPASS, 'is.segment.achat', 'search', [('name', '=', obj.name)], {})
        if is_segment_achat_ids:
            return is_segment_achat_ids[0]
        else:
            vals = {'name':obj.name,'description':obj.description, }
#             'family_line':[(6,0,[self.get_is_famille_achat_ids(is_famille , DB, USERID, USERPASS, sock) for is_famille in obj.family_line])]
            is_segment_achat = sock.execute(DB, USERID, USERPASS, 'is.segment.achat', 'create', vals, {})
            return is_segment_achat
        
    def get_is_famille_achat_ids(self, obj_ids , DB, USERID, USERPASS, sock):
        lst_is_famille_achat_ids = []
        for obj in obj_ids:
            famille_achat_ids = sock.execute(DB, USERID, USERPASS, 'is.famille.achat', 'search', [('name', '=', obj.name)], {})
            if famille_achat_ids:
                lst_is_famille_achat_ids.append(famille_achat_ids[0])
            else:
                vals = {'name':obj.name,'description':obj.description, 'segment_id':self.get_is_segment_achat(obj.segment_id , DB, USERID, USERPASS, sock)}
                is_famille_achat = sock.execute(DB, USERID, USERPASS, 'is.famille.achat', 'create', vals, {})
                lst_is_famille_achat_ids.append(is_famille_achat)
            return [(6,0,lst_is_famille_achat_ids)]
        
    def get_is_site_livre_ids(self, obj_ids , DB, USERID, USERPASS, sock):
        lst_site_livre_ids = []
        for obj in obj_ids:
            is_site_livre_ids = sock.execute(DB, USERID, USERPASS, 'is.site', 'search', [('name', '=', obj.name)], {})
            if is_site_livre_ids:
                lst_site_livre_ids.append(is_site_livre_ids[0])
            else:
                vals = {'name':obj.name}
                lst_site_livre_id = sock.execute(DB, USERID, USERPASS, 'is.site', 'create', vals, {})
                lst_site_livre_ids.append(lst_site_livre_id)
        return [(6,0,lst_site_livre_ids)]
    
    def get_is_transmission_cde(self, obj, DB, USERID, USERPASS, sock):
        is_transmission_cde_ids = sock.execute(DB, USERID, USERPASS, 'is.transmission.cde', 'search', [('name', '=', obj.name)], {})
        if is_transmission_cde_ids:
            return is_transmission_cde_ids[0]
        else:
            vals = {'name':obj.name}
            is_transmission_cde = sock.execute(DB, USERID, USERPASS, 'is.transmission.cde', 'create', vals, {})
            return is_transmission_cde
    
    def get_is_norme(self, obj, DB, USERID, USERPASS, sock):
        is_norme_ids = sock.execute(DB, USERID, USERPASS, 'is.norme.certificats', 'search', [('name', '=', obj.name)], {})
        if is_norme_ids:
            return is_norme_ids[0]
        else:
            vals = {'name':obj.name}
            is_norme = sock.execute(DB, USERID, USERPASS, 'is.norme.certificats', 'create', vals, {})
            return is_norme
    
    def get_is_certifications(self, obj_ids, DB, USERID, USERPASS, sock):
        lst_is_certifications = []
        for obj in obj_ids:
            is_certifications_ids = sock.execute(DB, USERID, USERPASS, 'is.certifications.qualite', 'search', [('is_norme.name', '=', obj.is_norme.name)], {})
            if is_certifications_ids:
                lst_is_certifications.append(is_certifications_ids[0])
            else:
                vals = {'is_norme':obj.is_norme and self.get_is_norme(obj.is_norme, DB, USERID, USERPASS, sock) or False,
                        'is_date_validation':obj.is_date_validation,
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
            'name': partner.name,
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
            
            
            'is_transporteur_id' : partner.is_transporteur_id and self.get_is_transporteur_id(partner.is_transporteur_id, DB, USERID, USERPASS, sock) or False,
            'is_delai_transport':partner.is_delai_transport,
            'is_certificat_matiere' :  partner.is_certificat_matiere,
            'is_import_function'    :  partner.is_import_function,
            'is_raison_sociale2'    :  partner.is_raison_sociale2,
            'is_code'               :  partner.is_code,
            'is_adr_code'           :  partner.is_adr_code,
            'is_rue3'               :  partner.is_rue3,
            'is_type_contact'       :  partner.is_type_contact and self.get_is_type_contact(partner.is_type_contact , DB, USERID, USERPASS, sock) or False,
            'is_adr_groupe'         :  partner.is_adr_groupe,
            'is_cofor'              :  partner.is_cofor,
	        'is_incoterm'           :  partner.is_incoterm and self.get_is_incoterm(partner.is_incoterm , DB, USERID, USERPASS, sock) or False,        
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
            'is_type_cde_fournisseur': partner.is_type_cde_fournisseur,
            'is_database_line_ids'   : self.get_is_database_line_ids(partner, DB, USERID, USERPASS, sock) or False,
            'active'                 : True
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

    is_database_origine_id = fields.Integer("Id d'origine (is.database)", readonly=True, select=True)
    is_database_line_ids = fields.Many2many('is.database','partner_database_rel','partner_id','database_id', string="Sites")

    @api.multi
    def write(self, vals):
        try:
            for obj in self:
                res=super(res_partner, self).write(vals)
                self.env['is.database'].copy_other_database(obj)
                return res
        except Exception as e:
            raise osv.except_osv(_('Client!'),
                             _('(%s).') % e)

    @api.model
    def create(self, vals):
        try:
            obj=super(res_partner, self).create(vals)
            self.env['is.database'].copy_other_database(obj)
        except Exception as e:
            raise osv.except_osv(_('Client!'),
                             _('(%s).') % e)
        return obj


class is_mold_project(models.Model):
    _inherit = 'is.mold.project'
 
    is_database_origine_id = fields.Integer("Id d'origine (is.database)", readonly=True)

    @api.multi
    def write(self, vals):
        try:
            res=super(is_mold_project, self).write(vals)
            for obj in self:
                obj.copy_other_database_project()
            return res
        except Exception as e:
            raise osv.except_osv(_('Project!'),
                             _('(%s).') % e)

    @api.model
    def create(self, vals):
        try:
            obj=super(is_mold_project, self).create(vals)
            obj.copy_other_database_project()
            return obj
        except Exception as e:
            raise osv.except_osv(_('Project!'),
                             _('(%s).') % e)
    
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
                USERID = uid
                DBLOGIN = database.login
                USERPASS = database.password
                DB_SERVER = database.ip_server
                DB_PORT = database.port_server
                sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/object' % (DB_SERVER, DB_PORT))
                project_vals = self.get_project_vals(project, DB, USERID, USERPASS, sock)
                dest_project_ids = sock.execute(DB, USERID, USERPASS, 'is.mold.project', 'search', [('is_database_origine_id', '=', project.id)], {})
                if dest_project_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.mold.project', 'write', dest_project_ids, project_vals, {})
                    project_created_id = dest_project_ids[0]
                else:
                    project_created_id = sock.execute(DB, USERID, USERPASS, 'is.mold.project', 'create', project_vals, {})
        return True


    @api.model
    def get_project_vals(self, project, DB, USERID, USERPASS, sock):
        project_vals = {
        'name': project.name,
        'client_id' : self._get_client_id(project, DB, USERID, USERPASS, sock),
        'chef_projet_id' : self._get_chef_projet_id(project, DB, USERID, USERPASS, sock),
        'mold_ids': self._get_mold_ids(project, DB, USERID, USERPASS, sock),
        'is_database_origine_id':project.id
        }
        return project_vals

    @api.model
    def _get_client_id(self, project, DB, USERID, USERPASS, sock):
        if project.client_id:
            client_ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', project.client_id.id),'|',('active','=',True),('active','=',False)], {})
            if not client_ids:
                self.env['is.database'].copy_other_database( project.client_id)
                client_ids = sock.execute(DB, USERID, USERPASS, 'res.partner', 'search', [('is_database_origine_id', '=', project.client_id.id),'|',('active','=',True),('active','=',False)], {})
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
    
    is_database_origine_id = fields.Integer("Id d'origine (is.database)", readonly=True)

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
                USERID = uid
                DBLOGIN = database.login
                USERPASS = database.password
                DB_SERVER = database.ip_server
                DB_PORT = database.port_server
                sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/object' % (DB_SERVER, DB_PORT))
                dossierf_vals = self.get_dossierf_vals(dossierf, DB, USERID, USERPASS, sock)
                dest_dossierf_ids = sock.execute(DB, USERID, USERPASS, 'is.dossierf', 'search', [('is_database_origine_id', '=', dossierf.id)], {})
                if dest_dossierf_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.dossierf', 'write', dest_dossierf_ids, dossierf_vals, {})
                    dossierf_created_id = dest_dossierf_ids[0]
                else:
                    dossierf_created_id = sock.execute(DB, USERID, USERPASS, 'is.dossierf', 'create', dossierf_vals, {})
        return True
    
    
    @api.model
    def get_dossierf_vals(self, dossierf, DB, USERID, USERPASS, sock):
        dossierf_vals = {
            'name': dossierf.name,
            'designation':dossierf.designation,
            'project':self._get_project(dossierf, DB, USERID, USERPASS, sock),
            'mold_ids': self._get_mold_ids(dossierf, DB, USERID, USERPASS, sock),
            'is_database_origine_id':dossierf.id,
        
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

class is_mold(models.Model):
    _inherit = 'is.mold'

    is_database_origine_id = fields.Integer("Id d'origine (is.database)", readonly=True)


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
                USERID = uid
                DBLOGIN = database.login
                USERPASS = database.password
                DB_SERVER = database.ip_server
                DB_PORT = database.port_server
                sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/object' % (DB_SERVER, DB_PORT))
                mold_vals = self.get_mold_vals(mold, DB, USERID, USERPASS, sock)
                dest_mold_ids = sock.execute(DB, USERID, USERPASS, 'is.mold', 'search', [('is_database_origine_id', '=', mold.id)], {})
                if dest_mold_ids:
                    sock.execute(DB, USERID, USERPASS, 'is.mold', 'write', dest_mold_ids, mold_vals, {})
                    mold_created_id = dest_mold_ids[0]
                else:
                    mold_created_id = sock.execute(DB, USERID, USERPASS, 'is.mold', 'create', mold_vals, {})
        return True


    @api.model
    def get_mold_vals(self, mold, DB, USERID, USERPASS, sock):
        mold_vals = {
        'name': mold.name,
        'designation' : mold.designation,
        'project' : self._get_project(mold, DB, USERID, USERPASS, sock),
        'dossierf_id': self._get_dossierf_id(mold, DB, USERID, USERPASS, sock),
        'nb_empreintes': mold.nb_empreintes,
        'moule_a_version': mold.moule_a_version,
        'date_creation':mold.date_creation,
        'date_fin':mold.date_fin,
        'mouliste_id':self._get_mouliste_id(mold, DB, USERID, USERPASS, sock),
        'carcasse': mold.carcasse,
        'emplacement':mold.emplacement,
        'is_database_origine_id':mold.id,
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
