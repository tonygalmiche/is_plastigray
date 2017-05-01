# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning
from math import *
from openerp.addons.purchase import purchase


purchase.purchase_order.STATE_SELECTION += [('demande_achat','Demande d\'achat')]

class purchase_order_line(models.Model):
    _inherit = "purchase.order.line"

    is_justification = fields.Char("Justification", help="Ce champ est obligatoire si l'article n'est pas renseigné ou le prix à 0")


    @api.multi
    def onchange_product_id(self, pricelist_id, product_id, qty, uom_id,
            partner_id, date_order=False, fiscal_position_id=False, date_planned=False,
            name=False, price_unit=False, state='draft'):
        res = super(purchase_order_line, self).onchange_product_id(pricelist_id, product_id, qty, uom_id,
            partner_id, date_order=date_order, fiscal_position_id=fiscal_position_id, date_planned=date_planned,
            name=name, price_unit=price_unit, state=state)
        if product_id:
            product = self.env['product.product'].browse(product_id)
            product_uom_obj = self.env['product.uom']
            if not uom_id:
                uom_id=product.uom_po_id.id
            qty = product_uom_obj._compute_qty(uom_id, qty, product.uom_id.id)
            lot      = product.lot_mini
            multiple = product.multiple
            if multiple==0:
                multiple=1
            if qty<lot:
                qty=lot
            else:
                delta=round(qty-lot,8)
                qty=lot+multiple*ceil(delta/multiple)
            qty = product_uom_obj._compute_qty(product.uom_id.id, qty, uom_id)
            res['value'].update({'product_qty': qty })
        return res



class purchase_order(models.Model):
    _inherit = "purchase.order"

    is_num_da            = fields.Char("N°Demande d'achat")
    is_document          = fields.Char("Document (N° de dossier)")
    is_demandeur_id      = fields.Many2one('res.users', 'Demandeur')
    is_date_confirmation = fields.Date("Date de confirmation du fournisseur")
    is_commentaire       = fields.Text("Commentaire")
    is_acheteur_id       = fields.Many2one('res.users','Acheteur')

    _defaults = {
        'is_demandeur_id': lambda obj, cr, uid, ctx=None: uid,
    }


    @api.multi
    def actualiser_prix_commande(self):
        for obj in self:
            for line in obj.order_line:
                res = line.onchange_product_id(
                    obj.pricelist_id.id, 
                    line.product_id.id, 
                    line.product_qty, 
                    line.product_uom.id,
                    obj.partner_id.id, 
                    date_order   = line.date_planned+u' 12:00:00',
                    date_planned = line.date_planned,
                )
                price=res['value']['price_unit']
                if not price:
                    raise Warning(u"Modification non éffectuée, car prix non trouvé")
                line.price_unit=price


    @api.multi
    def actualiser_taxes_commande(self):
        for obj in self:
            order_line_obj = self.env['purchase.order.line']
            obj.fiscal_position = obj.partner_id.property_account_position.id
            obj.payment_term_id = obj.partner_id.property_supplier_payment_term.id

            for line in obj.order_line:
                res=order_line_obj.onchange_product_id(
                    obj.pricelist_id.id, 
                    line.product_id.id, 
                    line.product_qty, 
                    line.product_uom.id, 
                    obj.partner_id.id, 
                    date_order         = line.date_order, 
                    fiscal_position_id = obj.partner_id.property_account_position.id, 
                    date_planned       = line.date_planned, 
                    name               = line.name, 
                    price_unit         = line.price_unit, 
                )
                taxes_id=[]
                for taxe_id in res['value']['taxes_id']:
                    taxes_id.append(taxe_id)
                line.taxes_id=[(6,0,taxes_id)]


    @api.multi
    def test_prix0(self,obj):
        for line in obj.order_line:
            if not line.is_justification and not line.price_unit:
                raise Warning(u"Prix à 0 sans justifcation pour l'article "+str(line.product_id.is_code))


    @api.multi
    def write(self,vals):
        res=super(purchase_order, self).write(vals)
        for obj in self:
            self.test_prix0(obj)
        return res


    @api.model
    def create(self, vals):
        obj = super(purchase_order, self).create(vals)
        self.test_prix0(obj)
        return obj

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
            partner_ids = purchase.is_acheteur_id and [purchase.is_acheteur_id.partner_id.id] or []
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




