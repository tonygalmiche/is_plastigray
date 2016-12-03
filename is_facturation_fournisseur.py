# -*- coding: utf-8 -*-
import datetime
from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning


class is_facturation_fournisseur(models.Model):
    _name = "is.facturation.fournisseur"
    _description = "Facturation fournisseur"

    name              = fields.Many2one('res.partner', 'Fournisseur'   , required=True)
    date_fin          = fields.Date('Date de fin'                      , required=True)
    total_ht          = fields.Float("Total HT"         , digits=(14,4), required=True)
    total_ht_calcule  = fields.Float("Total HT Calculé" , digits=(14,4), compute='_compute', readonly=True, store=False)
    ecart_ht          = fields.Float("Ecart HT"         , digits=(14,4), compute='_compute', readonly=True, store=False)
    total_ttc_calcule = fields.Float("Total TTC Calculé", digits=(14,4), compute='_compute', readonly=True, store=False)
    justification_id  = fields.Many2one('is.facturation.fournisseur.justification', 'Justification')
    line_ids          = fields.One2many('is.facturation.fournisseur.line', 'facturation_id', u"Lignes")
    state             = fields.Selection([('creation', u'Création'),('termine', u'Terminé')], u"État", readonly=True, select=True)

    def _date():
        now  = datetime.date.today()               # Date du jour
        date = now + datetime.timedelta(days=-1)   # Date -1
        return date.strftime('%Y-%m-%d')           # Formatage

    _defaults = {
        'date_fin':  _date(),
        'state'   : 'creation',
    }


    @api.depends('line_ids','total_ht')
    def _compute(self):
        for obj in self:
            ht=0
            ttc=0
            for line in obj.line_ids:
                if line.selection:
                    total=line.prix*line.quantite
                    ht=ht+total
                    ttc=ttc+total*(1+line.taxe_taux)
            obj.total_ht_calcule  = ht
            obj.ecart_ht          = obj.total_ht-ht
            obj.total_ttc_calcule = ttc


    @api.multi
    def cherche_receptions(self, partner_id, date_fin):
        cr=self._cr
        value = {}
        lines = []
        if partner_id and date_fin:
            sql="""
                select  sp.name, 
                        sp.note, 
                        sp.date_done, 
                        sm.product_id,
                        pt.is_ref_fournisseur,
                        sm.product_uom_qty,
                        sm.product_uom, 
                        sm.price_unit,
                        pot.tax_id,
                        at.amount,
                        sm.id
                from stock_picking sp inner join stock_move                sm on sp.id=sm.picking_id
                                      inner join product_product           pp on sm.product_id=pp.id
                                      inner join product_template          pt on pp.product_tmpl_id=pt.id 
                                      left outer join purchase_order_line pol on sm.purchase_line_id=pol.id
                                      left outer join purchase_order_taxe pot on pol.id=pot.ord_id
                                      left outer join account_tax          at on pot.tax_id=at.id
                where sm.state='done' 
                      and sm.invoice_state='2binvoiced' 
                      and sp.picking_type_id=1 """
            sql=sql+" and sp.partner_id="+str(partner_id)+" "
            sql=sql+" and sp.date_done<='"+str(date_fin)+" 23:59:59' "
            cr.execute(sql)
            for row in cr.fetchall():
                vals = {
                    'num_reception'     : row[0],
                    'num_bl_fournisseur': row[1],
                    'date_reception'    : row[2],
                    'product_id'        : row[3],
                    'ref_fournisseur'   : row[4],
                    'quantite'          : row[5],
                    'uom_id'            : row[6],
                    'prix'              : row[7],
                    'total'             : row[5]*row[7],
                    'taxe_id'           : row[8],
                    'taxe_taux'         : row[9],
                    'move_id'           : row[10],
                    'selection'         : True,
                }
                lines.append(vals)
        value.update({'line_ids': lines})
        return {'value': value}



    @api.multi
    def action_creer_facture(self):
        for obj in self:
            date_invoice=datetime.date.today().strftime('%Y-%m-%d')
            res=self.env['account.invoice'].onchange_partner_id('in_invoice', obj.name.id, date_invoice)
            vals=res['value']
            vals.update({
                'partner_id'  : obj.name.id,
                'account_id'  : obj.name.property_account_payable.id,
                'journal_id'  : 2,
                'type'        : 'in_invoice',
                'date_invoice': date_invoice,
            })
            lines = []
            for line in obj.line_ids:
                if line.selection:
                    product_id      = line.product_id.id
                    uom_id          = line.uom_id.id 
                    quantite        = line.quantite
                    name            = 'toto'
                    invoice_type    = 'in_invoice'
                    partner_id      = obj.name.id
                    fiscal_position = vals['fiscal_position']
                    invoice_line_tax_id=[]
                    if line.taxe_id:
                        invoice_line_tax_id.append((6,False,[line.taxe_id.id]))
                    if len(invoice_line_tax_id)==0:
                        invoice_line_tax_id=False
                    res=self.env['account.invoice.line'].product_id_change(product_id, uom_id, quantite, name, invoice_type, partner_id, fiscal_position)
                    v=res['value']
                    v.update({
                        'product_id'          : product_id,
                        'quantity'            : quantite,
                        'price_unit'          : line.prix,
                        'invoice_line_tax_id' : invoice_line_tax_id,
                        'is_document'         : line.move_id.purchase_line_id.order_id.is_document
                    })
                    lines.append([0,False,v]) 
            vals.update({
                'invoice_line': lines,
            })
            res=self.env['account.invoice'].create(vals)

            dummy, view_id = self.env['ir.model.data'].get_object_reference('account', 'invoice_supplier_form')
            obj.state='termine'

            #** Changement d'état des réceptions et des lignes *****************
            for line in obj.line_ids:
                line.move_id.invoice_state='invoiced'
                test=True
                for l in line.move_id.picking_id.move_lines:
                    if l.invoice_state=='2binvoiced':
                        test=False
                if test:
                    line.move_id.picking_id.invoice_state='invoiced'
            #*******************************************************************

            return {
                'name': "Facture Fournisseur",
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'account.invoice',
                'type': 'ir.actions.act_window',
                'res_id': res.id,
                'domain': '[]',
            }








class is_facturation_fournisseur_line(models.Model):
    _name='is.facturation.fournisseur.line'
    _order='id'

    facturation_id     = fields.Many2one('is.facturation.fournisseur', 'Facturation fournisseur', required=True, ondelete='cascade')
    num_reception      = fields.Char('N° de réception')
    num_bl_fournisseur = fields.Char('N° BL fournisseur')
    date_reception     = fields.Datetime('Date réception')
    product_id         = fields.Many2one('product.product', 'Article')
    ref_fournisseur    = fields.Char('Référence fournisseur')
    quantite           = fields.Float('Quantité', digits=(14,4))
    uom_id             = fields.Many2one('product.uom', 'Unité')
    prix               = fields.Float('Prix'    , digits=(14,4))
    total              = fields.Float('Total'   , digits=(14,4))
    taxe_id            = fields.Many2one('account.tax', 'Taxe')
    taxe_taux          = fields.Float('Taux')
    selection          = fields.Boolean('Sélection', default=True)
    move_id            = fields.Many2one('stock.move', 'Mouvement de stock')



class is_facturation_fournisseur_justification(models.Model):
    _name='is.facturation.fournisseur.justification'
    _order='name'

    name     = fields.Char('Justification')


