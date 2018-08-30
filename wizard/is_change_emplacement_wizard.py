# -*- coding: utf-8 -*-
from openerp import models,fields,api
import time

class is_change_emplacement_wizard(models.TransientModel):
    _name = "is.change.emplacement.wizard"
    _description = "Changement d'emplacement"

    location_id=fields.Many2one('stock.location', "Emplacement de destination", required=True)

    @api.multi
    def change_emplacement(self):
        cr , uid, context = self.env.args
        for obj in self:
            move_obj = self.env['stock.move']
            if 'active_ids' in context:
                for id in context['active_ids']:
                    line = self.env['report.stock.lot.change.location'].browse(id)
                    res = move_obj.onchange_product_id(line.product_id.id, line.location_id.id, obj.location_id.id, False)
                    uos_id = line.product_id.uos_id and line.product_id.uos_id.id or False
                    product_uos_qty =  move_obj.onchange_quantity(line.product_id.id, line.qty, line.product_id.uom_id.id, uos_id)['value']['product_uos_qty']
                    type_interne = self.env['stock.picking.type'].search([('code','=','internal')])
                    vals = {
                        'product_id': line.product_id.id,
                        'name': "Changement d'emplacement",
                        'product_uom': res['value']['product_uom'],
                        'product_uos': res['value']['product_uos'],
                        'product_uom_qty': line.qty,
                        'product_uos_qty': product_uos_qty,
                        'location_id': line.location_id.id,
                        'location_dest_id': obj.location_id.id,
                        'date': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'picking_type_id': type_interne and type_interne[0].id,
                        'restrict_lot_id': line.lot_id.id,
                    }
                    move = move_obj.create(vals)
                    move.action_done()

