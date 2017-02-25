# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning
from math import *


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
                    date_planned=line.date_planned,
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







