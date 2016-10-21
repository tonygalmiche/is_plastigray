# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _


class account_invoice(models.Model):
    _inherit = "account.invoice"

    is_document       = fields.Char('Document'     , help="Ce champ est utilisé dans les factures diverses pour saisir le moule ou le n° d'investissement")
    is_num_cde_client = fields.Char('N° Cde Client', help="Ce champ est utilisé dans les factures diverses sans commande client dans Odoo")
    is_num_bl_manuel  = fields.Char('N° BL manuel' , help="Ce champ est utilisé dans les factures diverses sans bon de livraison dans Odoo")


    @api.multi
    def invoice_print(self):
        assert len(self) == 1, 'This option should only be used for a single id at a time.'
        self.sent = True
        return self.env['report'].get_action(self, 'is_plastigray.is_report_invoice')



    @api.multi
    def action_move_create(self):
        super(account_invoice, self).action_move_create()
        self.escompte()

    @api.multi
    def button_reset_taxes(self):
        res=super(account_invoice, self).button_reset_taxes()
        self.escompte()
        return res

    @api.multi
    def escompte(self):
        for obj in self:
            #Suppression des lignes d'escomptes
            for l in obj.tax_line:
                if l.name=='Escompte' or l.name=='TVA sur escompte':
                    l.unlink()
            if obj.partner_id.is_escompte:
                #Recherche du total HT
                ht=0.0
                tax_id=False
                for l in obj.invoice_line:
                    ht=ht+l.price_subtotal
                    if l.invoice_line_tax_id:
                        tax_id=l.invoice_line_tax_id[0]
                #Escompte
                tax_obj = self.env['account.invoice.tax']
                taux=obj.partner_id.is_escompte.taux/100
                tax_vals={
                    'invoice_id': obj.id,
                    'name': 'Escompte',
                    'account_id': obj.partner_id.is_escompte.compte.id,
                    'base': ht,
                    'amount': -ht*taux
                }
                tax_obj.create(tax_vals)
                #TVA sur Escompte
                if tax_id:
                    tax_vals={
                        'invoice_id': obj.id,
                        'name': 'TVA sur escompte',
                        'account_id': tax_id.account_collected_id.id,
                        'base': ht*taux,
                        'amount': -ht*taux*tax_id.amount
                    }
                    tax_obj.create(tax_vals)

class account_invoice_line(models.Model):
    _inherit = "account.invoice.line"

    is_section_analytique_id = fields.Many2one('is.section.analytique', 'Section analytique')
    is_move_id               = fields.Many2one('stock.move', 'Mouvement de stock')

    @api.multi
    def product_id_change(self, product, uom_id, qty=0, name='', type='out_invoice',
            partner_id=False, fposition_id=False, price_unit=False, currency_id=False,
            company_id=None):
        res=super(account_invoice_line, self).product_id_change(product, uom_id, qty, name, type,
            partner_id, fposition_id, price_unit, currency_id,company_id)
        if product:
            product = self.env['product.product'].browse(product)
            is_section_analytique_id=product.is_section_analytique_id.id or False
            res['value']['is_section_analytique_id']=is_section_analytique_id
        return res


