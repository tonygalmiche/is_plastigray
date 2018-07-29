# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _

from openerp.exceptions import Warning
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare
import time
import datetime


class stock_pack_operation(models.Model):
    _inherit = "stock.pack.operation"
  
    move_id = fields.Many2one('stock.move', 'Stock Move')


class stock_location(models.Model):
    _inherit = 'stock.location'

    control_quality = fields.Boolean(u'Contrôle qualité', default=False)


class is_commentaire_mouvement_stock(models.Model):
    _name = 'is.commentaire.mouvement.stock'
    _description = 'Comentaires sur les mouvements'

    name = fields.Char('Description', required=True)


class stock_picking(models.Model):
    _inherit = "stock.picking"
    _order   = "date desc, name desc"
    
    location_id           = fields.Many2one(realted='move_lines.location_id', relation='stock.location', string='Location', readonly=False)
    is_sale_order_id      = fields.Many2one('sale.order', 'Commande Client')
    is_purchase_order_id  = fields.Many2one('purchase.order', 'Commande Fournisseur')
    is_transporteur_id    = fields.Many2one('res.partner', 'Transporteur')
    is_date_expedition    = fields.Date("Date d'expédition")
    is_date_livraison     = fields.Date("Date d'arrivée chez le client")
    is_date_livraison_vsb = fields.Boolean('Avertissement VSB', store=False, compute='_compute_is_date_livraison_vsb', readonly=True)
    is_date_livraison_msg = fields.Char("Avertissement"       , store=False, compute='_compute_is_date_livraison_vsb', readonly=True)
    is_num_bl             = fields.Char("N° BL fournisseur")
    is_date_reception     = fields.Date('Date de réception')
    is_facture_pk_id      = fields.Many2one('is.facture.pk', 'Facture PK')


    @api.depends('is_date_livraison', 'partner_id', 'company_id')
    def _compute_is_date_livraison_vsb(self):
        for obj in self:
            vsb = self.check_date_livraison(obj.is_date_livraison, obj.partner_id.id)
            obj.is_date_livraison_vsb=vsb
            msg=''
            if not vsb:
                msg='La date de livraison tombe pendant la fermeture du client !'
            obj.is_date_livraison_msg=msg


    @api.multi
    def check_date_livraison(self, date_livraison,  partner_id, context=None):
        res_partner = self.env['res.partner']
        if partner_id:
            partner = self.env['res.partner'].browse(partner_id)
            # jours de fermeture de la société
            jours_fermes = res_partner.num_closing_days(partner)
            # Jours de congé de la société
            leave_dates = res_partner.get_leave_dates(partner,avec_jours_feries=True)
            # num de jour dans la semaine de la date de livraison
            num_day = time.strftime('%w', time.strptime(date_livraison, '%Y-%m-%d'))
            if int(num_day) in jours_fermes or date_livraison in leave_dates:
                return False
        return True


    @api.multi
    def onchange_date_expedition(self, date_expedition, partner_id, company_id):
        date_livraison=date_expedition
        if partner_id and company_id:
            partner = self.env['res.partner'].browse(partner_id)
            company = self.env['res.company'].browse(company_id)
            date_livraison= self.env['res.partner'].get_date_livraison(company, partner, date_expedition)
        v = {}
        warning = {}
        v['is_date_livraison'] = date_livraison
        return {'value': v,
                'warning': warning}


    @api.multi
    def action_imprimer_etiquette_reception(self):
        for obj in self:
            uid=self._uid
            user=self.env['res.users'].browse(uid)
            soc=user.company_id.partner_id.is_code
            return {
                'type' : 'ir.actions.act_url',
                'url': 'http://odoo/odoo-erp/reception/Impression_Etiquette_Reception.php?Soc='+str(soc)+'&&zzCode='+str(obj.name),
                'target': '_blank',
            }


    @api.multi
    def action_annuler_reception(self):
        cr = self._cr
        for obj in self:

            #** Recherche s'il existe une réception pour cette commande ********
            order_id=obj.is_purchase_order_id.id
            pickings = self.env['stock.picking'].search([('is_purchase_order_id','=',order_id),('state','=','assigned')])
            picking=False
            for p in pickings:
                picking=p
            #*******************************************************************

            #** Copie de la réception pour pouvoir la réfaire ******************
            if not picking:
                picking=obj.copy()
                picking.invoice_state=obj.invoice_state
            else:
                for move in obj.move_lines:
                    copy=move.copy()
                    copy.picking_id=picking.id
            #*******************************************************************

            #** Création des mouvements inverses pour annuler la réception *****
            for move in obj.move_lines:
                #** Recherche du lot de la réception à annuler *****************
                lot_id=False
                for quant in move.quant_ids:
                    lot_id=quant.lot_id.id
