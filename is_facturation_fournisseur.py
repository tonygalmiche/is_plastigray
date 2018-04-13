# -*- coding: utf-8 -*-
import datetime
from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning
import math


class is_facturation_fournisseur(models.Model):
    _name = "is.facturation.fournisseur"
    _description = "Facturation fournisseur"
    _order='id desc'

    afficher_lignes     = fields.Selection([('oui', u'Oui'),('non', u'Non')], u"Afficher les lignes")
    name                = fields.Many2one('res.partner', 'Fournisseur à facturer', required=True)
    partner_ids         = fields.Many2many('res.partner', id1='facturation_id', id2='partner_id', string='Autres fournisseurs')
    date_fin            = fields.Date('Date de fin'                      , required=True)
    date_facture        = fields.Date('Date facture fournisseur'         , required=True)
    num_facture         = fields.Char('N° facture fournisseur'           , required=True)
    total_ht            = fields.Float("Total HT"         , digits=(14,2), required=True)
    total_ht_calcule    = fields.Float("Total HT Calculé" , digits=(14,2), compute='_compute', readonly=True, store=False)
    ecart_ht            = fields.Float("Ecart HT"         , digits=(14,2), compute='_compute', readonly=True, store=False)
    ecart_ht_compte_id  = fields.Many2one('product.product', "Compte d'écart HT")
    total_tva           = fields.Float("Total TVA"         , digits=(14,2))
    total_tva_calcule   = fields.Float("Total TVA Calculé" , digits=(14,2), compute='_compute', readonly=True, store=False)
    ecart_tva           = fields.Float("Ecart TVA"         , digits=(14,2), compute='_compute', readonly=True, store=False)
    ecart_tva_compte_id = fields.Many2one('product.product', "Compte d'écart TVA")
    total_ttc_calcule   = fields.Float("Total TTC Calculé", digits=(14,2), compute='_compute', readonly=True, store=False)
    justification_id    = fields.Many2one('is.facturation.fournisseur.justification', 'Justification')
    bon_a_payer         = fields.Boolean("Bon à payer", compute='_compute', readonly=True, store=False)
    forcer_bon_a_payer  = fields.Selection([('oui', u'Bon à payer = Oui'),('non', u'Bon à payer = Non')], "Forcer bon à payer")
    is_masse_nette      = fields.Float("Masse nette (Kg)")



    line_ids            = fields.One2many('is.facturation.fournisseur.line', 'facturation_id', u"Lignes")
    state               = fields.Selection([('creation', u'Création'),('termine', u'Terminé')], u"État", readonly=True, select=True)

    def _date():
        now  = datetime.date.today()               # Date du jour
        date = now + datetime.timedelta(days=0)    # Date +0
        return date.strftime('%Y-%m-%d')           # Formatage

    _defaults = {
        'afficher_lignes': 'oui',
        'date_fin'       :  _date(),
        'state'          : 'creation',
    }


    @api.depends('line_ids','total_ht','total_tva')
    def _compute(self):
        for obj in self:
            ht=ttc=tva=0
            for line in obj.line_ids:
                if line.selection:
                    #total=math.ceil(100*line.prix*line.quantite)/100
                    total=math.ceil(100.0*round(line.quantite*line.prix,2))/100.0
                    ht=ht+total
                    tva=tva+total*line.taxe_taux
                    ttc=ttc+total*(1+line.taxe_taux)
            ht  = round(ht,2)
            tva = round(tva,2)
            ttc = round(ttc,2)
            ecart_ht  = round(obj.total_ht-ht,2)
            ecart_tva = round(obj.total_tva-tva,2)
            bon_a_payer=True
            if ecart_ht or ecart_tva:
                bon_a_payer=False
            obj.total_ht_calcule  = ht
            obj.ecart_ht          = ecart_ht
            obj.total_tva_calcule = tva
            obj.ecart_tva         = ecart_tva
            obj.total_ttc_calcule = ttc

            #Si prix modifié sur les lignes, bon_a_payer=False
            for line in obj.line_ids:
                if line.selection:
                    if round(line.prix,4)!=round(line.prix_origine,4):
                        bon_a_payer=False
            obj.bon_a_payer       = bon_a_payer

    @api.multi
    def cherche_receptions(self, partner_id, partner_ids, date_fin):
        ids=partner_ids[0][2]
        ids.append(partner_id)
        partners=[]
        for id in ids:
            partners.append(str(id))
        cr=self._cr
        value = {}
        lines = []
        if partner_id and date_fin:
            sql="""
                select  sp.name, 
                        sp.is_num_bl, 
                        sp.is_date_reception, 
                        sm.product_id,
                        pt.is_ref_fournisseur,

                        round(sm.product_uom_qty-coalesce((select sum(quantity) from account_invoice_line ail where ail.is_move_id=sm.id ),0),4),
                        sm.product_uom, 
                        pol.price_unit,
                        sm.id,
                        pol.id,
                        sm.name as description
                from stock_picking sp inner join stock_move                sm on sp.id=sm.picking_id
                                      inner join product_product           pp on sm.product_id=pp.id
                                      inner join product_template          pt on pp.product_tmpl_id=pt.id 
                                      left outer join purchase_order_line pol on sm.purchase_line_id=pol.id
                where 
                    sm.state='done' and 
                    sp.state='done' and
                    round(sm.product_uom_qty-coalesce((select sum(quantity) from account_invoice_line ail where ail.is_move_id=sm.id ),0),4)>0 and 
                    sp.picking_type_id=1 and
                    pt.is_facturable='t'
            """
            sql=sql+" and sp.partner_id in("+','.join(partners)+") "
            sql=sql+" and sp.is_date_reception<='"+str(date_fin)+"' "
            sql=sql+' order by sp.name, pol.id '
            cr.execute(sql)
            result=cr.fetchall()
            for row in result:
                #** Recherche des taxes ****************************************
                taxe_ids  = []
                taxe_taux = 0
                pol_id=row[9]
                if pol_id:
                    sql="""
                        select pot.tax_id, at.amount
                        from purchase_order_taxe pot left outer join account_tax at on pot.tax_id=at.id 
                        where pot.ord_id="""+str(pol_id)
                    cr.execute(sql)
                    result2=cr.fetchall()
                    for row2 in result2:
                        taxe_ids.append(row2[0])
                        taxe_taux=taxe_taux+row2[1]
                #***************************************************************

                #** Recherche du compte d'achat associé au mouvement de stock **
                move_id=row[8]
                move=self.env['stock.move'].browse(move_id)

                account_id = move.product_id.property_account_expense.id
                #***************************************************************

                vals = {
                    'num_reception'     : row[0],
                    'num_bl_fournisseur': row[1],
                    'date_reception'    : row[2],
                    'product_id'        : row[3],
                    'description'       : row[10],
                    'account_id'        : account_id,
                    'ref_fournisseur'   : row[4],
                    'quantite'          : row[5],
                    'uom_id'            : row[6],
                    'prix'              : row[7],
                    'prix_origine'      : row[7],
                    'total'             : row[5]*(row[7] or 0),
                    'taxe_ids'          : [(6,0,taxe_ids)],
                    'taxe_taux'         : taxe_taux,
                    'move_id'           : row[8],
                    'selection'         : False,
                }
                lines.append(vals)
        value.update({'line_ids': lines})
        return {'value': value}


    @api.multi
    def action_afficher_lignes(self):
        for obj in self:
            view_id=self.env.ref('is_plastigray.is_facturation_fournisseur_line_tree_view')
            return {
                'name': u'Lignes',
                'view_mode': 'tree',
                'view_type': 'form',
                'view_id': view_id.id,
                'res_model': 'is.facturation.fournisseur.line',
                'domain': [
                    ('facturation_id','=',obj.id),
                ],
                'type': 'ir.actions.act_window',
                'limit': 1000,
            }


    @api.multi
    def action_creer_facture(self):
        for obj in self:
            bon_a_payer=obj.bon_a_payer
            if obj.forcer_bon_a_payer=='oui':
                bon_a_payer=True
            if obj.forcer_bon_a_payer=='non':
                bon_a_payer=False
            date_invoice=datetime.date.today().strftime('%Y-%m-%d')
            res=self.env['account.invoice'].onchange_partner_id('in_invoice', obj.name.id, date_invoice)
            vals=res['value']
            vals.update({
                'partner_id'  : obj.name.id,
                'account_id'  : obj.name.property_account_payable.id,
                'journal_id'  : 2,
                'type'        : 'in_invoice',
                'date_invoice': obj.date_facture,
                'supplier_invoice_number': obj.num_facture,
                'is_bon_a_payer': bon_a_payer,
                'is_masse_nette': obj.is_masse_nette,
            })
            lines = []
            invoice_line_tax_id=[]
            for line in obj.line_ids:
                if line.selection:
                    product_id      = line.product_id.id
                    description     = line.description
                    uom_id          = line.uom_id.id 
                    quantite        = line.quantite
                    name            = line.product_id.name
                    invoice_type    = 'in_invoice'
                    partner_id      = obj.name.id
                    fiscal_position = vals['fiscal_position']

                    invoice_line_tax_id=[]
                    for taxe_id in line.taxe_ids:
                        invoice_line_tax_id.append(taxe_id.id)

                    if len(invoice_line_tax_id)==0:
                        invoice_line_tax_id=False
                    res=self.env['account.invoice.line'].product_id_change(product_id, uom_id, quantite, name, invoice_type, partner_id, fiscal_position)
                    v=res['value']

                    is_document=line.move_id.purchase_line_id.is_num_chantier
                    if is_document==False:
                        is_document=line.move_id.purchase_line_id.order_id.is_document

                    v.update({
                        'product_id'          : product_id,
                        'name'                : description,
                        'quantity'            : quantite,
                        'price_unit'          : line.prix,
                        'invoice_line_tax_id' : [(6,0,invoice_line_tax_id)],
                        'is_document'         : is_document,
                        'is_move_id'          : line.move_id.id,
                    })
                    lines.append([0,False,v]) 


            #** Ajout de la ligne pour l'écart de facturation ******************
            if obj.ecart_ht_compte_id:
                product_id      = obj.ecart_ht_compte_id.id
                uom_id          = obj.ecart_ht_compte_id.uom_id.id
                name            = obj.ecart_ht_compte_id.name
                invoice_type    = 'in_invoice'
                partner_id      = obj.name.id
                fiscal_position = vals['fiscal_position']
                res=self.env['account.invoice.line'].product_id_change(product_id, uom_id, quantite, name, invoice_type, partner_id, fiscal_position)
                v=res['value']
                v.update({
                    'product_id'          : product_id,
                    'quantity'            : 1,
                    'price_unit'          : obj.ecart_ht,
                    'invoice_line_tax_id' : [(6,0,invoice_line_tax_id)],
                })
                lines.append([0,False,v]) 
            #*******************************************************************

            vals.update({
                'invoice_line': lines,
            })
            res=self.env['account.invoice'].create(vals)
            res.button_reset_taxes()
            #res.repartir_frais_de_port()

            dummy, view_id = self.env['ir.model.data'].get_object_reference('account', 'invoice_supplier_form')
            obj.state='termine'

            #** Changement d'état des réceptions et des lignes *****************
            for line in obj.line_ids:
                if line.selection:
                    if line.move_id:
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


    @api.depends('quantite','prix','taxe_ids')
    def _compute(self):
        for obj in self:
            obj.total=math.ceil(100.0*round(obj.quantite*obj.prix,2))/100.0
            taxe_taux=0
            for taxe in obj.taxe_ids:
                taxe_taux=taxe_taux+taxe.amount
            obj.taxe_taux=taxe_taux


    facturation_id     = fields.Many2one('is.facturation.fournisseur', 'Facturation fournisseur', required=True, ondelete='cascade')
    num_reception      = fields.Char('N° de réception')
    num_bl_fournisseur = fields.Char('N° BL fournisseur')
    date_reception     = fields.Date('Date réception')
    product_id         = fields.Many2one('product.product', 'Article')
    description        = fields.Char('Description')
    account_id         = fields.Many2one('account.account', 'Compte')
    ref_fournisseur    = fields.Char('Référence fournisseur')
    quantite           = fields.Float('Reste à facturer', digits=(14,4))
    uom_id             = fields.Many2one('product.uom', 'Unité')
    prix               = fields.Float('Prix'          , digits=(14,4))
    prix_origine       = fields.Float("Prix d'origine", digits=(14,4))
    total              = fields.Float("Total" , digits=(14,4), compute='_compute', readonly=True, store=False)
    taxe_ids           = fields.Many2many('account.tax', 'is_facturation_fournisseur_line_taxe_ids', 'facturation_id', 'taxe_id', 'Taxes')
    taxe_taux          = fields.Float('Taux', compute='_compute', readonly=True, store=False)
    selection          = fields.Boolean('Sélection', default=True)
    move_id            = fields.Many2one('stock.move', 'Mouvement de stock')


    @api.multi
    def action_cocher_lignes(self):
        for obj in self:
            obj.selection=True


    @api.multi
    def action_decocher_lignes(self):
        for obj in self:
            obj.selection=False



class is_facturation_fournisseur_justification(models.Model):
    _name='is.facturation.fournisseur.justification'
    _order='name'

    name        = fields.Char('Justification')
    commentaire = fields.Char('Commentaire')


