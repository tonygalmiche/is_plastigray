# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning


#TODO : 



class is_cde_ouverte_fournisseur(models.Model):
    _name='is.cde.ouverte.fournisseur'
    _order='partner_id,product_id'

    name          = fields.Char("N°", readonly=True)
    partner_id    = fields.Many2one('res.partner', 'Fournisseur'        , required=True)
    product_id    = fields.Many2one('product.product', 'Article'        , required=True)
    uom_po_id     = fields.Many2one('product.uom', "Unité d'achat"      , related='product_id.uom_po_id'                          , readonly=True)
    pricelist_id  = fields.Many2one('product.pricelist', 'Liste de prix', related='partner_id.property_product_pricelist_purchase', readonly=True)
    commentaire   = fields.Text("Commentaire")
    line_ids      = fields.One2many('is.cde.ouverte.fournisseur.line'   , 'order_id', u"Commandes")


    @api.model
    def create(self, vals):
        self.test_unique(vals['partner_id'], vals['product_id'])
        data_obj = self.env['ir.model.data']
        sequence_ids = data_obj.search([('name','=','is_cde_ouverte_fournisseur_seq')])
        if sequence_ids:
            sequence_id = data_obj.browse(sequence_ids[0].id).res_id
            vals['name'] = self.env['ir.sequence'].get_id(sequence_id, 'id')
        res = super(is_cde_ouverte_fournisseur, self).create(vals)
        return res


    @api.multi
    def write(self,vals):
        res=super(is_cde_ouverte_fournisseur, self).write(vals)
        for obj in self:
            self.test_unique(obj.partner_id.id, obj.product_id.id)
        return res


    @api.multi
    def test_unique(self, partner_id, product_id):
        ids=self.env['is.cde.ouverte.fournisseur'].search([ ('partner_id', '=', partner_id),('product_id', '=', product_id) ])
        if len(ids)>1:
            raise Warning(u"Une commande ouverte existe déjà pour ce fournisseur !")


    @api.multi
    def integrer_commandes(self):
        for obj in self:
            obj.line_ids.unlink()
            for row in self.env['mrp.prevision'].search([('type','=','sa'),('product_id','=',obj.product_id.id)]):
                vals={
                    'order_id'         : obj.id,
                    'date'             : row.end_date,
                    'type_cde'         : 'prev',
                    'quantite'         : row.quantity,
                    'mrp_prevision_id' : row.id,
                }
                line=self.env['is.cde.ouverte.fournisseur.line'].create(vals)
            for row in self.env['purchase.order.line'].search([('state','=','draft'),('product_id','=',obj.product_id.id)]):
                vals={
                    'order_id'          : obj.id,
                    'date'              : row.date_planned,
                    'type_cde'          : 'ferme',
                    'quantite'          : row.product_qty,
                    'purchase_order_id' : row.order_id.id,
                }
                line=self.env['is.cde.ouverte.fournisseur.line'].create(vals)


class is_cde_ouverte_fournisseur_line(models.Model):
    _name='is.cde.ouverte.fournisseur.line'
    _order='date'

    order_id          = fields.Many2one('is.cde.ouverte.fournisseur', 'Commande ouverte fournisseur', required=True, ondelete='cascade', readonly=True)
    date              = fields.Date("Date Commande")
    type_cde          = fields.Selection([('ferme', u'Ferme'),('prev', u'Prévisionnel')], u"Type de commande", select=True)
    quantite          = fields.Float("Quantité")
    mrp_prevision_id  = fields.Many2one('mrp.prevision' , 'SA')
    purchase_order_id = fields.Many2one('purchase.order', 'Commande')








