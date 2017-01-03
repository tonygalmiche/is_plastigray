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
        package_qty = is_qt_prevue = is_qt_fabriquee = is_qt_rebut = is_qt_reste = 0
        for line in self.move_created_ids2:
            if line.location_dest_id.scrap_location:
                is_qt_rebut=is_qt_rebut+line.product_uom_qty
            else:
                if line.location_dest_id.usage=='internal':
                    is_qt_fabriquee=is_qt_fabriquee+line.product_uom_qty
        for line in self.move_created_ids2:
            if line.location_id.usage=='internal':
                is_qt_fabriquee=is_qt_fabriquee-line.product_uom_qty

        product_package = False
        if self.product_id and self.product_id.packaging_ids:
            pack_brw        = self.product_id.packaging_ids[0]
            product_package = pack_brw.ul and pack_brw.ul.id or False
            package_qty     = pack_brw.qty
            is_qt_prevue    = self.product_qty 
        if package_qty==0:
            package_qty=1
        self.product_package     = product_package
        self.package_qty         = package_qty

        self.is_qt_fabriquee_uom = is_qt_fabriquee 
        self.is_qt_rebut_uom     = is_qt_rebut
        self.is_qt_reste_uom     = self.product_qty - self.is_qt_fabriquee_uom

        self.is_qt_prevue        = is_qt_prevue / package_qty
        self.is_qt_fabriquee     = is_qt_fabriquee / package_qty
        self.is_qt_rebut         = is_qt_rebut / package_qty
        self.is_qt_reste         = self.is_qt_prevue - self.is_qt_fabriquee

    is_qt_fabriquee_uom       = fields.Float(string="Qt fabriquée"     , compute="_compute")
    is_qt_rebut_uom           = fields.Float(string="Qt rebut"         , compute="_compute")
    is_qt_reste_uom           = fields.Float(string="Qt reste"         , compute="_compute")

    product_package           = fields.Many2one('product.ul'           , compute="_compute", string="Unité de conditionnement")
    package_qty               = fields.Float(string='Qt par UC'        , compute="_compute")

    is_qt_prevue              = fields.Float(string="Qt prévue (UC)"   , compute="_compute")
    is_qt_fabriquee           = fields.Float(string="Qt fabriquée (UC)", compute="_compute")
    is_qt_rebut               = fields.Float(string="Qt rebut (UC)"    , compute="_compute")
    is_qt_reste               = fields.Float(string="Qt reste (UC)"    , compute="_compute")

    date_planned              = fields.Datetime(string='Date plannifiée', required=True, readonly=False)
    is_done                   = fields.Boolean(string="Is done ?", default=False)
    mrp_product_suggestion_id = fields.Many2one('mrp.prevision','MRP Product Suggestion')
    is_mold_id                = fields.Many2one('is.mold', 'Moule', related='product_id.is_mold_id', readonly=True)

    is_num_essai              = fields.Char("N°Essai")


    @api.multi
    def action_produce(self, production_id, qty, production_mode, wiz=False):
        stock_mov_obj = self.env['stock.move']
        uom_obj       = self.env["product.uom"]
        production    = self.browse(production_id)
        qty_uom       = uom_obj._compute_qty(production.product_uom.id, qty, production.product_id.uom_id.id)
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        #** Traitement des produits finis **************************************
        main_production_move = False
        if production_mode == 'consume_produce':
            for move in production.move_created_ids:
                dest_id=wiz.finished_products_location_id
                reste=move.product_uom_qty
                if not dest_id.scrap_location:
                    reste=reste-qty_uom
                move.product_uom_qty=reste
                if qty_uom>=0:
                    location_id      = move.location_id.id
                    location_dest_id = dest_id.id
                else:
                    qty_uom=-qty_uom
                    location_id      = dest_id.id
                    location_dest_id = move.location_id.id 
                lot_id = wiz.lot_id.id
                new_move = move.copy(default={
                    'product_uom_qty'  : qty_uom, 
                    'production_id'    : production_id,
                    'location_id'      : location_id,
                    'location_dest_id' : location_dest_id,
                    'restrict_lot_id'  : lot_id
                })
                new_move.action_confirm()
                new_move.action_done()
                main_production_move = new_move.id
        #***********************************************************************

        #** Traitement des composants ******************************************
        if production_mode in ['consume', 'consume_produce']:
            sequence=0
            for move in production.move_lines:
                sequence=sequence+1
                for wiz_line in wiz.consume_lines:
                    if move.product_id==wiz_line.product_id and wiz_line.is_sequence==sequence:
                        consumed_qty=wiz_line.product_qty
                        move.action_consume(consumed_qty, move.location_id.id, restrict_lot_id=False, consumed_for=main_production_move)
            return
        #***********************************************************************



    

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
        self.action_cancel()
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


