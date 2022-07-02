# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
import time
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.tools import float_compare, float_is_zero
from openerp import tools, SUPERUSER_ID
import openerp.addons.decimal_precision as dp
from openerp.exceptions import Warning
import logging
_logger = logging.getLogger(__name__)


class MrpProduction(models.Model):
    _inherit = "mrp.production"
    _order="name desc"

    @api.one
    def _compute(self):
        package_qty = is_qt_prevue = is_qt_fabriquee = is_qt_rebut = is_qt_reste = 0
        for line in self.move_created_ids2:
            if line.location_dest_id.scrap_location and line.state=='done':
                is_qt_rebut=is_qt_rebut+line.product_uom_qty
            else:
                if line.location_dest_id.usage=='internal' and line.state=='done':
                    is_qt_fabriquee=is_qt_fabriquee+line.product_uom_qty
        for line in self.move_created_ids2:
            if line.location_id.usage=='internal' and line.state=='done':
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


    product_qty               = fields.Float('Product Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True, readonly=False)
    product_lines             = fields.One2many('mrp.production.product.line', 'production_id', 'Scheduled goods', readonly=False)
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
    is_mold_id                = fields.Many2one('is.mold', 'Moule', related='product_id.is_mold_id'      , readonly=True)
    is_mold_dossierf          = fields.Char('Moule ou Dossier F'  , related='product_id.is_mold_dossierf', readonly=True)
    is_num_essai              = fields.Char("N°Essai")
    is_prioritaire            = fields.Boolean("Ordre de fabrication prioritaire")
    move_lines2               = fields.One2many('stock.move', 'raw_material_production_id', 'Consumed Products',domain=[('state', '=', 'done')], readonly=True)


    @api.multi
    def action_confirm(self):
        res=super(MrpProduction, self).action_confirm()
        for obj in self:
            obj.force_production()
            obj.action_in_production()
        return res


    @api.multi
    def action_produce(self, production_id, qty, production_mode, wiz=False, is_employee_theia_id=False):

        #is_employee_theia_id=223

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
                    'restrict_lot_id'  : lot_id,
                    'is_employee_theia_id': is_employee_theia_id, 
                })
                new_move.action_confirm()
                new_move.action_done()
                main_production_move = new_move.id
        #***********************************************************************

        #** Traitement des composants ******************************************
        if production_mode in ['consume', 'consume_produce']:
            sequence=0
            nb=len(wiz.consume_lines)
            ct=0
            for move in production.move_lines:
                sequence=sequence+1
                for wiz_line in wiz.consume_lines:
                    if move.product_id==wiz_line.product_id and wiz_line.is_sequence==sequence:
                        ct=ct+1
                        consumed_qty = wiz_line.product_qty
                        lot_id       = wiz_line.lot_id.id
                        move.action_consume(consumed_qty, move.location_id.id, restrict_lot_id=lot_id, consumed_for=main_production_move)
                        move.is_employee_theia_id = is_employee_theia_id


            # TODO : Ajout d'un blocage le 27/01/2018 pour empècher les problèmes de déclarations sur les OF
            if nb!=ct:
                raise Warning("Probleme de synchronisation de nomenclature. Il faut modifier la quantite de cet OF pour resynchroniser la nomenclature")
        #***********************************************************************


        #** Vérifier qu'il n'y a pas de desyncronisation après *****************
        #TODO : Ajout de cette partie pour synchronier la nomenclature avec sudo si problème constaté le 20/02/2020
        if production_mode in ['consume', 'consume_produce']:
            sequence=0
            nb=len(wiz.consume_lines)
            ct=0
            for move in production.move_lines:
                sequence=sequence+1
                for wiz_line in wiz.consume_lines:
                    if move.product_id==wiz_line.product_id and wiz_line.is_sequence==sequence:
                        ct=ct+1
            if nb!=ct:
                _logger.info(u"#### Nomenclature Ordre de Fabrication desynchronise => importer_nomenclature avec sudo() ####")
                production.sudo().importer_nomenclature()
        #***********************************************************************

        return



    def _prepare_lines(self, cr, uid, production, properties=None, context=None):
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
        factor = uom_obj._compute_qty(cr, uid, production.product_uom.id, production.product_qty, bom_point.product_uom.id)
        return bom_obj._bom_explode(cr, uid, bom_point, production.product_id, factor / bom_point.product_qty, properties, routing_id=production.routing_id.id, context=context)


    @api.multi
    def _action_compute_lines(self, properties=None):
        """ Compute product_lines and workcenter_lines from BoM structure
        @return: product_lines
        """
        cr, uid, context = self.env.args
        if properties is None:
            properties = []
        results = []
        prod_line_obj = self.pool.get('mrp.production.product.line')
        workcenter_line_obj = self.pool.get('mrp.production.workcenter.line')
        for production in self:
            production.product_lines.unlink()
            production.workcenter_lines.unlink()
            res = self._prepare_lines(production, properties=properties)
            results = res[0] # product_lines
            results2 = res[1] # workcenter_lines
            uom_obj = self.pool.get('product.uom')
            bom_obj = self.pool.get('mrp.bom')
            factor = uom_obj._compute_qty(cr, uid, production.product_uom.id, production.product_qty, production.bom_id.product_uom.id)
            res=bom_obj._bom_explode(cr, uid, production.bom_id, production.product_id, 1, properties, routing_id=production.routing_id.id, context=context)
            results = res[0] # product_lines
            for line in results:
                qty=line['product_qty']
                line['production_id'] = production.id
                line['product_qty']   = qty*factor
                line['is_bom_qty']    = qty
                prod_line_obj.create(cr, uid, line)
            for line in results2:
                line['production_id'] = production.id
                workcenter_line_obj.create(cr, uid, line, context)
        return results


    @api.multi
    def action_production_end(self):
        for production in self:
            production._costs_generate(production)
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
    def recreer_mouvements(self):
        """
        Recréer les mouvements de stocks si nomenclature OF modifiée
        """
        for obj in self:
            qt_reste=obj.is_qt_reste_uom
            for move in obj.move_created_ids:
                move.product_uom_qty=qt_reste
            cr, uid, context = self.env.args
            for move in obj.move_lines:
                move.action_cancel()
            stock_moves = []
            for line in obj.product_lines:
                if line.product_id.type != 'service':
                    qty=qt_reste*line.is_bom_qty
                    #Si la quantité restante est à 0 , mettre 0.00001 pour ne pas solder le mouvement
                    if float_compare(qty, 0, precision_rounding=line.product_uom.rounding) == 0:
                        qty=line.product_uom.rounding
                    line.product_qty=qty
                    stock_move_id = obj._make_production_consume_line(line)
                    stock_moves.append(stock_move_id)
                line.product_qty=obj.product_qty*line.is_bom_qty
            if stock_moves:
                move_obj=self.pool.get('stock.move')
                move_obj.action_confirm(cr, uid, stock_moves, context=context)
                move_obj.force_assign(cr, uid, stock_moves)
            #** Mise à jour des ordres de travaux sans supprimer les lignes ****
            res = self._prepare_lines(obj)
            results = res[1] # workcenter_lines
            for row in results:
                for line in obj.workcenter_lines:
                    if row['sequence']==line.sequence:
                        line.cycle = row['cycle']
                        line.hour  = row['hour']
            #*******************************************************************


    @api.multi
    def write(self, vals, update=False):
        vals = vals or {}
        if vals.get('date_planned',False):
            stock_move_obj = self.env["stock.move"]
            for rec in self:
                move_ids = stock_move_obj.search([('production_id','=', rec.id)])
                move_ids += rec.move_lines
                for move in move_ids:
                    if move.state not in ['cancel','done']:
                        move.write({
                            'date'         : vals.get('date_planned'),
                            'date_expected': vals.get('date_planned'),
                        })

