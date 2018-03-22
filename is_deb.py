# -*- coding: utf-8 -*-
from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning
import datetime


class is_deb(models.Model):
    _name='is.deb'
    _order='name desc'

    name                 = fields.Date("Date DEB"     , required=True)
    date_debut           = fields.Date("Date de début", required=True, help="Date de début des factures")
    date_fin             = fields.Date("Date de fin"  , required=True, help="Date de fin des factures")
    exportation_line_ids = fields.One2many('is.deb.exportation'  , 'deb_id', u"Lignes DEB Exportation")

    _defaults = {
        'name': lambda *a: fields.datetime.now(),
    }


    @api.multi
    def calcul_action(self):
        cr , uid, context = self.env.args
        for obj in self:
            user    = self.pool['res.users'].browse(cr, uid, [uid])[0]
            company = user.company_id.partner_id



            print obj.date_debut
            SQL="""
                select 
                    ai.id,
                    ai.type,
                    ai.is_type_facture,
                    COALESCE(sp.partner_id, ai.partner_id),
                    pt.is_nomenclature_douaniere,
                    pt.weight_net*ail.quantity,
                    ail.price_unit*ail.quantity
                from account_invoice ai inner join account_invoice_line ail on ai.id=ail.invoice_id 
                                        inner join product_product       pp on ail.product_id=pp.id
                                        inner join product_template      pt on pp.product_tmpl_id=pt.id
                                        left outer join stock_move       sm on ail.is_move_id=sm.id
                                        left outer join stock_picking    sp on sm.picking_id=sp.id
                where 
                    ai.date_invoice>='"""+str(obj.date_debut)+"""' and
                    ai.date_invoice<='"""+str(obj.date_fin)+"""' and
                    ai.type in ('out_invoice', 'out_refund')
                limit 1000
            """



            cr.execute(SQL)
            result = cr.fetchall()
            obj.exportation_line_ids.unlink()
            for row in result:
                partner=self.env['res.partner'].browse(row[3])
                if partner.property_account_position.id==1:
                    vals={
                        'deb_id'                : obj.id,
                        'invoice_id'            : row[0],
                        'type_facture'          : row[1]+u' '+row[2],
                        'partner_id'            : partner.id,
                        'nomenclature_douaniere': row[4],
                        'masse_nette'           : row[5],
                        'pays_destination'      : partner.country_id.name,
                        'valeur_fiscale'        : row[6],
                        'departement_expedition': company.zip[:2],
                        'num_tva'               : partner.vat, 
                    }
                    line=self.env['is.deb.exportation'].create(vals)



#            <div t-foreach="o.invoice_line" t-as="l">
#                <t t-set="picking" t-value="l.is_move_id.picking_id"/>
#            </div>
#            <div t-if="picking">
#                <b>Livraison N° </b><span t-field="picking.name" /> du <span t-field="picking.date" t-field-options='{"format": "dd/MM/yyyy"}' /><br />





class is_deb_exportation(models.Model):
    _name='is.deb.exportation'
    _order='deb_id,invoice_id'

    deb_id                 = fields.Many2one('is.deb', "DEB", required=True, ondelete='cascade')
    invoice_id             = fields.Many2one('account.invoice', 'Facture')
    type_facture           = fields.Char("Type de facture")
    partner_id             = fields.Many2one('res.partner', 'Client livré')
    code_regime            = fields.Char("Code régime")
    nomenclature_douaniere = fields.Char("Nomenclature douaniere")
    masse_nette            = fields.Float("Masse nette")
    pays_destination       = fields.Char("Pays de destination", help="Pays de destination du client livré")
    valeur_fiscale         = fields.Float("Valeur fiscale"    , help="Montant net facturé")
    nature_transaction     = fields.Char("Nature de la transaction")
    mode_transport         = fields.Char("Mode de transport")
    departement_expedition = fields.Char("Département d'expédition", help="2 premiers chiffres du code postal du client livré")
    num_tva                = fields.Char("N°TVA du client livré")

    _defaults = {
        'code_regime'       : '21',
        'nature_transaction': '11',
        'mode_transport'    : '3',
    }