#                name=move.picking_id.name
#                lots = self.env['stock.production.lot'].search([('product_id','=',move.product_id.id),('name','=',name)])
#                print 'lots=',lots
#                lot_id=False
#                for lot in lots:
#                    lot_id=lot.id
#                    print lot.name
                #***************************************************************
                copy=move.copy()
                copy.location_id      = move.location_dest_id.id
                copy.location_dest_id = move.location_id.id
                copy.restrict_lot_id=lot_id
                copy.action_done()
            #*******************************************************************


            #** Requete directe pour annuler la réception sinon impossible *****
            obj.invoice_state='none'
            SQL="update stock_picking set state='cancel' where id="+str(obj.id)
            cr.execute(SQL)
            #*******************************************************************


            return {
                'name': "Réception",
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'stock.picking',
                'type': 'ir.actions.act_window',
                'res_id': picking.id,
                'domain': '[]',
            }





    #TODO : Fonction reprise complètement par Hiren pour pouvoir gérer les recéptions avec plusieurs lignes du même article
    @api.cr_uid_ids_context
    def do_prepare_partial(self, cr, uid, picking_ids, context=None):
        context = context or {}
        pack_operation_obj = self.pool.get('stock.pack.operation')
        #used to avoid recomputing the remaining quantities at each new pack operation created
        ctx = context.copy()
        ctx['no_recompute'] = True

        #get list of existing operations and delete them
        existing_package_ids = pack_operation_obj.search(cr, uid, [('picking_id', 'in', picking_ids)], context=context)
        if existing_package_ids:
            pack_operation_obj.unlink(cr, uid, existing_package_ids, context)
        for picking in self.browse(cr, uid, picking_ids, context=context):
            forced_qties = {}  # Quantity remaining after calculating reserved quants
            picking_quants = []
            #Calculate packages, reserved quants, qtys of this picking's moves
            for move in picking.move_lines:
                if move.state not in ('assigned', 'confirmed', 'waiting'):
                    continue
                move_quants = move.reserved_quant_ids
                picking_quants += move_quants
                forced_qty = (move.state == 'assigned') and move.product_qty - sum([x.qty for x in move_quants]) or 0
                #if we used force_assign() on the move, or if the move is incoming, forced_qty > 0
                if float_compare(forced_qty, 0, precision_rounding=move.product_id.uom_id.rounding) > 0:
                    if forced_qties.get(move):
                        forced_qties[move] += forced_qty
                    else:
                        forced_qties[move] = forced_qty
            for vals in self._prepare_pack_ops(cr, uid, picking, picking_quants, forced_qties, context=context):
                pack_operation_obj.create(cr, uid, vals, context=ctx)
        #recompute the remaining quantities all at once
        self.do_recompute_remaining_quantities(cr, uid, picking_ids, context=context)
        self.write(cr, uid, picking_ids, {'recompute_pack_op': False}, context=context)
 

    #TODO : Fonction reprise complètement par Hiren pour pouvoir gérer les recéptions avec plusieurs lignes du même article
    def _prepare_pack_ops(self, cr, uid, picking, quants, forced_qties, context=None):
        """ returns a list of dict, ready to be used in create() of stock.pack.operation.

        :param picking: browse record (stock.picking)
        :param quants: browse record list (stock.quant). List of quants associated to the picking
        :param forced_qties: dictionary showing for each product (keys) its corresponding quantity (value) that is not covered by the quants associated to the picking
        """
        def _picking_putaway_apply(product):
            location = False
            # Search putaway strategy
            if product_putaway_strats.get(product.id):
                location = product_putaway_strats[product.id]
            else:
                location = self.pool.get('stock.location').get_putaway_strategy(cr, uid, picking.location_dest_id, product, context=context)
                product_putaway_strats[product.id] = location
            return location or picking.location_dest_id.id

        # If we encounter an UoM that is smaller than the default UoM or the one already chosen, use the new one instead.
        product_uom = {} # Determines UoM used in pack operations
        location_dest_id = None
        location_id = None
        for move in [x for x in picking.move_lines if x.state not in ('done', 'cancel')]:

            #TODO : Le 11/02/2018 : Les articles bloqués sont réceptionnés en Q2
            if picking.is_purchase_order_id:
                if move.product_id.is_ctrl_rcp=='bloque':
                    res = self.pool.get('stock.location').search(cr, uid, [
                            ('name','=', 'Q2'),
                        ], context=context)
                    if res:
                        move.location_dest_id=res[0]

            if not product_uom.get(move.product_id.id):
                product_uom[move.product_id.id] = move.product_id.uom_id
            if move.product_uom.id != move.product_id.uom_id.id and move.product_uom.factor > product_uom[move.product_id.id].factor:
                product_uom[move.product_id.id] = move.product_uom

            if not move.scrapped:
                if location_dest_id and move.location_dest_id.id != location_dest_id:
                    raise Warning(_('The destination location must be the same for all the moves of the picking.'))
                location_dest_id = move.location_dest_id.id
                if location_id and move.location_id.id != location_id:
                    raise Warning(_('The source location must be the same for all the moves of the picking.'))
                location_id = move.location_id.id




        pack_obj = self.pool.get("stock.quant.package")
        quant_obj = self.pool.get("stock.quant")
        vals = []
        qtys_grouped = {}
        #for each quant of the picking, find the suggested location
        quants_suggested_locations = {}
        product_putaway_strats = {}
        for quant in quants:
            if quant.qty <= 0:
                continue
            suggested_location_id = _picking_putaway_apply(quant.product_id)
            quants_suggested_locations[quant] = suggested_location_id

        #find the packages we can movei as a whole
        top_lvl_packages = self._get_top_level_packages(cr, uid, quants_suggested_locations, context=context)
        # and then create pack operations for the top-level packages found
        for pack in top_lvl_packages:
            pack_quant_ids = pack_obj.get_content(cr, uid, [pack.id], context=context)
            pack_quants = quant_obj.browse(cr, uid, pack_quant_ids, context=context)
            vals.append({
                    'picking_id': picking.id,
                    'package_id': pack.id,
                    'product_qty': 1.0,
                    'location_id': pack.location_id.id,
                    'location_dest_id': quants_suggested_locations[pack_quants[0]],
                    'owner_id': pack.owner_id.id,
                })
            #remove the quants inside the package so that they are excluded from the rest of the computation
            for quant in pack_quants:
                del quants_suggested_locations[quant]

        # Go through all remaining reserved quants and group by product, package, lot, owner, source location and dest location
        for quant, dest_location_id in quants_suggested_locations.items():
            key = (quant.product_id.id, quant.package_id.id, quant.lot_id.id, quant.owner_id.id, quant.location_id.id, dest_location_id,quant.reservation_id.id)
            if qtys_grouped.get(key):
                qtys_grouped[key] += quant.qty
            else:
                qtys_grouped[key] = quant.qty

        # Do the same for the forced quantities (in cases of force_assign or incomming shipment for example)
        for move, qty in forced_qties.items():
            if qty <= 0:
                continue
            suggested_location_id = _picking_putaway_apply(move.product_id)
            key = (move.product_id.id, False, False, picking.owner_id.id, picking.location_id.id, suggested_location_id,move.id)
            if qtys_grouped.get(key):
                qtys_grouped[key] += qty
            else:
                qtys_grouped[key] = qty
        # Create the necessary operations for the grouped quants and remaining qtys
        uom_obj = self.pool.get('product.uom')
        prevals = {}
        for key, qty in qtys_grouped.items():
            product = self.pool.get("product.product").browse(cr, uid, key[0], context=context)
            uom_id = product.uom_id.id
            qty_uom = qty
            if product_uom.get(key[0]):
                uom_id = product_uom[key[0]].id
                qty_uom = uom_obj._compute_qty(cr, uid, product.uom_id.id, qty, uom_id)
            val_dict = {
                'picking_id': picking.id,
                'product_qty': qty_uom,
                'product_id': key[0],
                'package_id': key[1],
                'lot_id': key[2],
                'owner_id': key[3],
                'location_id': key[4],
                'location_dest_id': key[5],
                'product_uom_id': uom_id,
                'move_id':key[6],
            }
            if key[6] in prevals:
                prevals[key[6]].append(val_dict)
            else:
                prevals[key[6]] = [val_dict]
        # prevals var holds the operations in order to create them in the same order than the picking stock moves if possible
        processed_products = set()
        for move in [x for x in picking.move_lines if x.state not in ('done', 'cancel')]:
            if move.id not in processed_products:
                vals += prevals.get(move.id, [])
                processed_products.add(move.id)
        return vals
    

    #TODO : Fonction reprise complètement par Hiren pour pouvoir gérer les recéptions avec plusieurs lignes du même article
    def recompute_remaining_qty(self, cr, uid, picking, context=None):
        def _create_link_for_index(operation_id, index, product_id, qty_to_assign, move_id, quant_id=False):
            move_dict = prod2move_ids[move_id][index]
            qty_on_link = min(move_dict['remaining_qty'], qty_to_assign)
            self.pool.get('stock.move.operation.link').create(cr, uid, {'move_id': move_dict['move'].id, 'operation_id': operation_id, 'qty': qty_on_link, 'reserved_quant_id': quant_id}, context=context)
            if move_dict['remaining_qty'] == qty_on_link:
                prod2move_ids[move_id].pop(index)
            else:
                move_dict['remaining_qty'] -= qty_on_link
            return qty_on_link

        def _create_link_for_quant(operation_id, quant, qty, move_id):
            """create a link for given operation and reserved move of given quant, for the max quantity possible, and returns this quantity"""
            if not quant.reservation_id.id:
                return _create_link_for_product(operation_id, quant.product_id.id, qty, move_id)
            qty_on_link = 0
            for i in range(0, len(prod2move_ids[move_id])):
                if prod2move_ids[move_id][i]['move'].id != quant.reservation_id.id:
                    continue
                qty_on_link = _create_link_for_index(operation_id, i, quant.product_id.id, qty, move_id,quant_id=quant.id)
                break
            return qty_on_link

        def _create_link_for_product(operation_id, product_id, qty, move_id):
            '''method that creates the link between a given operation and move(s) of given product, for the given quantity.
            Returns True if it was possible to create links for the requested quantity (False if there was not enough quantity on stock moves)'''
            qty_to_assign = qty
            prod_obj = self.pool.get("product.product")
            product = prod_obj.browse(cr, uid, product_id)
            rounding = product.uom_id.rounding
            qtyassign_cmp = float_compare(qty_to_assign, 0.0, precision_rounding=rounding)
            if prod2move_ids.get(move_id):
                while prod2move_ids[move_id] and qtyassign_cmp > 0:
                    qty_on_link = _create_link_for_index(operation_id, 0, product_id, qty_to_assign, move_id, quant_id=False)
                    qty_to_assign -= qty_on_link
                    qtyassign_cmp = float_compare(qty_to_assign, 0.0, precision_rounding=rounding)
            return qtyassign_cmp == 0

        uom_obj = self.pool.get('product.uom')
        package_obj = self.pool.get('stock.quant.package')
        quant_obj = self.pool.get('stock.quant')
        link_obj = self.pool.get('stock.move.operation.link')
        quants_in_package_done = set()
        prod2move_ids = {}
        still_to_do = []
        #make a dictionary giving for each product, the moves and related quantity that can be used in operation links
        for move in [x for x in picking.move_lines if x.state not in ('done', 'cancel')]:
            if not prod2move_ids.get(move.id):
                prod2move_ids[move.id] = [{'move': move, 'remaining_qty': move.product_qty}]
            else:
                prod2move_ids[move.id].append({'move': move, 'remaining_qty': move.product_qty})
        need_rereserve = False
        #sort the operations in order to give higher priority to those with a package, then a serial number
        operations = picking.pack_operation_ids
        operations = sorted(operations, key=lambda x: ((x.package_id and not x.product_id) and -4 or 0) + (x.package_id and -2 or 0) + (x.lot_id and -1 or 0))
        #delete existing operations to start again from scratch
        links = link_obj.search(cr, uid, [('operation_id', 'in', [x.id for x in operations])], context=context)
        if links:
            link_obj.unlink(cr, uid, links, context=context)
        #1) first, try to create links when quants can be identified without any doubt
        for ops in operations:
            #for each operation, create the links with the stock move by seeking on the matching reserved quants,
            #and deffer the operation if there is some ambiguity on the move to select
            if ops.package_id and not ops.product_id:
                #entire package
                quant_ids = package_obj.get_content(cr, uid, [ops.package_id.id], context=context)
                for quant in quant_obj.browse(cr, uid, quant_ids, context=context):
                    remaining_qty_on_quant = quant.qty
                    if quant.reservation_id:
                        #avoid quants being counted twice
                        quants_in_package_done.add(quant.id)
                        qty_on_link = _create_link_for_quant(ops.id, quant, quant.qty, ops.move_id.id)
                        remaining_qty_on_quant -= qty_on_link
                    if remaining_qty_on_quant:
                        still_to_do.append((ops, quant.product_id.id, remaining_qty_on_quant))
                        need_rereserve = True
            elif ops.product_id.id:
                #Check moves with same product
                qty_to_assign = uom_obj._compute_qty_obj(cr, uid, ops.product_uom_id, ops.product_qty, ops.product_id.uom_id, context=context)
                for move_dict in prod2move_ids.get(ops.move_id.id, []):
                    move = move_dict['move']
                    for quant in move.reserved_quant_ids:
                        if not qty_to_assign > 0:
                            break
                        if quant.id in quants_in_package_done:
                            continue

                        #check if the quant is matching the operation details
                        if ops.package_id:
                            flag = quant.package_id and bool(package_obj.search(cr, uid, [('id', 'child_of', [ops.package_id.id])], context=context)) or False
                        else:
                            flag = not quant.package_id.id
                        flag = flag and ((ops.lot_id and ops.lot_id.id == quant.lot_id.id) or not ops.lot_id)
                        flag = flag and (ops.owner_id.id == quant.owner_id.id)
                        if flag:
                            max_qty_on_link = min(quant.qty, qty_to_assign)
                            qty_on_link = _create_link_for_quant(ops.id, quant, max_qty_on_link, ops.move_id.id)
                            qty_to_assign -= qty_on_link
                qty_assign_cmp = float_compare(qty_to_assign, 0, precision_rounding=ops.product_id.uom_id.rounding)
                if qty_assign_cmp > 0:
                    #qty reserved is less than qty put in operations. We need to create a link but it's deferred after we processed
                    #all the quants (because they leave no choice on their related move and needs to be processed with higher priority)
                    still_to_do += [(ops, ops.product_id.id, qty_to_assign)]
                    need_rereserve = True

        #2) then, process the remaining part
        all_op_processed = True
        for ops, product_id, remaining_qty in still_to_do:
            all_op_processed = _create_link_for_product(ops.id, product_id, remaining_qty,ops.move_id.id) and all_op_processed
        return (need_rereserve, all_op_processed)









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
                date_inv=move.picking_id.is_date_expedition
            context['date_inv']=date_inv
            invoices += self._invoice_create_line(cr, uid, moves, journal_id, type, context=context)
        return invoices