#                move_ids.write({
#                    'date'         : vals.get('date_planned'),
#                    'date_expected': vals.get('date_planned'),
#                })

        res=super(MrpProduction, self).write(vals, update=update)
        if 'product_lines' in vals or 'product_qty' in vals:
            self.recreer_mouvements()
        return res


    @api.multi
    def importer_nomenclature(self):
        cr, uid, context = self.env.args
        prod_line_obj = self.pool.get('mrp.production.product.line')
        uom_obj = self.pool.get('product.uom')
        bom_obj = self.pool.get('mrp.bom')
        for production in self:
            production.product_lines.unlink()
            res = self._prepare_lines(production)
            results = res[0] # product_lines
            res=bom_obj._bom_explode(cr, uid, production.bom_id, production.product_id, 1, None, routing_id=production.routing_id.id, context=context)
            results = res[0] # product_lines
            for line in results:
                qty=line['product_qty']
                line['production_id'] = production.id
                line['product_qty']   = qty*production.product_qty
                line['is_bom_qty']    = qty
                prod_line_obj.create(cr, uid, line)
            production.recreer_mouvements()


    @api.multi
    def get_consume_lines(self, production_id, product_qty):
        prod_obj = self.env["mrp.production"]
        uom_obj = self.env["product.uom"]
        production = prod_obj.browse(production_id)
        consume_lines = []
        new_consume_lines = []
        if product_qty > 0.0:
            product_uom_qty = uom_obj._compute_qty(production.product_uom.id, product_qty, production.product_id.uom_id.id)
            consume_lines = prod_obj._calculate_qty(production, product_qty=product_uom_qty)
        
        for consume in consume_lines:
            new_consume_lines.append([0, False, consume])
        return new_consume_lines
    

    @api.multi
    def get_track(self, product_id):
        prod_obj = self.env["product.product"]
        return product_id and prod_obj.browse(product_id).track_production or False


    @api.multi
    def get_wizard(self, production):
        wiz_obj = self.env['mrp.product.produce']
        vals = {
            'product_id': production.product_id.id,
            'product_qty': 1.0,
            'mode': 'consume_produce',
            'lot_id': False,
            'consume_lines': self.get_consume_lines(production.id, 1.0),
            'track_production': self.get_track(production.product_id.id)
        }
        wiz = wiz_obj.create(vals)
        return wiz


    @api.multi
    def declaration_production_theia_action(self,qt_bonne, qt_rebut, is_employee_theia_id=False):

        #is_employee_theia_id=480

        err=""
        for obj in self:
            qt=0
            if qt_bonne>0:
                qt=qt_bonne
                filtre = [
                    ('name' , '=', 'ATELIER'),
                    ('usage', '=', 'internal'),
                ]
            if qt_rebut>0:
                qt=qt_rebut
                filtre = [
                    ('name' , '=', 'Rebuts'),
                    ('usage', '=', 'inventory'),
                ]
            if qt==0:
                err="Qt = 0"
            if err=="":
                lines = self.env["stock.location"].search(filtre)
                location_id = lines and lines[0].id or False
                if location_id==False:
                    err="Emplacement non trouve"
            if err=="":
                wiz = obj.get_wizard(obj)

                #** Recherche / Création du lot *******************************
                lot_obj = self.env["stock.production.lot"]
                filtre = [
                    ('name'      , '=', obj.name),
                    ('product_id', '=', obj.product_id.id),
                ]
                lots = lot_obj.search(filtre)
                if lots:
                    lot_id=lots[0].id
                else:
                    vals={
                        'name'      : obj.name,
                        'product_id': obj.product_id.id,
                    }
                    lot = lot_obj.create(vals)
                    lot_id = lot.id
                wiz.lot_id = lot_id
                #**************************************************************

                wiz.finished_products_location_id = location_id
                wiz.product_package_qty = qt
                res = wiz.with_context(active_id=obj.id).on_change_qty(qt, False)
                wiz.consume_lines.unlink()
                wiz.write(res["value"])

                if qt_rebut>0:
                    for line in wiz.consume_lines:
                        code = line.product_id.is_code
                        if code[:1]!="5":
                            line.unlink()
                obj.action_produce(obj.id, qt, 'consume_produce', wiz, is_employee_theia_id=is_employee_theia_id)
                if qt_rebut>0:
                    obj.sudo().importer_nomenclature() #Sinon, j'ai un soucis avec la déclaration des rebuts
        res=True
        if err!="":
            res={"err": err}
        return res
    

class mrp_production_product_line(models.Model):
    _inherit = 'mrp.production.product.line'

    is_bom_qty = fields.Float("Quantité unitaire", digits=(16, 6))

    @api.multi
    def action_acceder_ligne(self):
        for obj in self:
            return {
                'name': "Mouvement de stock",
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'mrp.production.product.line',
                'type': 'ir.actions.act_window',
                'res_id': obj.id,
                'domain': '[]',
            }


    @api.multi
    def on_change_product_id(self, product_id,is_bom_qty):
        cr, uid, context = self.env.args
        qty=context.get('product_qty',1)
        value = {}
        if product_id:
            product=self.env["product.product"].browse(product_id)
            value = {
                'name'       : product.name,
                'product_uom': product.uom_id.id,
                'product_qty': is_bom_qty*qty
            }
        return {'value': value}



