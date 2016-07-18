# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _


class is_segment_achat(models.Model):
    _name = 'is.segment.achat'
    _description = "Segment d'achat"
    
    name        = fields.Char('Code', size=256, required=True)
    description = fields.Text('Commentaire')
    family_line = fields.One2many('is.famille.achat', 'segment_id', 'Familles')


class is_famille_achat(models.Model):
    _name = 'is.famille.achat'
    _description = "Famille d'achat"
    
    name        = fields.Char('Code', size=256, required=True)
    segment_id  = fields.Many2one('is.segment.achat', 'Segment', required=True)
    description = fields.Text('Commentaire')


class is_site(models.Model):
    _name = 'is.site'
    _description = 'Sites'
    
    name = fields.Char('Site', required=True)


class is_transmission_cde(models.Model):
    _name = 'is.transmission.cde'
    _description = 'Mode de transmission des cmds'
    
    name = fields.Char('Mode de transmission des commandes', required=True)


class is_norme_certificats(models.Model):
    _name = 'is.norme.certificats'
    _description = u'Norme Certificat qualité'
    
    name = fields.Char('Nome certificat', required=True)


class is_certifications_qualite(models.Model):
    _name = 'is.certifications.qualite'
    _description = u'Certifications qualité'
    
    is_norme           = fields.Many2one('is.norme.certificats', u'Norme Certificat qualité', required=True)
    is_date_validation = fields.Date('Date de validation du certificat', required=True)
    is_certificat      = fields.Binary('Certificat qualité')
    is_certificat_ids  = fields.Many2many('ir.attachment', 'is_certificat_attachment_rel', 'certificat_id', 'attachment_id', u'Pièces jointes')
    partner_id         = fields.Many2one('res.partner', 'Client/Fournisseur')


class is_secteur_activite(models.Model):
    _name='is.secteur.activite'
    _order='name'
    _sql_constraints = [('name_uniq','UNIQUE(name)', 'Ce code existe déjà')] 

    name = fields.Char("Secteur d'activité", required=True)


class is_type_contact(models.Model):
    _name='is.type.contact'
    _order='name'
    _sql_constraints = [('name_uniq','UNIQUE(name)', 'Ce code existe déjà')] 

    name = fields.Char("Type de contact", required=True)


class is_escompte(models.Model):
    _name='is.escompte'
    _order='name'

    name = fields.Char("Intitulé", required=True)
    taux = fields.Float("Taux d'escompte", required=True)
    compte = fields.Many2one('account.account', "Compte")


class res_partner(models.Model):
    _inherit = 'res.partner'

    is_delai_transport  = fields.Integer('Delai de transport (jour)')
    is_import_function  = fields.Selection([('eCar','eCar'),('xml1','Fonction XML1'),('csv1','Fonction CSV1')], "Fonction d'importation EDI")
    is_raison_sociale2  = fields.Char('Raison sociale 2')
    is_code             = fields.Char('Code')
    is_adr_code         = fields.Char('Code adresse')
    is_rue3             = fields.Char('Rue 3 ou Boite Postale')
    is_secteur_activite = fields.Many2one('is.secteur.activite', "Secteur d'activité")
    is_type_contact     = fields.Many2one('is.type.contact', "Type de contact")
    is_adr_facturation  = fields.Many2one('res.partner', 'Adresse de facturation')
    is_adr_groupe       = fields.Char('Code auxiliaire comptable', help="Code auxiliaire comptable de l'adresse groupe pour la comptabilité")
    is_cofor            = fields.Char('N° fournisseur (COFOR)', help="Notre code fourniseur chez le client")
    is_incoterm         = fields.Many2one('stock.incoterms', "Incoterm")
    is_escompte         = fields.Many2one('is.escompte', "Escompte")

    is_num_fournisseur    = fields.Char(u'N° de fournisseur')
    is_type_reglement     = fields.Many2one('account.journal', u'Type règlement', domain=[('type', 'in', ['bank','cash'])])
    is_num_siret          =  fields.Char(u'N° de SIRET')
    is_segment_achat      =  fields.Many2one('is.segment.achat', "Segment d'achat")
    is_famille_achat      =  fields.Many2one('is.famille.achat', "Famille d'achat")
    is_fournisseur_imp    =  fields.Boolean(u'Fournisseur imposé')

    #is_site_livre         =  fields.Many2one('is.site', u'sites livrés')

    is_site_livre_ids     = fields.Many2many('is.site', id1='partner_id', id2='site_id', string=u'sites livrés')


    is_groupage           =  fields.Boolean('Groupage')
    is_tolerance_delai    =  fields.Boolean('Tolérance sur délai')
    is_tolerance_quantite =  fields.Boolean('Tolérance sur quantité')
    is_transmission_cde   =  fields.Many2one('is.transmission.cde', 'Mode de transmission des commandes')
    is_certifications     = fields.One2many('is.certifications.qualite', 'partner_id', u'Certification qualité')
    is_type_contact       =  fields.Many2one('is.type.contact', "Type de contact")


    _defaults = {
        'delai_transport': 0,
        'is_adr_code': 0,
    }

    _sql_constraints = [
        ('code_adr_uniq', 'unique(is_code, is_adr_code, company_id)', u'Le code et le code adresse doivent être uniques par société!'),
    ]
    
    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            name = record.name
            if record.parent_id and not record.is_company:
                name =  "%s, %s" % (record.parent_id.name, name)
            if record.is_company:
                if record.is_code and record.is_adr_code:
                    name =  "%s (%s/%s)" % (name, record.is_code, record.is_adr_code)
                if record.is_code and not record.is_adr_code:
                    name =  "%s (%s)" % (name, record.is_code)
                                    
            if context.get('show_address_only'):
                name = self._display_address(cr, uid, record, without_company=True, context=context)
            if context.get('show_address'):
                name = name + "\n" + self._display_address(cr, uid, record, without_company=True, context=context)
            name = name.replace('\n\n','\n')
            name = name.replace('\n\n','\n')
            if context.get('show_email') and record.email:
                name = "%s <%s>" % (name, record.email)
            res.append((record.id, name))
        return res
    
    
    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}        
        partner = self.browse(cr, uid, id, context=context)   
        if partner.is_company:           
            default.update({
                'is_code': partner.is_code + ' (copie)',
                'is_adr_code': partner.is_adr_code + ' (copie)',
        })
        return super(is_partner, self).copy(cr, uid, id, default, context=context)
    

    def onchange_segment_id(self, cr, uid, ids, segment_id, context=None):
        domain = []
        val = {'is_famille_achat': False }
        if segment_id:
            domain.append(('segment_id','=',segment_id))           
        return {'value': val,
                'domain': {'is_famille_achat': domain}}




