# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _

from openerp.exceptions import Warning
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare


     
class stock_picking(models.Model):
    _inherit = "stock.picking"
    _order   = "date desc, name desc"
    
    location_id          = fields.Many2one(realted='move_lines.location_id', relation='stock.location', string='Location', readonly=False)
    is_sale_order_id     = fields.Many2one('sale.order', 'Commande Client')
    is_purchase_order_id = fields.Many2one('purchase.order', 'Commande Fournisseur')
    is_transporteur_id   = fields.Many2one('res.partner', 'Transporteur')
    is_date_livraison    = fields.Date('Date de livraison')
    is_num_bl            = fields.Char("N° BL fournisseur")
    is_date_reception    = fields.Date('Date de réception')


    @api.onchange('location_id')
    def onchange_location(self):
        for move in self.move_lines:
            move.location_id = self.location_id


    def action_invoice_create(self, cr, uid, ids, journal_id, group=False, type='out_invoice', context=None):
        """
            Permet de fixer la date de la facture à la date de la livraison lors 
            de la création des factures à partir des livraisons
        """
        context = context or {}
        todo = {}
        for picking in self.browse(cr, uid, ids, context=context):
            partner = self._get_partner_to_invoice(cr, uid, picking, dict(context, type=type))
            if group:
                key = partner
            else:
                key = picking.id
            for move in picking.move_lines:
                if move.invoice_state == '2binvoiced':
                    if (move.state != 'cancel') and not move.scrapped:
                        todo.setdefault(key, [])
                        todo[key].append(move)
        invoices = []
        for moves in todo.values():
            date_inv=False
            for move in moves:
                date_inv=move.picking_id.date
            context['date_inv']=date_inv
            invoices += self._invoice_create_line(cr, uid, moves, journal_id, type, context=context)
        return invoices










class stock_quant(models.Model):
    _inherit = "stock.quant"
    _order   = "product_id, location_id"

    is_mold_id = fields.Many2one('is.mold', 'Moule', related='product_id.is_mold_id', readonly=True)



