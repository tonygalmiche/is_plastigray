# -*- coding: utf-8 -*-
from openerp import models,fields,api,SUPERUSER_ID
from openerp.tools.translate import _
from openerp.exceptions import Warning
import datetime
import xmlrpclib


#TODO : 
#- DEB importation
#- Ajouter un bouton pour accèder aux lignes de la synthese quand la fiche est terminé


class is_deb(models.Model):
    _name='is.deb'
    _order='name desc'

    def _compute(self):
        uid=self._uid
        user = self.env['res.users'].browse(uid)
        soc=user.company_id.partner_id.is_code
        for obj in self:
            obj.soc=soc

    name         = fields.Date("Date DEB"     , required=True)
    date_debut   = fields.Date("Date de début", required=True, help="Date de début des factures")
    date_fin     = fields.Date("Date de fin"  , required=True, help="Date de fin des factures")
    soc          = fields.Char('Code société', compute='_compute', readonly=True, store=False)
    line_ids     = fields.One2many('is.deb.line'    , 'deb_id', u"Lignes DEB")
    synthese_ids = fields.One2many('is.deb.synthese', 'deb_id', u"Synthèse DEB")
    state        = fields.Selection([('creation', u'Création'),('modification', u'Modification des lignes'),('termine', u'Terminé')], u"État", readonly=True, select=True)

    _defaults = {
        'name' : lambda *a: fields.datetime.now(),
        'state': 'creation',
    }


    @api.multi
    def transfert_action(self):
        for obj in self:
            obj.line_ids.unlink()
            obj.transfert()
            obj.state='modification'
            return obj.lignes_deb_action()


    @api.multi
    def transfert(self):
        cr , uid, context = self.env.args
        for obj in self:
            user    = self.pool['res.users'].browse(cr, uid, [uid])[0]
            company     = user.company_id.partner_id
            departement = company.zip[:2]
            SQL="""
                select 
                    ai.id,
                    ai.internal_number,
                    ai.date_invoice,
                    ai.type,
                    ai.is_type_facture,
                    COALESCE(sp.partner_id, ai.partner_id),
                    pt.is_nomenclature_douaniere,
                    pt.is_origine_produit_id,
                    sum(fsens(ai.type)*pt.weight_net*ail.quantity),
                    sum(fsens(ai.type)*ail.price_unit*ail.quantity)
                from account_invoice ai inner join account_invoice_line ail on ai.id=ail.invoice_id 
                                        inner join product_product       pp on ail.product_id=pp.id
                                        inner join product_template      pt on pp.product_tmpl_id=pt.id
                                        left outer join stock_move       sm on ail.is_move_id=sm.id
                                        left outer join stock_picking    sp on sm.picking_id=sp.id
                where 
                    ai.date_invoice>='"""+str(obj.date_debut)+"""' and
                    ai.date_invoice<='"""+str(obj.date_fin)+"""' and
                    get_property_account_position(COALESCE(sp.partner_id, ai.partner_id))=1
                group by
                    ai.id,
                    ai.internal_number,
                    ai.date_invoice,
                    ai.type,
                    ai.is_type_facture,
                    sp.partner_id, 
                    ai.partner_id,
                    pt.is_nomenclature_douaniere,
                    pt.is_origine_produit_id
            """
            cr.execute(SQL)
            result = cr.fetchall()
            for row in result:
                type_deb='exportation'
                type_facture=row[3]
                if type_facture=='in_invoice' or type_facture=='in_refund':
                    type_deb='introduction'
                masse_nette=row[8]
                if type_deb=='introduction':
                    masse_nette=0
                country=self.env['res.country'].browse(row[7])

                pays_origine=''
                if type_deb=='introduction':
                    pays_origine=country.name


                partner=self.env['res.partner'].browse(row[5])
                pays_destination=partner.country_id.name
                vals={
                    'deb_id'                : obj.id,
                    'type_deb'              : type_deb,
                    'invoice_id'            : row[0],
                    'num_facture'           : row[1],
                    'date_facture'          : row[2],
                    'type_facture'          : row[3]+u' '+row[4],
                    'partner_id'            : partner.id,
                    'nomenclature_douaniere': row[6],
                    'masse_nette'           : masse_nette,
                    'pays_origine'          : pays_origine,
                    'pays_destination'      : pays_destination,
                    'valeur_fiscale'        : row[9],
                    'departement_expedition': departement,
                    'num_tva'               : partner.vat, 
                }
                line=self.env['is.deb.line'].create(vals)


    @api.multi
    def synthese_action(self):
        cr , uid, context = self.env.args
        for obj in self:
            SQL="""
                select 
                    type_deb,
                    num_facture,
                    date_facture,
                    code_regime,
                    nomenclature_douaniere,
                    pays_origine,
                    pays_destination,
                    nature_transaction,
                    mode_transport,
                    departement_expedition,
                    num_tva,
                    sum(masse_nette),
                    sum(valeur_fiscale)
                from is_deb_line
                where deb_id="""+str(obj.id)+"""
                group by
                    type_deb,
                    num_facture,
                    date_facture,
                    code_regime,
                    nomenclature_douaniere,
                    pays_origine,
                    pays_destination,
                    nature_transaction,
                    mode_transport,
                    departement_expedition,
                    num_tva
            """
            cr.execute(SQL)
            result = cr.fetchall()
            obj.synthese_ids.unlink()
            for row in result:
                type_deb=row[0]
                pays=row[5]
                if type_deb=='exportation':
                    pays=row[6]
                vals={
                    'deb_id'                : obj.id,
                    'type_deb'              : type_deb,
                    'num_facture'           : row[1],
                    'date_facture'          : row[2],
                    'code_regime'           : row[3],
                    'nomenclature_douaniere': row[4],
                    'pays_destination'      : pays,
                    'nature_transaction'    : row[7],
                    'mode_transport'        : row[8],
                    'departement_expedition': row[9],
                    'num_tva'               : row[10],
                    'masse_nette'           : row[11],
                    'valeur_fiscale'        : row[12],
                }
                line=self.env['is.deb.synthese'].create(vals)
            obj.state='termine'
            return self.synthese_lignes_action()






    @api.multi
    def synthese_multi_sites_action(self):
        for obj in self:
            obj.synthese_ids.unlink()
            databases=self.env['is.database'].search([])
            for database in databases:
                if database.database:
                    DB = database.database
                    USERID = SUPERUSER_ID
                    DBLOGIN = database.login
                    USERPASS = database.password
                    DB_SERVER = database.ip_server
                    DB_PORT = database.port_server
                    sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/object' % (DB_SERVER, DB_PORT))
                    ids = sock.execute(DB, USERID, USERPASS, 'is.deb.synthese', 'search', [
                        ('deb_id.name', '=', obj.name),
                    ], {})
                    fields=[
                        'type_deb',
                        'num_facture',
                        'date_facture',
                        'code_regime',
                        'nomenclature_douaniere',
                        'masse_nette',
                        'pays_destination',
                        'valeur_fiscale',
                        'nature_transaction',
                        'mode_transport',
                        'departement_expedition',
                        'num_tva',
                    ]
                    res = sock.execute(DB, USERID, USERPASS, 'is.deb.synthese', 'read', ids,  fields)
                    for vals in res:
                        vals.update({'deb_id':obj.id})
                        created=self.env['is.deb.synthese'].create(vals)
            obj.state='termine'
            return {
                'name': u'Synthèse DEB',
                'view_mode': 'tree,form',
                'view_type': 'form',
                'res_model': 'is.deb.synthese',
                'domain': [
                    ('deb_id'  ,'=', obj.id),
                ],
                'context': {
                    'default_deb_id'  : obj.id,
                },
                'type': 'ir.actions.act_window',
                'limit': 1000,
            }



    @api.multi
    def lignes_deb_action(self):
        for obj in self:
            return {
                'name': u'Lignes DEB',
                'view_mode': 'tree,form',
                'view_type': 'form',
                'res_model': 'is.deb.line',
                'domain': [
                    ('deb_id'  ,'=', obj.id),
                ],
                'context': {
                    'default_deb_id'  : obj.id,
                },
                'type': 'ir.actions.act_window',
                'limit': 1000,
            }


    @api.multi
    def synthese_lignes_action(self):
        for obj in self:
            return {
                'name': u'Synthèse DEB',
                'view_mode': 'tree,form',
                'view_type': 'form',
                'res_model': 'is.deb.synthese',
                'domain': [
                    ('deb_id'  ,'=', obj.id),
                ],
                'context': {
                    'default_deb_id'  : obj.id,
                },
                'type': 'ir.actions.act_window',
                'limit': 1000,
            }






