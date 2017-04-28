# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
from openerp.http import request


class ir_actions_act_url(models.Model):
    _inherit = 'ir.actions.act_url'


    def read(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
        if not context: context = {}
        results = super(ir_actions_act_url, self).read(cr, uid, ids, fields=fields, context=context, load=load)
        if load=='_classic_read' and len(ids) == 1:
                if results[0]['name']==u'is_url_planning_action':
                    user = self.pool['res.users'].browse(cr, uid, [uid], context=context)[0]
                    soc  = user.company_id.partner_id.is_code
                    ip   = request.httprequest.environ['REMOTE_ADDR'] 
                    url='http://odoo/odoo-erp/planning/?soc='+str(soc)+'&uid='+str(uid)
                    results[0].update({'url': url})
        return results



