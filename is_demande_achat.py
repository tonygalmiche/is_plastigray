# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _
import werkzeug
from urlparse import urljoin

class is_demande_achat(models.Model):
    _name='is.demande.achat'

    name               = fields.Char(string='N°DA')
    demandeur_id       = fields.Many2one('res.users', string='Demandeur')
    acheteur_id        = fields.Many2one('res.users', string='Acheteur')
    type_da            = fields.Selection([('achat','Achat'),('investissement','Investissement')], string='Type', select=True)
    sous_type_da       = fields.Selection([('divers','Divers'),
                                     ('ei','E.I.'),
                                     ('preserie','Pre-Serie'),
                                     ('serie','Serie'),
                                     ], string='Sous Type', select=True)
    delai_souhaite     = fields.Date(string='Délai Liv souhaité')
    lieu_livraison     = fields.Many2one('is.database', string='Lieu de Livraison')
    lieu_autre         = fields.Char('Lieu (Autre)')
    fournisseur_id     = fields.Many2one('res.partner', string='Fournisseur', domain=[('supplier','=',True),('is_company','=',True)])
    fournisseur_autre  = fields.Char('Fournisseur (Autre)')
    piece_jointe       = fields.Selection([('acceptation_ei','Acceptation E.I.'),
                                     ('plan','Plan'),
                                     ('prototype','Prototype'),
                                     ('cdc','CDC'),
                                     ('cahier_numerique','Cahier Numerique'),
                                     ('dfn_2d_3d','DFN 2D-3D'),
                                     ('autre','Autre'),
                                     ], string='Pièce Jointe', select=True)
    piece_jointe_autre = fields.Char('Piece Jointe (Autre)')
    equipement_mesure  = fields.Selection([('oui','Oui'),
                                     ('non','Non'),
                                     ], string='Equipement de mesure à étalonner', select=True)
    fiche_securite     = fields.Selection([('oui','Oui'),
                                     ('non','Non'),
                                     ], string='Demander la fiche de données de sécurité au fournisseur', select=True)
    commentaire        = fields.Char('Commentaire')
    is_pos             = fields.Boolean('Is Pos ?')
    line_ids           = fields.One2many('is.demande.achat.line', 'achat_id', string='Lignes')
    po_id              = fields.Many2one('purchase.order', string='Purchase Order')
    state              = fields.Selection([('brouillon','Brouillon'),
                              ('envoye','Envoye'),
                              ('termine','Termine'),
                             ], string='Equipement de mesure a etalonner', select=True)
    record_url         = fields.Char('Record URL for Mail')


    _defaults = {
        'demandeur_id': lambda self, cr, uid, c: uid,
        'state': 'brouillon',
    }

    @api.model
    def create(self, vals):
        data_obj = self.env['ir.model.data']
        sequence_ids = data_obj.search([('name','=','seq_is_demande_achat')])
        if len(sequence_ids)>0:
            sequence_id = sequence_ids[0].res_id
            vals['name'] = self.env['ir.sequence'].get_id(sequence_id, 'id')
        res = super(is_demande_achat, self).create(vals)
        model, action_id = data_obj.get_object_reference('is_plastigray', 'is_demande_achat_action')
        print ":action_id::",action_id
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        menu_id = self.env['ir.ui.menu'].search([('name','=', "Demandes d'achat")])
        print "::menu_id::",menu_id
        route = 'login'
        query = dict(db=self._cr.dbname)
        fragment = dict()
        fragment['action'] = action_id
        fragment['view_type'] = 'form'
        fragment['menu_id'] = menu_id[0]
        fragment['model'] = model
        fragment['id'] = res.id

        if fragment:
            query['redirect'] = '/web#' + werkzeug.url_encode(fragment)
            
        record_url = urljoin(base_url, "/web/%s?%s" % (route, werkzeug.url_encode(query)))
        res.record_url = record_url
        
        return res

    @api.multi
    def action_envoye(self):
        template_id = self.env['ir.model.data'].get_object_reference('is_plastigray', 'demande_chart_acheteur_id_email_template')[1]
        for rec in self:
            self.pool.get('email.template').send_mail(self._cr, self._uid, template_id, rec.id, force_send=True, context=self._context)
        self.state = 'envoye'

    @api.multi
    def action_termine(self):
        template_id = self.env['ir.model.data'].get_object_reference('is_plastigray', 'demande_chart_demandeur_id_email_template')[1]
        for rec in self:
            self.pool.get('email.template').send_mail(self._cr, self._uid, template_id, rec.id, force_send=True, context=self._context)
        self.state = 'termine'
        
    @api.multi
    def action_po(self):
        po_obj = self.env['purchase.order']
        stock_location_obj = self.env['stock.location']
        product_pricelist_obj = self.env['product.pricelist']
        line_obj = self.env['purchase.order.line']
        for rec in self:
            location_id = stock_location_obj.search([('usage', '=', 'supplier')])
            pricelist_id = product_pricelist_obj.search([('type', '=', 'sale')])
            po_val = {
                'partner_id': rec.fournisseur_id and rec.fournisseur_id.id or False,
                'date_order': rec.delai_souhaite,
                'location_id': location_id[0].id,
                'pricelist_id': pricelist_id[0].id,
            }
            po_line = []
            for line in rec.line_ids:
                
                on_change_val=line_obj.onchange_product_id(
                    pricelist_id[0].id, 
                    line.product_id.id, 
                    line.qt_cde, 
                    line.product_uom.id, 
                    rec.fournisseur_id.id, 
                )
                val = on_change_val['value']
                val.update({
                    'product_id': line.product_id and line.product_id.id or False,
                    'product_qty': line.qt_cde,
                    'price_unit': line.prix,
                    'taxes_id': [(6, 0, on_change_val['value']['taxes_id'])],
                })
                po_line.append((0, 0, val))
            po_val.update({'order_line': po_line})
            po_id = po_obj.create(po_val)
            rec.po_id = po_id
            rec.is_pos = True
            return {
                'domain': "[('id','=', " + str(po_id.id) + ")]",
                'name': _('Purchase Orders'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'purchase.order',
                'view_id': False,
                'type': 'ir.actions.act_window',
                'search_view_id': po_id.id
            }


class is_demande_achat_line(models.Model):
    _name='is.demande.achat.line'

    achat_id = fields.Many2one('is.demande.achat', string='Ligne')
    product_id = fields.Many2one('product.product', string='Code PG')
    code_fournisseur = fields.Char('Code Fournisseur')
    designation = fields.Char('Désignation')
    qt_cde = fields.Float('Qt Cde')
    prix = fields.Float('Prix')
    compte = fields.Char('Compte')
    section = fields.Char('Section')
    chantier = fields.Char('Chantier')
    product_uom = fields.Many2one('product.uom', string='unit of purchase')
    
    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id and self.product_id.uom_po_id:
            self.product_uom = self.product_id.uom_po_id.id

