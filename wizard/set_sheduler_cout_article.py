# -*- coding: utf-8 -*-

from openerp.exceptions import except_orm
from openerp import models, fields, api, _
from openerp.exceptions import Warning
import pytz
import datetime
from openerp import tools



def _next_call():
    now=datetime.datetime.now()
    return now.strftime('%Y-%m-%d 20:00:00')




class shedule_cout_article_report(models.TransientModel):
    _name="shedule.cout.article.report"

    next_call = fields.Datetime("Heure d'exécution", required=True)

    _defaults = {
        'next_call': lambda *a: _next_call(),
    }


    @api.multi
    def set_sheduler_cout_article(self):




        user = self.env['res.users'].browse(self._uid)
        data_obj = self.env['ir.model.data']
        model, res_id = data_obj.get_object_reference('is_plastigray', 'cron_cout_article_report')
        if res_id:
            sheduler_brw = self.env['ir.cron'].browse(res_id)
            if sheduler_brw.active:
                utc = sheduler_brw.nextcall
                datetime_format = tools.misc.DEFAULT_SERVER_DATETIME_FORMAT
                from_zone=pytz.utc
                to_zone = self.env.user.tz
                user_tz = self.env.user.tz or pytz.utc
                local = pytz.timezone(user_tz)
                display_date_result = datetime.datetime.strftime(pytz.utc.localize(datetime.datetime.strptime(utc, datetime_format)).astimezone(local),u"%d/%m/%Y à %H:%M") 
                raise Warning(u"Cette action est déjà plannifiée le "+display_date_result)

            sheduler_brw.sudo().write({
                'active':True, 
                'nextcall':self.next_call, 'numbercall':1,
                'user_id': self._uid,
            })
        return True
    
    
