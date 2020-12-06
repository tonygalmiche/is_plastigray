# -*- coding: utf-8 -*-
from openerp import models,fields,api


class calendar_event(models.Model):
    _inherit = 'calendar.event'

    is_project_id = fields.Many2one('is.mold.project', 'Projet')
    is_partner_id = fields.Many2one('res.partner'    , 'Client')


    @api.onchange('is_project_id')
    def _onchange_project_id(self):
        self.is_partner_id = self.is_project_id.client_id.id
