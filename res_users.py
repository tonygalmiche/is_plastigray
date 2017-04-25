from openerp import models,fields,api, SUPERUSER_ID
from openerp.tools.translate import _

from openerp.http import request


class is_service(models.Model):
    _name = 'is.service'
    _description = "Service"
    
    name        = fields.Char('Service', required=True)


class res_users(models.Model):
    _inherit = "res.users"

    is_service_id = fields.Many2one('is.service', 'Service')
    is_adresse_ip = fields.Char('Adresse IP')


    def _login(self, db, login, password):
        """Permet d'ajouter l'adresse IP de la personne qui se connecte
        cela est utilise par les programmes externes"""

        user_id = super(res_users, self)._login(db, login, password)
        ip=request.httprequest.environ['REMOTE_ADDR'] 
        cr = self.pool.cursor()
        cr.autocommit(True)
        if user_id and ip:
            res=cr.execute("UPDATE res_users SET is_adresse_ip='"+str(ip)+"' WHERE id="+str(user_id))
            cr.close()
        return user_id


class res_groups(models.Model):
    _inherit = "res.groups"
    _order='category_id,name'

    active = fields.Boolean('Actif')

    _defaults = {
        'active': True,
    }


