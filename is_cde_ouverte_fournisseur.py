# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning


class is_cde_ouverte_fournisseur(models.Model):
    _name='is.cde.ouverte.fournisseur'
    _order='partner_id'

    name          = fields.Char("N°", readonly=True)
    partner_id    = fields.Many2one('res.partner', 'Fournisseur'        , required=True)
    pricelist_id  = fields.Many2one('product.pricelist', 'Liste de prix', related='partner_id.property_product_pricelist_purchase', readonly=True)
    type_commande = fields.Selection([('ouverte', 'Commande ouverte'),('ferme', 'Commande ferme avec horizon.')], "Type de commande", required=True)
    sans_commande = fields.Selection([('oui', 'Oui'),('non', 'Non')], "Articles sans commandes", help="Imprimer dans les documents les articles sans commandes")
    commentaire   = fields.Text("Commentaire")
    product_ids   = fields.One2many('is.cde.ouverte.fournisseur.product', 'order_id', u"Articles")


    @api.model
    def create(self, vals):
        self.test_unique(vals['partner_id'])
        data_obj = self.env['ir.model.data']
        sequence_ids = data_obj.search([('name','=','is_cde_ouverte_fournisseur_seq')])
        if sequence_ids:
            sequence_id = data_obj.browse(sequence_ids[0].id).res_id
            vals['name'] = self.env['ir.sequence'].get_id(sequence_id, 'id')
        obj = super(is_cde_ouverte_fournisseur, self).create(vals)
        self.update_partner(obj)
        return obj


    @api.multi
    def write(self,vals):
        res=super(is_cde_ouverte_fournisseur, self).write(vals)
        for obj in self:
            self.update_partner(obj)
            self.test_unique(obj.partner_id.id)
        return res


    @api.multi
    def unlink(self):
        for obj in self:
            obj.partner_id.is_type_cde_fournisseur=False
        res=super(is_cde_ouverte_fournisseur, self).unlink()


    @api.multi
    def update_partner(self, obj):
        obj.partner_id.is_type_cde_fournisseur=obj.type_commande


    @api.multi
    def test_unique(self, partner_id):
        ids=self.env['is.cde.ouverte.fournisseur'].search([ ('partner_id', '=', partner_id) ])
        if len(ids)>1:
            raise Warning(u"Une commande ouverte existe déjà pour ce fournisseur !")


    @api.multi
    def integrer_commandes(self):
        cr = self._cr
        for obj in self:
            for product in obj.product_ids:
                product.imprimer=False

            #** Recherche du dernier numéro de BL ******************************
            for product in obj.product_ids:
                SQL="""
                    select sp.is_num_bl, sp.is_date_reception, sm.product_uom_qty
                    from stock_picking sp inner join stock_move sm on sm.picking_id=sp.id
                    where sm.product_id="""+str(product.product_id.id)+""" 
                          and sp.is_date_reception is not null
                          and sm.state='done' 
                    order by sp.is_date_reception desc, sm.date desc
                    limit 1
                """
                cr.execute(SQL)
                result = cr.fetchall()
                num_bl  = False
                date_bl = False
                qt_bl   = 0
                for row in result:
                    num_bl  = row[0]
                    date_bl = row[1]
                    qt_bl   = row[2]

                product.num_bl  = num_bl
                product.date_bl = date_bl
                product.qt_bl   = qt_bl
            #*******************************************************************

            for product in obj.product_ids:
                product.line_ids.unlink()
            for product in obj.product_ids:
                for row in self.env['mrp.prevision'].search([('type','=','sa'),('product_id','=',product.product_id.id)]):
                    vals={
                        'product_id'       : product.id,
                        'date'             : row.end_date,
                        'type_cde'         : 'prev',
                        'quantite'         : row.quantity,
                        'mrp_prevision_id' : row.id,
                    }
                    line=self.env['is.cde.ouverte.fournisseur.line'].create(vals)
                for row in self.env['purchase.order.line'].search([('state','=','confirmed'),('product_id','=',product.product_id.id)]):
                    vals={
                        'product_id'        : product.id,
                        'date'              : row.date_planned,
                        'type_cde'          : 'ferme',
                        'quantite'          : row.product_qty,
                        'purchase_order_id' : row.order_id.id,
                    }
                    line=self.env['is.cde.ouverte.fournisseur.line'].create(vals)



class is_cde_ouverte_fournisseur_product(models.Model):
    _name='is.cde.ouverte.fournisseur.product'
    _order='product_id'

    order_id      = fields.Many2one('is.cde.ouverte.fournisseur', 'Commande ouverte fournisseur', required=True, ondelete='cascade', readonly=True)
    product_id    = fields.Many2one('product.product', 'Article'  , required=True)
    uom_po_id     = fields.Many2one('product.uom', "Unité d'achat", related='product_id.uom_po_id', readonly=True)
    lot_appro     = fields.Float("Lot d'appro."                   , related='product_id.lot_mini' , readonly=True)
    prix_achat    = fields.Float("Prix d'achat")
    num_bl        = fields.Char("Dernier BL", readonly=True)
    date_bl       = fields.Date("Date BL"   , readonly=True)
    qt_bl         = fields.Float("Qt reçue" , readonly=True)
    imprimer      = fields.Boolean("A imprimer", help="Si cette case n'est pas cochée, l'article ne sera pas imprimé")
    line_ids      = fields.One2many('is.cde.ouverte.fournisseur.line'   , 'product_id', u"Commandes")


    @api.multi
    def onchange_product_id(self, partner_id, pricelist_id, product_id):
        if pricelist_id and product_id:
            product=self.env['product.product'].browse(product_id)
            prix_achat = self.pool.get('product.pricelist').price_get(self._cr, self._uid, [pricelist_id],
                    product_id, product.lot_mini, partner_id, self._context)[pricelist_id]
            vals={}
            vals['value']={}
            vals['value']['prix_achat'] = prix_achat
            return vals


class is_cde_ouverte_fournisseur_line(models.Model):
    _name='is.cde.ouverte.fournisseur.line'
    _order='date'

    product_id        = fields.Many2one('is.cde.ouverte.fournisseur.product', 'Commande ouverte fournisseur', required=True, ondelete='cascade', readonly=True)
    date              = fields.Date("Date Commande")
    type_cde          = fields.Selection([('ferme', u'Ferme'),('prev', u'Prévisionnel')], u"Type de commande", select=True)
    quantite          = fields.Float("Quantité")
    mrp_prevision_id  = fields.Many2one('mrp.prevision' , 'SA')
    purchase_order_id = fields.Many2one('purchase.order', 'Commande')




