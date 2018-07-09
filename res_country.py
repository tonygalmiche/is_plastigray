# -*- coding: utf-8 -*-

from openerp import models,fields,api

class res_country(models.Model):
    _inherit = 'res.country'

    is_jour_ferie_ids = fields.One2many('is.jour.ferie.country', 'country_id', u"Jours fériés")


class is_jour_ferie_country(models.Model):
    _name='is.jour.ferie.country'
    _order='name'

    name       = fields.Date("Jours fériés", required=True, select=True)
    country_id = fields.Many2one('res.country', 'Pays')