class stock_quant(models.Model):
    _inherit = "stock.quant"
    _order   = "product_id, location_id"

    is_mold_id          = fields.Many2one('is.mold'    , 'Moule'            , related='product_id.is_mold_id'         , readonly=True)


class stock_move(models.Model):
    _inherit = "stock.move"
    _order   = "date desc, id"
    is_dosmat_ctrl_qual           = fields.Char('Contrôle qualité', readonly=True)


    @api.multi
    def name_get(self):
        res=[]
        for obj in self:
            name=obj.product_id.is_code+u' / '+ u'qt='+str(obj.product_uom_qty) 
            if obj.picking_id:
                name=name + u' / bl='+str(obj.picking_id.name)
            if obj.origin:
                name=name + u' / '+str(obj.origin)
            name=name+u' / id='+str(obj.id)
            res.append((obj.id, name))
        return res


    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if name:
            try:
                id = int(name)
            except ValueError:
                id = 0
            if id>0:
                filtre=['|','|','|',('product_id.is_code','ilike', name),('picking_id.name','ilike', name),('origin','ilike', name),('id','=', name)]
            else:
                filtre=['|','|',('product_id.is_code','ilike', name),('picking_id.name','ilike', name),('origin','ilike', name)]
            ids = self.search(cr, user, filtre, limit=limit, context=context)
        else:
            ids = self.search(cr, user, args, limit=limit, context=context)
        result = self.name_get(cr, user, ids, context=context)
        return result





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
    def get_working_day(self, date, num_day, jours_fermes, leave_dates):
        """ Déterminer la date de livraison en fonction des jours de fermeture ou des jours de congés
        """
        if int(num_day) not in jours_fermes and date not in leave_dates:
            return date
        else:
            date = datetime.datetime.strptime(date, '%Y-%m-%d') + datetime.timedelta(days=1)
            date = date.strftime('%Y-%m-%d')
            num_day = time.strftime('%w', time.strptime(date, '%Y-%m-%d'))
            return self.get_working_day(date, num_day, jours_fermes, leave_dates)


    def _get_date_livraison(self,date_expedition):
        date_livraison=date_expedition
        for obj in self:
            date_livraison= self.env['res.partner'].get_date_livraison(obj.company_id, obj.partner_id, date_expedition)
        return date_livraison