class stock_move(models.Model):
    _inherit = "stock.move"
    _order   = "date desc, id"


    @api.model
    def create(self, vals):
        obj = super(stock_move, self).create(vals)
        if obj.purchase_line_id and obj.picking_id:
            obj.picking_id.is_purchase_order_id=obj.purchase_line_id.order_id.id
        return obj





    def _create_invoice_line_from_vals(self, cr, uid, move, invoice_line_vals, context=None):
        """
        Permet d'ajouter le lien avec la livraison et la section analytique sur
        les lignes des factures
        """
        if move:
            is_section_analytique_id=move.product_id.is_section_analytique_id.id
            invoice_line_vals['is_move_id']=move.id
            invoice_line_vals['is_section_analytique_id']=is_section_analytique_id
        res = super(stock_move, self)._create_invoice_line_from_vals(cr, uid, move, invoice_line_vals, context)
        return res


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


    @api.multi
    def _picking_assign(self, procurement_group, location_from, location_to):
        """Assign a picking on the given move_ids, which is a list of move supposed to share the same procurement_group, location_from and location_to
        (and company). Those attributes are also given as parameters.
        """
        cr       = self._cr
        uid      = self._uid
        context  = self._context
        move_ids = self._ids
        pick_obj = self.env["stock.picking"]
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
            move = self.browse(move_ids)[0]
            if move.origin:
                sale_obj = self.env['sale.order']
                sales = sale_obj.search([('name','=',move.origin)])
                for sale_data in sales:

                    date_livraison=False
                    for line in sale_data.order_line:
                        if line.is_date_livraison>date_livraison:
                            date_livraison=line.is_date_livraison
                    values = {
                        'origin'            : move.origin,
                        'company_id'        : move.company_id and move.company_id.id or False,
                        'move_type'         : move.group_id and move.group_id.move_type or 'direct',
                        'partner_id'        : move.partner_id.id or False,
                        'picking_type_id'   : move.picking_type_id and move.picking_type_id.id or False,
                        'is_sale_order_id'  : sale_data and sale_data.id or False,
                        'is_transporteur_id': sale_data and sale_data.is_transporteur_id.id or False,
                        'is_date_livraison' : date_livraison,
                    }
                    pick = pick_obj.create(values)
        if pick:
            self.write({'picking_id': pick.id})
        return
    





    def action_consume(self, cr, uid, ids, product_qty, location_id=False, restrict_lot_id=False, restrict_partner_id=False,
                       consumed_for=False, context=None):
        """ Consumed product with specific quantity from specific source location.
        @param product_qty: Consumed/produced product quantity (= in quantity of UoM of product)
        @param location_id: Source location
        @param restrict_lot_id: optionnal parameter that allows to restrict the choice of quants on this specific lot
        @param restrict_partner_id: optionnal parameter that allows to restrict the choice of quants to this specific partner
        @param consumed_for: optionnal parameter given to this function to make the link between raw material consumed and produced product, for a better traceability
        @return: New lines created if not everything was consumed for this line
        """

        if context is None:
            context = {}
        res = []
        production_obj = self.pool.get('mrp.production')

        #** Test si la quantité est négative pour inverser les emplacements ****
        inverse=False
        if product_qty <= 0:
            inverse=True
            product_qty=-product_qty

        ids2 = []
        for move in self.browse(cr, uid, ids, context=context):
            if move.state == 'draft':
                ids2.extend(self.action_confirm(cr, uid, [move.id], context=context))
            else:
                ids2.append(move.id)
        prod_orders = set()

        for move in self.browse(cr, uid, ids2, context=context):
            prod_orders.add(move.raw_material_production_id.id or move.production_id.id)
            move_qty = move.product_qty

            #** Si la quantité est négative, il faut augmenter le reste à produire
            if inverse:
                quantity_rest = move_qty + product_qty
            else:
                quantity_rest = move_qty - product_qty
            
            # Compare with numbers of move uom as we want to avoid a split with 0 qty
            quantity_rest_uom = move.product_uom_qty - self.pool.get("product.uom")._compute_qty_obj(cr, uid, move.product_id.uom_id, product_qty, move.product_uom)

            #** Si la quantité est négative, ajout de 2 fois la quantité déclarée sur le mouvement en attente
            #** La fonction slit ci-dessous enlevera fois la quantité => Du coup, nous seront bien à +1 comme souhaité
            if inverse and product_qty>0:
                move.product_uom_qty=move.product_uom_qty+2*product_qty

            #Si la quantité restante est à 0 , mettre 0.00001 pour ne pas solder le mouvement
            if float_compare(quantity_rest_uom, 0, precision_rounding=move.product_uom.rounding) == 0:
                quantity_rest=move.product_uom.rounding

            #** Invertion des emplacements pour faire un mouvement négatif
            if inverse:
                mem_location_id           = move.location_id.id
                mem_location_dest_id      = move.location_dest_id.id
                move.location_dest_id     = mem_location_id
                move.location_id          = mem_location_dest_id

            #** Création d'un nouveau mouvement qui contiendra le reste à fabriquer. Le mouvement en cours contiendra la quantité déclarée
            new_mov = self.split(cr, uid, move, quantity_rest, context=context)

            if move.production_id:
                self.write(cr, uid, [new_mov], {'production_id': move.production_id.id}, context=context)

            #** Sur le nouveau mouvement qui correspond au reste à produire, il faut remettre les emplacements dans l'ordre (nouvelle invertion)
            if inverse:
                v={
                    'location_id'     : mem_location_id,
                    'location_dest_id': mem_location_dest_id,
                }
                self.write(cr, uid, [new_mov], v, context)
            res.append(new_mov)

            vals = {'restrict_lot_id': restrict_lot_id,
                    'restrict_partner_id': restrict_partner_id,
                    'consumed_for': consumed_for}
            self.write(cr, uid, [move.id], vals, context=context)


        # Original moves will be the quantities consumed, so they need to be done
        self.action_done(cr, uid, ids2, context=context)

        if res:
            self.action_assign(cr, uid, res, context=context)
        if prod_orders:
            production_obj.signal_workflow(cr, uid, list(prod_orders), 'button_produce')
        return res



class stock_production_lot(models.Model):
    _inherit = "stock.production.lot"

    is_date_peremption = fields.Date("Date de péremption")
    is_lot_fournisseur = fields.Char("Lot fournisseur")





