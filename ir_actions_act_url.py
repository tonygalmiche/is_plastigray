# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
from openerp.http import request


class ir_actions_act_url(models.Model):
    _inherit = 'ir.actions.act_url'


    def get_soc(self, cr, uid):
        user = self.pool['res.users'].browse(cr, uid, [uid])[0]
        soc  = user.company_id.partner_id.is_code
        return soc


    def read(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
        if not context: context = {}
        results = super(ir_actions_act_url, self).read(cr, uid, ids, fields=fields, context=context, load=load)
        if load=='_classic_read' and len(ids) == 1:

                if results[0]['name']==u'is_url_planning_action':
                    soc=self.get_soc(cr,uid)
                    ip   = request.httprequest.environ['REMOTE_ADDR'] 
                    url='http://odoo/odoo-erp/planning/?soc='+str(soc)+'&uid='+str(uid)
                    results[0].update({'url': url})

                if results[0]['name']==u'is_url_analyse_cbn_action':
                    soc=self.get_soc(cr,uid)
                    ip   = request.httprequest.environ['REMOTE_ADDR'] 
                    url='http://odoo/odoo-erp/cbn/Sugestion_CBN.php?Soc='+str(soc)+'&product_id=&uid='+str(uid)
                    results[0].update({'url': url})

                if results[0]['name']==u'is_url_pic_3_ans_action':
                    soc=self.get_soc(cr,uid)
                    ip   = request.httprequest.environ['REMOTE_ADDR'] 
                    url='http://odoo/odoo-erp/analyses/pic-3-ans.php?Soc='+str(soc)+'&uid='+str(uid)
                    results[0].update({'url': url})

                if results[0]['name']==u'is_url_theia':
                    soc=self.get_soc(cr,uid)
                    url='http://odoo-cpi1'
                    if soc=='3':
                        url='http://odoo-theia3'
                    if soc=='4':
                        url='http://odoo-theia4'
                    results[0].update({'url': url})

                if results[0]['name']==u'is_url_theia_suivi_prod':
                    soc=self.get_soc(cr,uid)
                    url='http://raspberry-cpi/atelier.php?soc='+soc
                    results[0].update({'url': url})

                if results[0]['name']==u'is_url_theia_rebuts':
                    soc=self.get_soc(cr,uid)
                    url='http://odoo/odoo-cpi/rebuts.php?soc='+soc
                    results[0].update({'url': url})

                if results[0]['name']==u'is_url_theia_trs':
                    soc=self.get_soc(cr,uid)
                    url='http://odoo/odoo-cpi/trs.php?soc='+soc
                    results[0].update({'url': url})

        return results