class is_deb_line(models.Model):
    _name='is.deb.line'
    _order='deb_id,type_deb,invoice_id'

    deb_id                 = fields.Many2one('is.deb', "DEB", required=True, ondelete='cascade')
    type_deb               = fields.Selection([('introduction', u'Introduction'),('exportation', u'Exportation')], u"Type de DEB", required=True, select=True)
    invoice_id             = fields.Many2one('account.invoice', 'Facture')
    num_facture            = fields.Char("N° de facture")
    date_facture           = fields.Date("Date facture")
    type_facture           = fields.Char("Type de facture")
    partner_id             = fields.Many2one('res.partner', 'Client livré / Fournisseur')
    code_regime            = fields.Char("Code régime")
    nomenclature_douaniere = fields.Char("Nomenclature douaniere")
    masse_nette            = fields.Float("Masse nette")
    pays_origine           = fields.Char("Pays d'origine"     , help="Pays d'origine indiqué dans la fiche article")
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


class is_deb_synthese(models.Model):
    _name='is.deb.synthese'
    _order='deb_id,type_deb,num_facture'

    deb_id                 = fields.Many2one('is.deb', "DEB", required=True, ondelete='cascade')
    type_deb               = fields.Selection([('introduction', u'Introduction'),('exportation', u'Exportation')], u"Type de DEB", required=True, select=True)
    num_facture            = fields.Char("N° de facture")
    date_facture           = fields.Date("Date facture")
    code_regime            = fields.Char("Code régime")
    nomenclature_douaniere = fields.Char("Nomenclature douaniere")
    masse_nette            = fields.Float("Masse nette")
    pays_destination       = fields.Char("Pays", help="Pays de destination du client livré ou Pays d'expédition pour les fournisseurs")
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






