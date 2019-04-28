# -*- coding: utf-8 -*-

from openerp import models,fields,api, SUPERUSER_ID
from openerp.tools.translate import _
from openerp.http import request


class is_res_users(models.Model):
    _name = 'is.res.users'
    _order= 'heure_connexion desc'

    user_id         = fields.Many2one('res.users', 'Utilisateur', select=True)
    heure_connexion = fields.Datetime('Heure de connexion'      , select=True)
    adresse_ip      = fields.Char('Adresse IP'                  , select=True)


class is_service(models.Model):
    _name = 'is.service'
    _description = "Service"
    
    name        = fields.Char('Service', required=True)


class res_users(models.Model):
    _inherit = "res.users"

    is_site_id    = fields.Many2one("is.database", "Site de production", help=u"Ce champ est utilisé en particulier pour la gestion des OT dans odoo0")
    is_service_id = fields.Many2one('is.service', 'Service')
    is_adresse_ip = fields.Char('Adresse IP', help='Adresse IP de cet utilisateur pour lui donner des accès spcécifiques dans THEIA')


    def _login(self, db, login, password):
        """Permet d'ajouter l'adresse IP de la personne qui se connecte
        cela est utilise par les programmes externes"""

        user_id = super(res_users, self)._login(db, login, password)

        print request
        print request.httprequest
        print request.httprequest.environ


#        ip=request.httprequest.environ.get('REMOTE_ADDR',False)
#        if ip:
#            cr = self.pool.cursor()
#            cr.autocommit(True)
#            if user_id and ip:
#                SQL="""
#                    INSERT INTO is_res_users (user_id, heure_connexion, adresse_ip)
#                    VALUES ("""+str(user_id)+""", now() at time zone 'UTC', '"""+str(ip)+"""')
#                """
#                res=cr.execute(SQL)
#                #res=cr.execute("UPDATE res_users SET is_adresse_ip='"+str(ip)+"' WHERE id="+str(user_id))
#                cr.close()
        return user_id


class res_groups(models.Model):
    _inherit = "res.groups"
    _order='category_id,name'

    active = fields.Boolean('Actif')

    _defaults = {
        'active': True,
    }


