from openerp.exceptions import except_orm
from openerp import models, fields, api, _



class shedule_cout_article_report(models.TransientModel):
    _name="shedule.cout.article.report"

    next_call = fields.Datetime('Set Next Execution Time')
    
    @api.multi
    def set_sheduler_cout_article(self):
        data_obj = self.env['ir.model.data']
        model, res_id = data_obj.get_object_reference('is_plastigray', 'cron_cout_article_report')
        if res_id:
            sheduler_brw = self.env['ir.cron'].browse(res_id)
            sheduler_brw.write({'active':True, 'nextcall':self.next_call, 'numbercall':1})
        return True
    
    