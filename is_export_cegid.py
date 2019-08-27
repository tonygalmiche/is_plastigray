# -*- coding: utf-8 -*-
from openerp import models,fields,api
from openerp.tools.translate import _
import datetime
from openerp.exceptions import Warning
import codecs
import unicodedata
import base64
import csv, cStringIO



def date2txt(date):
    if not date:
        return '        '
    txt=str(date)
    AAAA = txt[:4]
    MM   = txt[5:7]
    JJ   = txt[-2:]
    return JJ+MM+AAAA

def float2txt(val,lg):
    val="{:.2f}".format(val);
    val='                                                                                                                           '+val
    val=val[-lg:]
    return val


def s(txt,lg):
    if type(txt)==int or type(txt)==float:
        txt=str(txt)
    if type(txt)!=unicode:
        txt = unicode(txt,'utf-8')
    txt = unicodedata.normalize('NFD', txt).encode('ascii', 'ignore')
    txt=txt+'                                                                                                                           '
    txt=txt[:lg]
    return txt


class is_export_cegid_ligne(models.Model):
    _name = 'is.export.cegid.ligne'
    _description = u"Lignes d'export cegid"
    _order='ligne,id'

    export_cegid_id   = fields.Many2one('is.export.cegid', u'Export Cegid', required=True, ondelete='cascade')
    ligne             = fields.Integer(u"Ligne")
    journal           = fields.Char(u"Journal")
    datecomptable     = fields.Date(u"Date")
    type_piece        = fields.Char(u"Nature mouvement")
    general           = fields.Char(u"Compte général")
    type_cpte         = fields.Char(u"Nature ligne")
    auxilaire_section = fields.Char(u"Compte auxilaire ou Section")
    refinterne        = fields.Char(u"Référence (Pièce)")
    libelle           = fields.Char(u"Libellé")
    modepaie          = fields.Char(u"Mode paiement")
    echeance          = fields.Date(u"Date échéance")
    sens              = fields.Char(u"Sens")
    montant1          = fields.Float(u"Montant")
    devise            = fields.Char(u"Devise")
    tauxdev           = fields.Float(u"Taux devise")
    etablissement     = fields.Char(u"Etablissement")
    axe               = fields.Char(u"Axe analytique")
    refexterne        = fields.Char(u"Référence externe")
    societe           = fields.Char(u"Code société")
    affaire           = fields.Char(u"Code affaire")
    reflibre          = fields.Char(u"Folio")
    tvaencaissement   = fields.Char(u"TVA encaissement")
    regimetva         = fields.Char(u"Régime TVA")
    tva               = fields.Char(u"TVA")
    bon_a_payer       = fields.Char(u"Bon à payer")
    invoice_id        = fields.Many2one('account.invoice', u"Facture")

    _defaults = {
        'journal': 'VTE',
        'devise' : 'E',
    }



