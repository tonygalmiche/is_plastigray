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

    is_document = fields.Char("Document (N° de dossier)")


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







