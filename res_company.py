# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _



class res_company(models.Model):
    _inherit = 'res.company'

    is_mysql_pwd    = fields.Char('Mot de passe MySQL')
    is_dynacase_pwd = fields.Char('Mot de passe Dynacase')
    is_cpta_pwd     = fields.Char('Mot de passe AS400 CPTA')
    is_logo         = fields.Binary("Logo", help="Logo utilisé dans les documents (BL, facures,..)")
    bg_color        = fields.Char('Background color')
    text_color      = fields.Char('Text color')
    is_nb_threads   = fields.Integer('Nombre de coeurs à utiliser dans les programmes', default=1)

    is_url_intranet_odoo  = fields.Char('URL Intranet Odoo' , default='http://odoo')
    is_url_intranet_theia = fields.Char('URL Intranet THEIA', default='http://raspberry-cpi')
    is_url_odoo_theia     = fields.Char('URL Odoo THEIA')

    is_acheteur_id               = fields.Many2one('res.users', 'Acheteur', help=u"Utilisé en particulier pour transformer les SA en DAS")
    is_gest_demande_transport_id = fields.Many2one('res.users', 'Gestionnaire des demandes de transport', help=u"Utilisé pour envoyer un mail lors de la création d'une demande de transport")

    is_base_principale = fields.Boolean('Base principale (Primaire)', help="Cette case permet de masquer certains champs sur les bases répliquées si elle n'est pas cochée")

    is_code_societe      = fields.Char('Code société')
    is_dest_bilan_of_ids = fields.Many2many('res.users', 'is_res_company_users_rel', 'res_company_id','user_id', string="Destinataires du bilan de fin d'OF")
    is_cout_ctrl_qualite = fields.Float(u"Coût horaire vendu contrôle qualité", digits=(12, 2))