class is_export_cegid(models.Model):
    _name='is.export.cegid'
    _order='name desc'

    name = fields.Char(u"N°Folio", readonly=True)
    journal = fields.Selection([
        ('VTE', u'Ventes'),
        ('ACH', u'Achats'),
    ], 'Journal', required=True)
    date_debut         = fields.Date(u"Date de début", required=True)
    date_fin           = fields.Date(u"Date de fin"  , required=True)
    ligne_ids          = fields.One2many('is.export.cegid.ligne', 'export_cegid_id', u'Lignes')
    invoice_ids        = fields.One2many('account.invoice', 'is_export_cegid_id', 'Factures', readonly=True)


    @api.model
    def create(self, vals):
        data_obj = self.env['ir.model.data']
        sequence_ids = data_obj.search([('name','=','is_export_cegid_seq')])
        if sequence_ids:
            sequence_id = data_obj.browse(sequence_ids[0].id).res_id
            vals['name'] = self.env['ir.sequence'].get_id(sequence_id, 'id')
        res = super(is_export_cegid, self).create(vals)
        return res






    @api.multi
    def action_export_cegid(self):
        cr=self._cr
        ligne=0
        for obj in self:
            obj.ligne_ids.unlink()


            if obj.journal=='VTE':
                type_facture=['out_invoice', 'out_refund']
            else:
                type_facture=['in_invoice','in_refund' ]
            invoices = self.env['account.invoice'].search([
                ('state'       , '=' , 'open'),
                ('date_invoice', '>=', obj.date_debut),
                ('date_invoice', '<=', obj.date_fin),
                ('is_export_cegid_id', '=' , False),
                ('is_folio_id'      ,  '=' , False),
                ('type'        , 'in', type_facture),
                #('id'          , '=' , 12865),
            ], order='is_bon_a_payer, number')

            if len(invoices)==0:
                raise Warning('Aucune facture à traiter')

            #** Création du Folio **********************************************
            #folio=self.env['is.account.folio'].create({})
            #*******************************************************************

            #res=[]
            #Soc             = u'PLI'
            #Folio           = obj.name
            #CodeDevice      = u''
            #DateJour = datetime.datetime.strptime(obj.date_fin, '%Y-%m-%d')
            #DateJour = DateJour.strftime('%y%m%d') 
            #CompteCollectif = u'"411000"'
            #res.append("FPGVMFCO")
            #res.append(u"E"+Soc+Journal+CodeDevice+(u"0000"+Folio)[-4:]+DateJour+u" 211")


            for invoice in invoices:
                #** Mettre le numéro de Folio sur la facture *******************
                invoice.is_export_cegid_id=obj.id
                #***************************************************************

                #id=invoice.id
                #TotalTTC  = 0  # Total TTC du compte 411000
                #TotalTTC2 = 0  # Montant de la somme des autres lignes (l'écart sera ajouté sur la dernière ligne)

                sql="""
                    SELECT  ai.number, 
                            ai.date_invoice, 
                            rp.is_code, 
                            rp.name, 
                            aa.code, 
                            isa.name, 
                            ai.type, 
                            ai.date_due,
                            aj.code,
                            sum(aml.debit), 
                            sum(aml.credit),
                            rp.supplier,
                            ai.is_bon_a_payer,
                            ai.supplier_invoice_number,
                            rp.is_adr_groupe,
                            ail.is_document,
                            ai.id
                    FROM account_move_line aml inner join account_invoice ai             on aml.move_id=ai.move_id
                                               inner join account_account aa             on aml.account_id=aa.id
                                               inner join res_partner rp                 on ai.partner_id=rp.id
                                               left outer join account_invoice_line ail  on aml.is_account_invoice_line_id=ail.id
                                               left outer join is_section_analytique isa on ail.is_section_analytique_id=isa.id
                                               left outer join account_journal aj        on rp.is_type_reglement=aj.id
                    WHERE ai.id="""+str(invoice.id)+"""
                    GROUP BY ai.is_bon_a_payer, ai.number, ai.date_invoice, rp.is_code, rp.name, aa.code, isa.name, ai.type, ai.date_due, aj.code, rp.supplier,ai.supplier_invoice_number,rp.is_adr_groupe,ail.is_document,ai.id
                    ORDER BY ai.is_bon_a_payer, ai.number, ai.date_invoice, rp.is_code, rp.name, aa.code, isa.name, ai.type, ai.date_due, aj.code, rp.supplier,ai.supplier_invoice_number,rp.is_adr_groupe,ail.is_document,ai.id
                """



                # Recherche des affaires par facture pour les mettre sur le compte 401000
                cr.execute(sql)
                Affaires={}
                for row in cr.fetchall():
                    NumFacture = str(row[0])
                    Affaire    = str(row[15])
                    if Affaire!='None':
                        Affaires[NumFacture]=Affaire


                #print Affaires


                cr.execute(sql)
                for row in cr.fetchall():
                    ligne+=1
                    journal           = obj.journal
                    datecomptable     = row[1]
                    general           = row[4]
                    refexterne        = row[13] or ''

                    tab={
                        'out_invoice': 'FC', # Facture Client
                        'out_refund' : 'AC', # Avoir client
                        'in_invoice' : 'FF', # Facture fournisseur
                        'in_refund'  : 'AF', # Avoir fournisseur 
                    }
                    type_piece = tab.get(row[6],'??')


                    #Test si client ou fournisseur
                    if row[11]:
                        CompteCollectif = u'401000'
                        if type_piece=='FC':
                            type_piece = 'OD'
                    else:
                        CompteCollectif = u'411000'


                    # X : Auxilaire
                    # A : Analytique
                    # H : Analytique = Général
                    type_cpte=' '
                    if general==u'411000' or general==u'401000':
                        type_cpte='X'
                        general = CompteCollectif


                    CodeAuxiliaire =(u"000000"+str(row[2]))[-6:]
                    ClientGroupe=row[14] or False
                    if ClientGroupe!=False:
                        CodeAuxiliaire=(u"000000"+str(ClientGroupe))[-6:]
                    auxilaire_section=''
                    if type_cpte=='X':
                        auxilaire_section = CodeAuxiliaire
                        if obj.journal=='VTE':
                            auxilaire_section='C'+auxilaire_section
                        else:
                            auxilaire_section='F'+auxilaire_section


                    refinterne        = row[0]


                    #** Ajout de l'affaire devant le libelle *******************
                    libelle = row[3]
                    Affaire = row[15] or False
                    if obj.journal=='ACH':
                        if general[:1]=='2' or general=='401000':
                            if not Affaire:
                                if row[0] in Affaires:
                                    Affaire=Affaires[row[0]]
                            if Affaire:
                                if Affaire[:5]=='M0000' or Affaire[:5]=='m0000':
                                    Affaire=Affaire[-5:]
                                libelle=Affaire+u' '+libelle
                    #***********************************************************

                    #Mode de paiement	
                    #BOR	Billet à ordre
                    #CHQ	Chèque
                    #DIV	Divers
                    #ESP	Espèces
                    #LCR	LCR acceptée
                    #LCS	LCR soumis acceptation
                    #PRE	Prélèvements
                    #VIR	Virement
                    #VRT	Virement international
                    modepaie          = 'VIR'

                    echeance          = row[7]
                    debit             = row[9]
                    credit            = row[10]
                    montant1          = credit - debit
                    sens=u"C"
                    if montant1<0:
                        sens = u"D"
                        montant1=-montant1

                    #TODO : A revoir pour générer les lignes A1 et A2
                    axe             = ''

                    #TODO : A revoir avec les axes analytiques
                    affaire         = ''

                    reflibre        = obj.name


                    #Opération soumise à la TVA : 
                    # - : Non
                    # X : Oui
                    tvaencaissement = '-'


                    #TODO : A revoir
                    #Régime de TVA du Tiers	
                    #COR	Corse
                    #DTM	Dom-Tom
                    #EXO	Exonéré
                    #EXP	Export
                    #FRA	France soumis
                    #INT	Intracommunautaire
                    #AUT	Autoliquidation
                    regimetva       = 'FRA'


                    #TODO : A revoir
                    #Code TVA	
                    #T0	Sans taux
                    #TI	Taux intermédiaire
                    #TN	Taux normal
                    #TR	Taux réduit
                    tva = ''


                    #** Bon à payer (champ libre position 833) *****************
                    BonAPayer = row[12]
                    bon_a_payer = ''
                    if obj.journal=='ACH':
                        if not BonAPayer:
                            bon_a_payer=u'L' # Litige

                    TypeFacture=row[6]
                    if TypeFacture=='in_refund':
                        bon_a_payer=u'A'  # Avoir
                    #***********************************************************

                    invoice_id      = row[16]

                    vals={
                        'export_cegid_id'  : obj.id,
                        'ligne'            : ligne,
                        'journal'          : journal,
                        'datecomptable'    : datecomptable,
                        'type_piece'       : type_piece,
                        'general'          : general,
                        'type_cpte'        : type_cpte,
                        'auxilaire_section': auxilaire_section,
                        'refinterne'       : refinterne,
                        'libelle'          : libelle,
                        'modepaie'         : modepaie,
                        'echeance'         : echeance,
                        'sens'             : sens,
                        'montant1'         : montant1,
                        'devise'           : 'EUR',
                        'tauxdev'          : 1,
                        'etablissement'    : '001',
                        'axe'              : axe,
                        'refexterne'       : refexterne,
                        'societe'          : '001',
                        'affaire'          : affaire,
                        'reflibre'         : reflibre,
                        'tvaencaissement'  : tvaencaissement,
                        'regimetva'        : regimetva,
                        'tva'              : tva,
                        'bon_a_payer'      : bon_a_payer,
                        'invoice_id'       : invoice_id,
                    }
                    self.env['is.export.cegid.ligne'].create(vals)


                    #print refinterne,echeance


                    # A1 = Axe Analytique 1 = Section Analytique
                    # Pas de section analytique pour les comptes 2xx (immo)
                    A1=str(row[5] or False) 
                    if general[:1]==u'2':
                        A1=False

                    # A2 = Axe Analytique 2 = Moule
                    A2=False
                    Affaire = row[15] or False
                    if Affaire:
                        A2=(Affaire[-5:]+u'    ')[:5]

                    if general[0:1] in ['6','7']:
                        if A1:
                            vals['echeance']          = False
                            vals['type_cpte']         = 'A'
                            vals['axe']               = 'A1'
                            vals['auxilaire_section'] = A1
                            self.env['is.export.cegid.ligne'].create(vals)
                        if A2:
                            vals['echeance']          = False
                            vals['type_cpte']         = 'A'
                            vals['axe']               = 'A2'
                            vals['auxilaire_section'] = A2
                            self.env['is.export.cegid.ligne'].create(vals)


    @api.multi
    def action_generer_fichier(self):
        for obj in self:

            name='export-cegid-'+obj.name+'.TRA'
            model='is.export.cegid'
            attachments = self.env['ir.attachment'].search([('res_model','=',model),('res_id','=',obj.id),('name','=',name)])
            attachments.unlink()
            dest     = '/tmp/'+name
            f = codecs.open(dest,'wb',encoding='utf-8')
            f.write('!\r\n')
            for l in obj.ligne_ids:
                f.write(s(l.journal,3))
                f.write(date2txt(l.datecomptable))
                f.write(s(l.type_piece,2))
                f.write(s(l.general,17))
                f.write(s(l.type_cpte,1))
                f.write(s(l.auxilaire_section,17))
                f.write(s(l.refinterne,35))
                f.write(s(l.libelle,35))
                f.write(s(l.modepaie,3))
                f.write(date2txt(l.echeance))
                f.write(s(l.sens,1))
                f.write(float2txt(l.montant1,20))

                f.write(s('N',1))

                #f.write(s('',8))
                f.write(s(l.refinterne,8)) # Pour pouvoir cocher "Conserver les rupture d pièces" lors de l'import

                f.write(s(l.devise,3))
                f.write(s('1,00000000',10))
                f.write(s('E--',3))
                f.write(s('',20+20))

                f.write(s(l.etablissement,3))
                f.write(s(l.axe,2))

                f.write(s('',2))
                f.write(s(l.refexterne,35))
                f.write(s('',8+8))

                f.write(s(l.societe,3))
                f.write(s(l.affaire,17))

                f.write(s('',8+3+20+20+3+3))

                f.write(s(l.reflibre,35))
                f.write(s(l.tvaencaissement,1))
                f.write(s(l.regimetva,3))
                f.write(s(l.tva,3))

                #for i in range(1,441):
                for i in range(1,632):
                    f.write(s('',1))
                f.write(s(l.bon_a_payer,1))

                f.write('\r\n')

            f.close()
            r = open(dest,'rb').read().encode('base64')
            vals = {
                'name':        name,
                'datas_fname': name,
                'type':        'binary',
                'res_model':   model,
                'res_id':      obj.id,
                'datas':       r,
            }
            id = self.env['ir.attachment'].create(vals)




