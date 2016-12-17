# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_users_groups(models.Model):
    _name='is.users.groups'
    _order='service,login,category,group'
    _auto = False

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
        tools.drop_view_if_exists(cr, 'is_users_groups')
        cr.execute("""
            CREATE OR REPLACE view is_users_groups AS (
                select  row_number() over(order by ru.id, rg.id) as id,
                        ru.id as user_id, 
                        rp.email, 
                        ru.login, 
                        s.name    as service, 
                        rg.name   as group,
                        rg.id     as group_id, 
                        imc.name  as category,
                        ru.active as active_user,
                        rg.active as active_group
                from res_users ru inner join res_partner                 rp on ru.partner_id=rp.id
                                  left outer join res_groups_users_rel rgur on ru.id=rgur.uid
                                  left outer join res_groups             rg on rgur.gid=rg.id
                                  left outer join ir_module_category    imc on rg.category_id=imc.id
                                  left outer join is_service             s  on ru.is_service_id=s.id
                order by rp.name
            )
        """)

