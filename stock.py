# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _



     
class stock_picking(models.Model):
    _inherit = "stock.picking"
    
    location_id        = fields.Many2one(realted='move_lines.location_id', relation='stock.location', string='Location', readonly=False)
    is_sale_order_id   = fields.Many2one('sale.order', 'Commande')
    is_transporteur_id = fields.Many2one('res.partner', 'Transporteur')
    
    @api.onchange('location_id')
    def onchange_location(self):
        for move in self.move_lines:
            move.location_id = self.location_id






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


    @api.cr_uid_ids_context
    def _picking_assign(self, cr, uid, move_ids, procurement_group, location_from, location_to, context=None):
        """Assign a picking on the given move_ids, which is a list of move supposed to share the same procurement_group, location_from and location_to
        (and company). Those attributes are also given as parameters.
        """
        pick_obj = self.pool.get("stock.picking")
        # Use a SQL query as doing with the ORM will split it in different queries with id IN (,,)
        # In the next version, the locations on the picking should be stored again.
        query = """
            SELECT stock_picking.id FROM stock_picking, stock_move
            WHERE
                stock_picking.state in ('draft', 'confirmed', 'waiting') AND
                stock_move.picking_id = stock_picking.id AND
                stock_move.location_id = %s AND
                stock_move.location_dest_id = %s AND
        """
        params = (location_from, location_to)
        if not procurement_group:
            query += "stock_picking.group_id IS NULL LIMIT 1"
        else:
            query += "stock_picking.group_id = %s LIMIT 1"
            params += (procurement_group,)
        cr.execute(query, params)
        [pick] = cr.fetchone() or [None]
        if not pick:
            move = self.browse(cr, uid, move_ids, context=context)[0]
            print "MOVE", move.origin, move.id
            sale_obj = self.pool.get('sale.order')
            sale_id = sale_obj.search(cr, uid, [('name','=',move.origin)])
            if sale_id:
                sale_data = sale_obj.browse(cr, uid, sale_id[0])
                values = {
                    'origin': move.origin,
                    'company_id'        : move.company_id and move.company_id.id or False,
                    'move_type'         : move.group_id and move.group_id.move_type or 'direct',
                    'partner_id'        : move.partner_id.id or False,
                    'picking_type_id'   : move.picking_type_id and move.picking_type_id.id or False,
                    'is_sale_order_id'  : sale_data and sale_data.id or False,
                    'is_transporteur_id': sale_data and sale_data.is_transporteur_id.id or False,
                }
                pick = pick_obj.create(cr, uid, values, context=context)
        return self.write(cr, uid, move_ids, {'picking_id': pick}, context=context)
    





class stock_production_lot(models.Model):
    _inherit = "stock.production.lot"

    is_date_peremption = fields.Date("Date de péremption")
