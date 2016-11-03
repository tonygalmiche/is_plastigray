# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
import time
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.tools import float_compare, float_is_zero

class MrpProduction(models.Model):
    _inherit = "mrp.production"
    _order="name desc"

    @api.one
    def _compute(self):
        package_qty = is_qt_prevue = is_qt_fabriquee = is_qt_reste = 0
        for line in self.move_created_ids2:
            is_qt_fabriquee=is_qt_fabriquee+line.product_uom_qty
        product_package = False
        if self.product_id and self.product_id.packaging_ids:
            pack_brw        = self.product_id.packaging_ids[0]
            product_package = pack_brw.ul and pack_brw.ul.id or False
            package_qty     = pack_brw.qty
            is_qt_prevue    = self.product_qty 
        if package_qty==0:
            package_qty=1
        self.product_package = product_package
        self.package_qty     = package_qty
        self.is_qt_prevue    = is_qt_prevue / package_qty
        self.is_qt_fabriquee = is_qt_fabriquee / package_qty
        self.is_qt_reste     = self.is_qt_prevue - self.is_qt_fabriquee


    product_package           = fields.Many2one('product.ul'           , compute="_compute", string="Unité de conditionnement")
    package_qty               = fields.Float(string='Qt par UC'        , compute="_compute")
    is_qt_prevue              = fields.Float(string="Qt prévue (UC)"   , compute="_compute")
    is_qt_fabriquee           = fields.Float(string="Qt fabriquée (UC)", compute="_compute")
    is_qt_reste               = fields.Float(string="Qt reste (UC)"    , compute="_compute")
    date_planned              = fields.Datetime(string='Date plannifiée', required=True, readonly=False)
    is_done                   = fields.Boolean(string="Is done ?", default=False)
    mrp_product_suggestion_id = fields.Many2one('mrp.prevision','MRP Product Suggestion')


    @api.multi
    def action_confirm(self):
        for rec in self:
            if rec.mrp_product_suggestion_id:
                rec.mrp_product_suggestion_id.unlink()
        return super(MrpProduction, self).action_confirm()






    def action_produce(self, cr, uid, production_id, production_qty, production_mode, wiz=False, context=None):
        """ To produce final product based on production mode (consume/consume&produce).
        If Production mode is consume, all stock move lines of raw materials will be done/consumed.
        If Production mode is consume & produce, all stock move lines of raw materials will be done/consumed
        and stock move lines of final product will be also done/produced.
        @param production_id: the ID of mrp.production object
        @param production_qty: specify qty to produce in the uom of the production order
        @param production_mode: specify production mode (consume/consume&produce).
        @param wiz: the mrp produce product wizard, which will tell the amount of consumed products needed
        @return: True
        """
        stock_mov_obj = self.pool.get('stock.move')
        uom_obj = self.pool.get("product.uom")
        production = self.browse(cr, uid, production_id, context=context)
        production_qty_uom = uom_obj._compute_qty(cr, uid, production.product_uom.id, production_qty, production.product_id.uom_id.id)
        precision = self.pool['decimal.precision'].precision_get(cr, uid, 'Product Unit of Measure')
        main_production_move = False
        if production_mode == 'consume_produce':
            produced_products = {}
            for produced_product in production.move_created_ids2:
                if produced_product.scrapped:
                    continue
                if not produced_products.get(produced_product.product_id.id, False):
                    produced_products[produced_product.product_id.id] = 0
                produced_products[produced_product.product_id.id] += produced_product.product_qty
            if production.move_created_ids:
                for produce_product in production.move_created_ids:
                    subproduct_factor = self._get_subproduct_factor(cr, uid, production.id, produce_product.id, context=context)
                    lot_id = False
                    if wiz:
                        lot_id = wiz.lot_id.id
                    qty = min(subproduct_factor * production_qty_uom, produce_product.product_qty) #Needed when producing more than maximum quantity

                    #location_id=production.location_dest_id.id
                    new_moves = stock_mov_obj.action_consume(cr, uid, [produce_product.id], qty,
                                                             location_id=produce_product.location_id.id, restrict_lot_id=lot_id, context=context)
                    stock_mov_obj.write(cr, uid, new_moves, {'production_id': production_id}, context=context)
                    remaining_qty = subproduct_factor * production_qty_uom - qty
                    if not float_is_zero(remaining_qty, precision_digits=precision):
                        extra_move_id = stock_mov_obj.copy(cr, uid, produce_product.id, default={'product_uom_qty': remaining_qty,
                                                                                                 'production_id': production_id}, context=context)
                        stock_mov_obj.action_confirm(cr, uid, [extra_move_id], context=context)
                        stock_mov_obj.action_done(cr, uid, [extra_move_id], context=context)
    
                    if produce_product.product_id.id == production.product_id.id:
                        main_production_move = produce_product.id
            else:
                e_move_id = False
                if production.move_created_ids2:
                    e_move_id = production.move_created_ids2[0]
                    extra_move_id = stock_mov_obj.copy(cr, uid, e_move_id.id, default={
                        'product_uom_qty'  : production_qty_uom, 
                        'production_id'    : production_id,
                        'location_dest_id' : production.location_dest_id.id
                    }, context=context)
                    stock_mov_obj.action_confirm(cr, uid, [extra_move_id], context=context)
                    stock_mov_obj.action_done(cr, uid, [extra_move_id], context=context)

    


        if production_mode in ['consume', 'consume_produce']:
            if wiz:
                consume_lines = []
                for cons in wiz.consume_lines:
                    consume_lines.append({'product_id': cons.product_id.id, 'lot_id': cons.lot_id.id, 'product_qty': cons.product_qty})
            else:
                consume_lines = self._calculate_qty(cr, uid, production, production_qty_uom, context=context)
            for consume in consume_lines:
                remaining_qty = consume['product_qty']
                for raw_material_line in production.move_lines:
                    if raw_material_line.state in ('done', 'cancel'):
                        continue
                    if remaining_qty <= 0:
                        break
                    if consume['product_id'] != raw_material_line.product_id.id:
                        continue
                    consumed_qty = min(remaining_qty, raw_material_line.product_qty)
                    stock_mov_obj.action_consume(cr, uid, [raw_material_line.id], consumed_qty, raw_material_line.location_id.id,
                                                 restrict_lot_id=consume['lot_id'], consumed_for=main_production_move, context=context)
                    remaining_qty -= consumed_qty
                if not float_is_zero(remaining_qty, precision_digits=precision):
                    product = self.pool.get('product.product').browse(cr, uid, consume['product_id'], context=context)
                    extra_move_id = self._make_consume_line_from_data(cr, uid, production, product, product.uom_id.id, remaining_qty, False, 0, context=context)
                    stock_mov_obj.write(cr, uid, [extra_move_id], {'restrict_lot_id': consume['lot_id'],
                                                                    'consumed_for': main_production_move}, context=context)
                    stock_mov_obj.action_done(cr, uid, [extra_move_id], context=context)

        self.message_post(cr, uid, production_id, body=_("%s produced") % self._description, context=context)

        # Remove remaining products to consume if no more products to produce
        if not production.move_created_ids and production.move_lines:
            stock_mov_obj.action_cancel(cr, uid, [x.id for x in production.move_lines], context=context)

        self.signal_workflow(cr, uid, [production_id], 'button_produce_done')
        return True
    

    @api.v7
    def _prepare_lines(self, cr, uid, production, properties=None, context=None):
        if not context:
            context = {}
        if not context.get('is_custom_compute',False):
            return super(MrpProduction, self)._prepare_lines(cr, uid, production, properties=properties, context=context)
        else:
            # This code is to produce Extra Qty of production
            # search BoM structure and route
            product_qty = context.get('qty_to_compute',0.00)
            bom_obj = self.pool.get('mrp.bom')
            uom_obj = self.pool.get('product.uom')
            bom_point = production.bom_id
            bom_id = production.bom_id.id
            if not bom_point:
                bom_id = bom_obj._bom_find(cr, uid, product_id=production.product_id.id, properties=properties, context=context)
                if bom_id:
                    bom_point = bom_obj.browse(cr, uid, bom_id)
                    routing_id = bom_point.routing_id.id or False
                    self.write(cr, uid, [production.id], {'bom_id': bom_id, 'routing_id': routing_id})
    
            if not bom_id:
                raise osv.except_osv(_('Error!'), _("Cannot find a bill of material for this product."))
    
            # get components and workcenter_lines from BoM structure
            factor = uom_obj._compute_qty(cr, uid, production.product_uom.id, product_qty, bom_point.product_uom.id)
            # product_lines, workcenter_lines
            return bom_obj._bom_explode(cr, uid, bom_point, production.product_id, factor / bom_point.product_qty, properties, routing_id=production.routing_id.id, context=context)


    @api.multi
    def action_production_end(self):
        for production in self:
            production._costs_generate(production)
        # Check related procurements
        proc_obj = self.env["procurement.order"]
        procs = proc_obj.search([('production_id', 'in', self.ids)])
        procs.check()
        self.write({'is_done': True})
        return True
    

    @api.multi
    def action_done(self):
        self.write({'state': 'done', 'date_finished': time.strftime('%Y-%m-%d %H:%M:%S')})
        return True
    

    @api.multi
    def write(self, vals, update=False):
        vals = vals or {}
        if vals.get('date_planned',False):
            stock_move_obj = self.env["stock.move"]
            for rec in self:
                move_ids = stock_move_obj.search([('production_id','=', rec.id)])
                move_ids += rec.move_lines
                move_ids.write({'date': vals.get('date_planned')})
        return super(MrpProduction, self).write(vals, update=update)


