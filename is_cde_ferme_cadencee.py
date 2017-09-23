# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning


class is_cde_ferme_cadencee(models.Model):
    _name='is.cde.ferme.cadencee'
    _order='name desc'

    name          = fields.Char("N° de commande ferme cadencée", readonly=True)
    partner_id    = fields.Many2one('res.partner'    , 'Fournisseur', required=True)
    is_livre_a_id = fields.Many2one('res.partner', 'Livrer à', related='partner_id.is_livre_a_id')
    product_id    = fields.Many2one('product.product', u"Article"   , required=True)

    order_ids     = fields.One2many('is.cde.ferme.cadencee.order', 'cfc_id', u"Commandes")

    @api.model
    def create(self, vals):

        data_obj = self.env['ir.model.data']
        sequence_ids = data_obj.search([('name','=','is_cde_ferme_cadencee_seq')])
        if sequence_ids:
            sequence_id = data_obj.browse(sequence_ids[0].id).res_id
            vals['name'] = self.env['ir.sequence'].get_id(sequence_id, 'id')
        obj = super(is_cde_ferme_cadencee, self).create(vals)
        self.verification_saisies(obj)
        return obj



    @api.multi
    def write(self,vals):
        res=super(is_cde_ferme_cadencee, self).write(vals)
        for obj in self:
            self.verification_saisies(obj)
        return res


    @api.multi
    def verification_saisies(self, obj):
        print obj
        for line in obj.order_ids:
            nb=len(line.order_id.order_line)
            if nb!=1:
                raise Warning(u"La commande "+str(line.order_id.name)+u" à "+str(nb)+u" lignes")
            for row in line.order_id.order_line:
                if row.product_id!=obj.product_id:
                    raise Warning(u"L'article de la commande "+str(line.order_id.name)+u" ne correspond pas à l'article indiqué")


        #ids=self.env['is.cde.ouverte.fournisseur'].search([ ('partner_id', '=', partner_id) ])
        #if len(ids)>1:
        #    raise Warning(u"Une commande ouverte existe déjà pour ce fournisseur !")


    @api.multi
    def actualiser_commandes(self):
        cr = self._cr
        for obj in self:
            for order in obj.order_ids:
                #** Recherche du dernier numéro de BL **************************
                SQL="""
                    select sp.is_num_bl, sp.is_date_reception, sm.product_uom_qty
                    from stock_picking sp inner join stock_move sm on sm.picking_id=sp.id
                    where 
                        sm.product_id="""+str(obj.product_id.id)+""" and
                        sp.is_date_reception is not null and
                        sm.state='done' and
                        sp.picking_type_id=1 and 
                        sp.partner_id="""+str(obj.partner_id.id)+""" and
                        sp.is_purchase_order_id="""+str(order.order_id.id)+""" 
                    order by sp.is_date_reception desc, sm.date desc
                    limit 1
                """
                cr.execute(SQL)
                result = cr.fetchall()
                num_bl  = False
                date_bl = False
                for row in result:
                    num_bl  = row[0]
                    date_bl = row[1]
                #***************************************************************

                #** Recherche du total réceptionné *****************************
                SQL="""
                    select sum(sm.product_uom_qty)
                    from stock_picking sp inner join stock_move sm on sm.picking_id=sp.id
                    where 
                        sm.product_id="""+str(obj.product_id.id)+""" and
                        sp.is_date_reception is not null and
                        sm.state='done' and
                        sp.picking_type_id=1 and 
                        sp.partner_id="""+str(obj.partner_id.id)+""" and
                        sp.is_purchase_order_id="""+str(order.order_id.id)+""" 
                    limit 1
                """
                cr.execute(SQL)
                result = cr.fetchall()
                qt_rcp = 0
                for row in result:
                    qt_rcp  = row[0]
                #***************************************************************
                order.num_bl   = num_bl
                order.date_bl  = date_bl
                order.qt_rcp   = qt_rcp
                order.qt_reste = order.product_qty-qt_rcp


class is_cde_ferme_cadencee_order(models.Model):
    _name='is.cde.ferme.cadencee.order'
    _order='date_planned'

    @api.depends('order_id')
    def _compute(self):
        for obj in self:
            if obj.order_id:
                for line in obj.order_id.order_line:
                    obj.date_planned = line.date_planned
                    obj.product_qty  = line.product_qty
                    obj.product_uom  = line.product_uom

    cfc_id       = fields.Many2one('is.cde.ferme.cadencee', 'Commande ferme cadencée', required=True, ondelete='cascade', readonly=True)
    order_id     = fields.Many2one('purchase.order', 'Commande Fournisseur', required=True)
    date_planned = fields.Date("Date prévue"              , compute='_compute', readonly=True, store=True)
    product_uom  = fields.Many2one('product.uom', 'Unité' , compute='_compute', readonly=True, store=True)
    product_qty  = fields.Float("Quantité commandée"      , compute='_compute', readonly=True, store=True)

    qt_rcp       = fields.Float("Quantité réceptionnée", readonly=True)
    qt_reste     = fields.Float("Reste à réceptionner" , readonly=True)
    num_bl       = fields.Char("Dernier BL"            , readonly=True)
    date_bl      = fields.Date("Date BL"               , readonly=True)






