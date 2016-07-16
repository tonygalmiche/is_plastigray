# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _


class stock_move(models.Model):
    _inherit = "stock.move"


    @api.multi
    def action_acceder_mouvement_stock(self):
        dummy, view_id = self.env['ir.model.data'].get_object_reference('stock', 'view_move_form')
        for obj in self:
            return {
                'name': "Mouvement de stock",
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'stock.move',
                'type': 'ir.actions.act_window',
                'res_id': obj.id,
                'domain': '[]',
            }


class stock_production_lot(models.Model):
    _inherit = "stock.production.lot"

    is_date_peremption = fields.Date("Date de péremption")
