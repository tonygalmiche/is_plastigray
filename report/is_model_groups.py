# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_model_groups(models.Model):
    _name='is.model.groups'
    _order='service,login,category,group'
    _auto = False

    model_id        = fields.Char('Modèle Id')
    model_name      = fields.Char('Modèle')
    perm_read       = fields.Boolean('Lire')
    perm_write      = fields.Boolean('Ecrire')
    perm_create     = fields.Boolean('Créer')
    perm_unlink     = fields.Boolean('Supp')
    user_id         = fields.Many2one('res.users', 'Utilisateur')
    email           = fields.Char('Courriel')
    login           = fields.Char('Login')
    service         = fields.Char('Service')
    group_id        = fields.Many2one('res.groups', 'Groupe Id')
    group           = fields.Char('Groupe')
    category        = fields.Char('Application')
    active_user     = fields.Boolean('Utilisateur actif')
    active_group    = fields.Boolean('Group actif')



    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_model_groups')
        cr.execute("""
            CREATE OR REPLACE view is_model_groups AS (
                select  row_number() over(order by ru.id, rg.id) as id,
                        im.model as model_id,
                        im.name  as model_name,
                        ima.perm_read,
                        ima.perm_write,
                        ima.perm_create,
                        ima.perm_unlink,
                        ru.id as user_id, 
                        rp.email, 
                        ru.login, 
                        s.name    as service, 
                        rg.name   as group,
                        rg.id     as group_id, 
                        imc.name  as category,
                        ru.active as active_user,
                        rg.active as active_group
                from ir_model_access ima inner join ir_model                im on ima.model_id=im.id 
                                         inner join res_groups              rg on ima.group_id=rg.id
                                         inner join res_groups_users_rel  rgur on rg.id=rgur.gid
                                         inner join res_users               ru on rgur.uid=ru.id
                                         inner join res_partner             rp on ru.partner_id=rp.id
                                  left outer join ir_module_category       imc on rg.category_id=imc.id
                                  left outer join is_service                s  on ru.is_service_id=s.id
                order by rp.name
            )
        """)

