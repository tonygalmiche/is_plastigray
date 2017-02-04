# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning
import time
from datetime import date, datetime
from ftplib import FTP
import os


class is_account_folio(models.Model):
    _name  = 'is.account.folio'
    _order = 'name desc'

    name          = fields.Char('N° de Folio'              , readonly=True)
    date_creation = fields.Date("Date de création"         , readonly=True)
    createur_id   = fields.Many2one('res.users', 'Créé par', readonly=True)
    invoice_ids   = fields.One2many('account.invoice', 'is_folio_id', 'Factures', readonly=True)

    def _date_creation():
        return date.today() # Date du jour

    _defaults = {
        'date_creation': _date_creation(),
        'createur_id': lambda obj, cr, uid, ctx=None: uid,
    }


    @api.model
    def create(self, vals):
        data_obj = self.env['ir.model.data']
        sequence_ids = data_obj.search([('name','=','seq_is_account_folio')])
        if len(sequence_ids)>0:
            sequence_id = sequence_ids[0].res_id
            vals['name'] = self.env['ir.sequence'].get_id(sequence_id, 'id')
        res = super(is_account_folio, self).create(vals)
        return res


class account_move_line(models.Model):
    _inherit = "account.move.line"
    is_account_invoice_line_id = fields.Many2one('account.invoice.line', 'Ligne de facture')


class account_invoice(models.Model):
    _inherit = 'account.invoice'
    _order   = 'id desc'

    is_document       = fields.Char('Document'     , help="Ce champ est utilisé dans les factures diverses pour saisir le moule ou le n° d'investissement")
    is_num_cde_client = fields.Char('N° Cde Client', help="Ce champ est utilisé dans les factures diverses sans commande client dans Odoo")
    is_num_bl_manuel  = fields.Char('N° BL manuel' , help="Ce champ est utilisé dans les factures diverses sans bon de livraison dans Odoo")
    is_escompte       = fields.Float("Escompte", compute='_compute')
    is_tva            = fields.Float("TVA"     , compute='_compute', help="Taxes sans l'escompte")
    is_folio_id       = fields.Many2one('is.account.folio', 'Folio')
    is_bon_a_payer    = fields.Boolean("Bon à payer", default=True)
    is_type_facture   = fields.Selection([('standard', u'Standard'),('diverse', u'Diverse')], u"Type de facture", default='standard', select=True)


    def _compute(self):
        for obj in self:
            escompte = tva = 0
            for tax in obj.tax_line:
                if tax.account_id.code=='665000':
                    escompte=escompte+tax.amount
                else:
                    tva=tva++tax.amount
            obj.is_escompte = escompte
            obj.is_tva      = tva



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


    @api.model
    def line_get_convert(self, line, part, date):
        '''
        Permet d'ajouter dans la table account_move_line le lien vers la ligne de facture,
        pour récupérer en particulier la section analytique
        '''
        res=super(account_invoice, self).line_get_convert(line, part, date)
        res['is_account_invoice_line_id']=line.get('invl_id', False)
        return res


    @api.model
    def _prepare_refund(self, invoice, date=None, period_id=None, description=None, journal_id=None):
        """
        Permet d'ajouter les champs personnalisés de la facture sur l'avoir
        """
        res=super(account_invoice, self)._prepare_refund(invoice, date, period_id, description, journal_id)
        res['is_document']=invoice.is_document
        res['is_num_cde_client']=invoice.is_num_cde_client
        res['is_num_bl_manuel']=invoice.is_num_bl_manuel

        return res


#    @api.multi
#    def initialisation_mouvement_stock(self):
#        for obj in self:
#            factures = self.env['is.facturation.fournisseur'].search([
#                ('name'        , '=', obj.partner_id.id),
#                ('date_facture', '=', obj.date_invoice),
#                ('num_facture' , '=', obj.supplier_invoice_number),
#            ])
#            for facture in factures:
#                for line in obj.invoice_line:
#                    lignes = self.env['is.facturation.fournisseur.line'].search([
#                        ('facturation_id', '=', facture.id),
#                        ('selection'     , '=', True),
#                        ('product_id'    , '=', line.product_id.id),
#                        ('quantite'      , '=', line.quantity),
#                    ])
#                    for ligne in lignes:
#                        line.is_move_id=ligne.move_id


class account_invoice_line(models.Model):
    _inherit = "account.invoice.line"

    is_section_analytique_id = fields.Many2one('is.section.analytique', 'Section analytique')
    is_move_id               = fields.Many2one('stock.move', 'Mouvement de stock')
    is_document              = fields.Char("Document (N° de dossier)")

    @api.multi
    def product_id_change(self, product_id, uom_id, qty=0, name='', type='out_invoice',
            partner_id=False, fposition_id=False, price_unit=False, currency_id=False,
            company_id=None):

        res=super(account_invoice_line, self).product_id_change(product_id, uom_id, qty, name, type,
            partner_id, fposition_id, price_unit, currency_id,company_id)

        #** Recherche de la section analytique *********************************
        if product_id:
            product = self.env['product.product'].browse(product_id)
            is_section_analytique_id=product.is_section_analytique_id.id or False
            res['value']['is_section_analytique_id']=is_section_analytique_id
        #***********************************************************************

        #** Recherche prix dans liste de prix pour la date et qt ***************
        partner = self.env['res.partner'].browse(partner_id)
        pricelist = partner.property_product_pricelist.id
        if product_id:
            date = time.strftime('%Y-%m-%d',time.gmtime()) # Date du jour
            if pricelist:
                ctx = dict(
                    self._context,
                    uom=uom_id,
                    date=date,
                )
                price_unit = self.pool.get('product.pricelist').price_get(self._cr, self._uid, [pricelist],
                        product_id, qty or 1.0, partner_id, ctx)[pricelist]
            res['value']['price_unit']=price_unit
        #***********************************************************************

        return res