#    def _get_date_livraison(self,date_expedition):
#        cr, uid, context = self.env.args
#        date_livraison=date_expedition
#        for obj in self:
#            if obj.partner_id:
#                res_partner = self.env['res.partner']
#                # jours de fermeture de la société
#                jours_fermes = res_partner.num_closing_days(obj.partner_id)
#                # Jours de congé de la société
#                leave_dates = res_partner.get_leave_dates(obj.partner_id)
#                # Délai de transport
#                delai_transport = obj.partner_id.is_delai_transport
#                date_livraison = datetime.datetime.strptime(date_livraison, '%Y-%m-%d') + datetime.timedelta(days=delai_transport)
#                # Reporter au premier jour ouvré disponible
#                date = date_livraison.strftime('%Y-%m-%d')
#                num_day = date_livraison.strftime('%w')
#                date_livraison = self.get_working_day(date, num_day, jours_fermes, leave_dates)
#            return date_livraison
#        return date_livraison


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
                    date_expedition = time.strftime('%Y-%m-%d')
                    date_livraison  = self._get_date_livraison(date_expedition)
                    values = {
                        'origin'             : move.origin,
                        'company_id'         : move.company_id and move.company_id.id or False,
                        'move_type'          : move.group_id and move.group_id.move_type or 'direct',
                        'partner_id'         : move.partner_id.id or False,
                        'picking_type_id'    : move.picking_type_id and move.picking_type_id.id or False,
                        'is_sale_order_id'   : sale_data and sale_data.id or False,
                        'is_transporteur_id' : sale_data and sale_data.is_transporteur_id.id or False,
                        'is_date_expedition' : date_expedition,
                        'is_date_livraison'  : date_livraison,
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
            #if float_compare(quantity_rest_uom, 0, precision_rounding=move.product_uom.rounding) == 0:
            #    quantity_rest=move.product_uom.rounding
            #TODO : Modif du 09/09/17 pour corriger un pb de division par 0
            if abs(quantity_rest)<0.00001:
                quantity_rest=0.00001
                
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


        #TODO : J'ai commenté ces lignes le 26/12/2017 pour ne pas réserver le stock sur les OF
        #if res:
        #    self.action_assign(cr, uid, res, context=context)


        #TODO : J'ai désactivé ce code car cela bloquait les homes flux
        #if prod_orders:
        #    production_obj.signal_workflow(cr, uid, list(prod_orders), 'button_produce')
        return res



class stock_production_lot(models.Model):
    _inherit = "stock.production.lot"
    _order="id desc"

    is_date_peremption = fields.Date("Date de péremption")
    is_lot_fournisseur = fields.Char("Lot fournisseur")




class stock_inventory(models.Model):
    _inherit = "stock.inventory"
    _order="date desc"



