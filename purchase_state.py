# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning
from openerp.addons.purchase import purchase

purchase.purchase_order.STATE_SELECTION += [('demande_achat','Demande d\'achat')]

class purchase_order(models.Model):
    _inherit = "purchase.order"
    
    def do_demande_achat(self, cr, uid, ids, context=None):
        purchase = self.browse(cr, uid, ids[0],context=context)
        if not context:
            context= {}
        ir_model_data = self.pool.get('ir.model.data')
        try:
            template_id = ir_model_data.get_object_reference(cr, uid, 'purchase', 'email_template_edi_purchase_done')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference(cr, uid, 'mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False 
        ctx = dict(context)
        if context.get('confirm_demande_achat',False):
            partner_ids = purchase.is_demandeur_id and [purchase.is_demandeur_id.partner_id.id] or []
            ctx.update({'confirm_demande_achat':True})
        else:
            partner_ids = purchase.is_demandeur_id and purchase.is_demandeur_id.is_acheteur_id and [purchase.is_demandeur_id.is_acheteur_id.partner_id.id] or []
            ctx.update({'demande_achat':True})
            
        ctx.update({
            'default_model': 'purchase.order',
            'default_res_id': ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'default_partner_ids':partner_ids
        })
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

class mail_compose_message(models.Model):
    _inherit = "mail.compose.message"
    
    
    def onchange_template_id(self, cr, uid, ids, template_id, composition_mode, model, res_id, context=None):
        res = super(mail_compose_message,self).onchange_template_id(cr, uid, ids, template_id, composition_mode, model, res_id, context=context)
        if not context:
            context = {}
        if context.get('demande_achat',False) or context.get('confirm_demande_achat',False):
            if res.get('value',{}).get('partner_ids',[]):
                del res['value']['partner_ids']
        return res
    
    def send_mail(self, cr, uid, ids, context=None):
        context = context or {}
        if context.get('demande_achat',False) and context.get('default_model') == 'purchase.order' and context.get('default_res_id'):
            context = dict(context, mail_post_autofollow=True)
            self.pool.get('purchase.order').signal_workflow(cr, uid, [context['default_res_id']], 'demande_achat')
        elif context.get('confirm_demande_achat',False) and context.get('default_model') == 'purchase.order' and context.get('default_res_id'):
            ontext = dict(context, mail_post_autofollow=True)
            self.pool.get('purchase.order').signal_workflow(cr, uid, [context['default_res_id']], 'confirm_demande_achat')
        return super(mail_compose_message, self).send_mail(cr, uid, ids, context=context)
    
    
class res_users(models.Model):
    _inherit = "res.users"
    
    is_acheteur_id = fields.Many2one('res.users','Acheteur')

    