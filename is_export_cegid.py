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
    societe           = fields.Char(u"Code société")
    affaire           = fields.Char(u"Code affaire")
    reflibre          = fields.Char(u"Folio")
    tvaencaissement   = fields.Char(u"TVA encaissement")
    regimetva         = fields.Char(u"Régime TVA")
    tva               = fields.Char(u"TVA")
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
                #('is_folio_id' , '=' , False),
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

                cr.execute(sql)

                for row in cr.fetchall():
                    ligne+=1
                    journal           = obj.journal
                    datecomptable     = row[1]
                    general           = row[4]





                    tab={
                        'out_invoice': 'FC', # Facture Client
                        'out_refund' : 'AC', # Avoir client
                        'in_invoice' : 'FF', # Facture fournisseur
                        'in_refund'  : 'AF', # Avoir fournisseur 
                    }
                    type_piece = tab.get(row[6],'??')

                    general           = row[4]

                    # X : Auxilaire
                    # A : Analytique
                    # H : Analytique = Général
                    type_cpte=' '
                    if general==u'411000' or general==u'401000':
                        type_cpte='X'


                    CodeAuxiliaire =(u"000000"+str(row[2]))[-6:]
                    ClientGroupe=row[14] or False
                    if ClientGroupe!=False:
                        CodeAuxiliaire=(u"000000"+str(ClientGroupe))[-6:]
                        #print 'ClientGroupe=',ClientGroupe

                    auxilaire_section=''
                    if type_cpte=='X':
                        auxilaire_section = CodeAuxiliaire


                    #print general, type_cpte,CodeAuxiliaire,ClientGroupe


                    refinterne        = row[0]
                    libelle           = row[3]

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
                        'societe'          : '001',
                        'affaire'          : affaire,
                        'reflibre'         : reflibre,
                        'tvaencaissement'  : tvaencaissement,
                        'regimetva'        : regimetva,
                        'tva'              : tva,
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

                f.write(s('',2+35+8+8))

                f.write(s(l.societe,3))
                f.write(s(l.affaire,17))

                f.write(s('',8+3+20+20+3+3))

                f.write(s(l.reflibre,35))
                f.write(s(l.tvaencaissement,1))
                f.write(s(l.regimetva,3))
                f.write(s(l.tva,3))

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



#                f.write('##Transfert\r\n')
#                f.write('##Section\tDos\r\n')
#                f.write('EUR\r\n')
#                f.write('##Section\tMvt\r\n')
#                for row in obj.ligne_ids:
#                    if row.date_facture[0:7]==mois:
#                        compte=str(row.account_id.code or '')
#                        debit=row.debit
#                        credit=row.debit
#                        if row.credit>0.0:
#                            montant=row.credit  
#                            sens='C'
#                        else:
#                            montant=row.debit  
#                            sens='D'
#                        montant='%0.2f' % montant
#                        date=row.date_facture
#                        date=datetime.datetime.strptime(date, '%Y-%m-%d')
#                        date=date.strftime('%d/%m/%Y')
#                        f.write('"'+obj.name+'"\t')
#                        f.write('"'+obj.journal+'"\t')
#                        f.write('"'+date+'"\t')
#                        f.write('"'+compte+'"\t')
#                        f.write('"'+row.libelle[0:34]+'"\t')
#                        f.write('"'+montant+'"\t')
#                        f.write(sens+'\t')
#                        f.write('B\t')
#                        f.write('"'+(row.libelle_piece[0:34] or '')+'"\t')
#                        f.write('"'+(row.piece or '')+'"\t')
#                        f.write('\r\n')
#                f.write('##Section\tJnl\r\n')
#                f.write('"CAI"\t"Caisse"\t"T"\r\n')
#                f.close()
#                r = open(dest,'rb').read().encode('base64')
#                vals = {
#                    'name':        name,
#                    'datas_fname': name,
#                    'type':        'binary',
#                    'res_model':   model,
#                    'res_id':      obj.id,
#                    'datas':       r,
#                }
#                id = self.env['ir.attachment'].create(vals)






#                    CodeAuxiliaire = (u"000000"+str(row[2]))[-6:]
#                    ClientGroupe   = str(row[14])
#                    Affaire        = str(row[15])
#                    if Affaire=='None':
#                        Affaire=''

#                    #Test si client ou fournisseur
#                    if row[11]:
#                        CompteCollectif = u'401000'
#                    else:
#                        CompteCollectif = u'411000'
#                        if ClientGroupe!='None':
#                            CodeAuxiliaire=(u"000000"+str(ClientGroupe))[-6:]


#                    NumCompte         = row[4]
#                    Debit             = row[9]
#                    Credit            = row[10]
#                    BonAPayer         = row[12]
#                    NumFacFournisseur = str(row[13])

#                    if NumFacFournisseur=="None":
#                        NumFacFournisseur="         "

#                    Montant   = Credit - Debit
#                    Sens=u"D"
#                    if Montant>0:
#                        Sens    = u"C"
#                    else:
#                        Sens    = u"D"

#                    #CodeAuxiliaire =(u"000000"+str(row[2]))[-6:]
#                    #ClientGroupe=row[14]
#                    #if ClientGroupe!=False:
#                    #    CodeAuxiliaire=(u"000000"+str(ClientGroupe))[-6:]

#                    if NumCompte==u'411000' or NumCompte==u'401000':
#                        #CompteCollectif = NumCompte
#                        NumCompte       = CompteCollectif
#                        CodeFournisseur = CodeAuxiliaire
#                        TotalTTC=Montant
#                    else:
#                        CodeFournisseur = "      "
#                        TotalTTC2 = TotalTTC2 + Montant

#                    Montant=abs(int(round(100*Montant)))
#                    Montant=(u"00000000000"+str(Montant))[-11:]
#                    TypeFacture=row[6]
#                    if TypeFacture=='out_refund' or TypeFacture=='in_refund':
#                        TypeFacture=u'A'  # Avoir
#                    else:
#                        TypeFacture=u'F'  # Facture
#                    if obj.journal=='achats' and not BonAPayer:
#                        TypeFacture=u'L'  # Facture fournisseur en litige


#                    #Intitule=




#                    Intitule=(row[3]+u"                                ")[:26]
#                    Moule=''

#                    if Journal=="AC":
#                        # Intitule SERIE-M : 10car dans Ref Fac + 16car dans Libelle
#                        # Si Affaire n'existe pas               -> Intitule = N°Fac fournisseur sur 5car + Fournisseur
#                        # Si Compte == 401000 et Affaire existe -> Intitule = N°Fac fournisseur + Affaire + Fournisseur
#                        # Si Compte != 401000 et Affaire existe 
#                        #       et si Compte == '2xx'           -> Intitule = Affaire sur 5car + Fournisseur
#                        #       et si Compte != '2xx'           -> Intitule = Fournisseur sur 15car + Affaire complète
#                        Fournisseur       = row[3]
#                        NumFacFournisseur = (NumFacFournisseur+u'    ')[:5]


#                        if NumCompte=='401000':
#                            if row[0] in Affaires:
#                                Affaire=Affaires[row[0]]
#                        DossierModif=Affaire
#                        if Affaire[:5]=='M0000':
#                            DossierModif=u'M'+Affaire[-5:]
#                        if Affaire=='':
#                            Intitule=NumFacFournisseur+u' '+Fournisseur
#                        else:
#                            if NumCompte=='401000':
#                                Intitule=NumFacFournisseur+u' '+DossierModif+u' '+Fournisseur
#                            else:
#                                if NumCompte[:1]=='2':
#                                    Intitule=(Affaire[-5:]+u'    ')[:5]+u' '+NumFacFournisseur+u' '+Fournisseur
#                                else:
#                                    Intitule=NumFacFournisseur+u' '+(Fournisseur+u'               ')[:15]+DossierModif
#                                    Moule=(Affaire[-5:]+u'    ')[:5]

#                        Intitule=(Intitule+u"                                ")[:26]

#                        #** Pour les investissements, remplacer la numéro de facture fournisseur par le numéro d'affaire
#                        #if Affaire!='' and NumCompte[:1]=='2':
#                        #    NumFacFournisseur=(Affaire[-5:]+u'    ')[:5]
#                        #else:
#                        #    NumFacFournisseur=(NumFacFournisseur+u'    ')[:5]
#                        #Intitule=(NumFacFournisseur+u' '+Intitule)[:26]

#                    NumFacture=(u"000000"+str(row[0]))[-6:]
#                    DateEcheance=row[7]
#                    DateEcheance=datetime.datetime.strptime(DateEcheance, '%Y-%m-%d')
#                    DateEcheance=DateEcheance.strftime('%y%m%d')
#                    TypeReglement='  '
#                    if row[8]:
#                        TypeReglement=(row[8]+"  ")[:2]
#                    DateFacture=str(row[1])
#                    JourFacture=(u"00"+DateFacture)[-2:]

#                    #** Pas de section analytique pour les comptes 2xx (immo) **
#                    SectionAnalytique=str(row[5] or u'    ')
#                    if NumCompte[:1]==u'2':
#                        SectionAnalytique=u'    '

#                    if Journal=="VE":
#                        if Affaire!='':
#                            Intitule=Affaire+u' '+row[3]
#                            Moule=(Affaire[-5:]+u'    ')[:5]
#                        else:
#                            Intitule=row[3]
#                        Intitule=(Intitule+u"                                ")[:26]
#                        if Affaire!='' and NumCompte[:3]=='707':
#                            Moule=(Affaire[-5:]+u'    ')[:5]




#                    Ligne=u"L" + \
#                        NumCompte + \
#                        CodeFournisseur + \
#                        Montant + \
#                        Sens + \
#                        TypeFacture + \
#                        Intitule + \
#                        NumFacture + \
#                        SectionAnalytique + \
#                        JourFacture + \
#                        u"   00000000000   00000000000" + \
#                        Moule
#                    res.append(Ligne)
#                    print Ligne





#                    #print Ligne

#                # ** Ligne de fin type H *******************************************
#                TotalTTC=int(round(100*TotalTTC))
#                TotalTTC=(u"000000000"+str(TotalTTC))[-9:]
#                Ligne=u'H'+Soc+CompteCollectif+CodeAuxiliaire+NumFacture+u'01'+TotalTTC+u' '+DateEcheance+TypeReglement+'  0000000 1'






#                res.append(Ligne)
#                #*******************************************************************



#            # Enregistrement du fichier ****************************************
#            os.chdir('/tmp')
#            if obj.journal=='ventes':
#                name='PGVMFCO'
#            else:
#                name='PGVMFCA'

#            err=""
#            try:
#                fichier = open(name, "w")
#            except IOError, e:
#                err="Problème d'accès au fichier '"+name+"' => "+ str(e)
#            if err=="":
#                for row in res:
#                    fichier.write(row+u'\n')
#                fichier.close()
#            else:
#                raise Warning(err)

#            # ******************************************************************

            #raise Warning('test')

#            # Envoi du fichier dans l'AS400 ************************************
#            if err=="":
#                uid=self._uid
#                user=self.env['res.users'].browse(uid)
#                pwd=user.company_id.is_cpta_pwd
#                try:
#                    ftp = FTP('192.0.0.99', 'qsecofr', pwd)  
#                except Exception, e:
#                    err=u"Problème d'accès à l'AS400 CPTA => "+ str(e)
#                if err=="":
#                    f = open(name, 'rb')
#                    ftp.sendcmd('CWD FMPRO')
#                    ftp.storlines('STOR ' + name, f)
#                    f.close() 
#                    ftp.quit() 
#                else:
#                    raise Warning(err)
#            # ******************************************************************

#            res= {
#                'name': 'Folio',
#                'view_mode': 'form, tree',
#                'view_type': 'form',
#                'res_model': 'is.account.folio',
#                'type': 'ir.actions.act_window',
#                'res_id': folio.id,
#            }
#            return res























#    @api.multi
#    def action_importer_fichier(self):
#        cr=self._cr
#        for obj in self:
#            obj.ligne_ids.unlink()
#            if obj.journal=='BQ':
#                for attachment in obj.file_ids:
#                    attachment=base64.decodestring(attachment.datas)
#                    #conversion d'ISO-8859-1/latin1 en UTF-8
#                    attachment=attachment.decode('iso-8859-1').encode('utf8')
#                    csvfile=attachment.split("\r\n")
#                    tab=[]
#                    ct=0
#                    for row in csvfile:
#                        ct=ct+1
#                        if ct>1:
#                            lig=row.split(";")
#                            if len(lig)>5:
#                                date    = lig[0]
#                                debit   = lig[2].replace(',', '.')
#                                credit  = lig[3].replace(',', '.')
#                                libelle = lig[4][0:29]
#                                try:
#                                    debit = -float(debit)
#                                except ValueError:
#                                    debit=0
#                                try:
#                                    credit = float(credit)
#                                except ValueError:
#                                    credit=0
#                                vals={
#                                    'export_compta_id'  : obj.id,
#                                    'ligne'             : (ct-1),
#                                    'date_facture'      : date,
#                                    'libelle'           : libelle,
#                                    'libelle_piece'     : libelle,
#                                    'journal'           : obj.journal,
#                                    'debit'             : debit,
#                                    'credit'            : credit,
#                                    'devise'            : u'EUR',
#                                }
#                                self.env['is.export.compta.ligne'].create(vals)
#                self.generer_fichier()
#            if obj.journal=='OD':
#                for attachment in obj.file_ids:
#                    attachment=base64.decodestring(attachment.datas)
#                    csvfile=attachment.split("\n")
#                    csvfile = attachment.split("\n")
#                    csvfile = csv.reader(csvfile, delimiter=',')
#                    for lig, row in enumerate(csvfile):
#                        if lig>0 and len(row)>1:
#                            ligne        = row[0]
#                            date_facture = row[1]
#                            compte       = row[2]
#                            accounts   = self.env['account.account'].search([('code','=',compte)])
#                            account_id=False
#                            if len(accounts):
#                                account_id=accounts[0].id
#                            piece         = row[3]
#                            libelle       = row[4]

#                            debit = row[5].replace(',', '.').replace(' ', '')
#                            try:
#                                debit = float(debit)
#                            except ValueError:
#                                debit=0

#                            credit  = row[6].replace(',', '.').replace(' ', '')
#                            try:
#                                credit = float(credit)
#                            except ValueError:
#                                credit=0
#                            vals={
#                                'export_compta_id'  : obj.id,
#                                'ligne'             : ligne,
#                                'date_facture'      : date_facture,
#                                'account_id'        : account_id,
#                                'libelle'           : libelle,
#                                'piece'             : piece,
#                                'libelle_piece'     : libelle,
#                                'journal'           : obj.journal,
#                                'debit'             : debit,
#                                'credit'            : credit,
#                                'devise'            : u'EUR',
#                            }
#                            self.env['is.export.compta.ligne'].create(vals)



#    @api.multi
#    def action_generer_fichier(self):
#        for obj in self:
#            ct=0
#            for row in obj.ligne_ids:
#                if not row.account_id.id:
#                    ct=ct+1
#            if ct:
#                raise Warning('Compte non renseigné sur '+str(ct)+' lignes')
#            #** Ajout des lignes en 512000
#            if obj.journal=='BQ':
#                account_id = self.env['account.account'].search([('code','=','512000')])[0].id
#                self.env['is.export.compta.ligne'].search([('export_compta_id','=',obj.id),('account_id','=',account_id)]).unlink()
#                for row in obj.ligne_ids:
#                    vals={
#                        'export_compta_id'  : obj.id,
#                        'ligne'             : row.ligne,
#                        'date_facture'      : row.date_facture,
#                        'account_id'        : account_id,
#                        'libelle'           : row.libelle,
#                        'libelle_piece'     : row.libelle_piece,
#                        'journal'           : obj.journal,
#                        'debit'             : row.credit,
#                        'credit'            : row.debit,
#                        'devise'            : u'EUR',
#                    }
#                    self.env['is.export.compta.ligne'].create(vals)
#            self.generer_fichier()


#    @api.multi
#    def action_export_compta(self):
#        cr=self._cr
#        for obj in self:
#            obj.ligne_ids.unlink()

#            if obj.journal=='CAI':
#                sql="""
#                    SELECT  
#                        aml.date,
#                        aa.code, 
#                        aa.name,
#                        '',
#                        '',
#                        '',
#                        aml.account_id,
#                        sum(aml.credit)-sum(aml.debit)
#                    FROM account_move_line aml left outer join account_invoice ai        on aml.move_id=ai.move_id
#                                               inner join account_account aa             on aml.account_id=aa.id
#                                               left outer join res_partner rp            on aml.partner_id=rp.id
#                                               inner join account_journal aj             on aml.journal_id=aj.id
#                    WHERE 
#                        aml.date>='"""+str(obj.date_debut)+"""' and 
#                        aml.date<='"""+str(obj.date_fin)+"""' and 
#                        ((aa.code>'411100' and aa.code not like '512%') or aa.code='411000') and 
#                        aj.type in ('sale','bank','general','cash')
#                    GROUP BY aml.date, aa.code, aa.name,aml.account_id
#                    ORDER BY aml.date, aa.code, aa.name,aml.account_id
#                """


#            if obj.journal=='HA':
#                sql="""
#                    SELECT  
#                        aml.date,
#                        aa.code, 
#                        aa.name,
#                        aj.code,
#                        ai.number,
#                        rp.is_code,
#                        aml.account_id,
#                        sum(aml.credit)-sum(aml.debit)
#                    FROM account_move_line aml left outer join account_invoice ai        on aml.move_id=ai.move_id
#                                               inner join account_account aa             on aml.account_id=aa.id
#                                               left outer join res_partner rp            on aml.partner_id=rp.id
#                                               inner join account_journal aj             on aml.journal_id=aj.id
#                    WHERE aj.code='FACTU' and ai.state not in ('draft','cancel','paid') 
#                """
#                if obj.facture_debut_id:
#                    sql=sql+" and ai.number>='"+str(obj.facture_debut_id.number)+"' "
#                if obj.facture_fin_id:
#                    sql=sql+" and ai.number<='"+str(obj.facture_fin_id.number)+"' "
#                sql=sql+"""
#                    GROUP BY ai.number,aml.date, aa.code, aa.name,aj.code,rp.is_code,aml.account_id
#                    ORDER BY ai.number,aml.date, aa.code, aa.name,aj.code,rp.is_code,aml.account_id
#                """
#            cr.execute(sql)
#            ct=0
#            for row in cr.fetchall():
#                ct=ct+1
#                montant=row[7]
#                debit=0
#                credit=0
#                if montant<0:
#                    debit=-montant
#                else:
#                    credit=montant


#                date_facture=row[0]

#                date=date_facture
#                date=datetime.datetime.strptime(date, '%Y-%m-%d')
#                date=date.strftime('%d/%m/%Y')

#                libelle_piece='Caisse du '+date
#                if obj.journal=='HA':
#                    libelle_piece=row[5]

#                if montant:
#                    vals={
#                        'export_compta_id'  : obj.id,
#                        'ligne'             : ct,
#                        'date_facture'      : date_facture,
#                        'account_id'        : row[6],
#                        'libelle'           : s(row[2][0:29]),
#                        'piece'             : row[4],
#                        'libelle_piece'     : libelle_piece[0:29],
#                        'journal'           : obj.journal,
#                        'debit'             : debit,
#                        'credit'            : credit,
#                        'devise'            : u'EUR',
#                    }


#                    self.env['is.export.compta.ligne'].create(vals)
#            self.generer_fichier()


#    def generer_fichier(self):
#        cr=self._cr


#        for obj in self:

#            sql="""
#                SELECT to_char(date_facture,'YYYY-MM')
#                FROM is_export_compta_ligne
#                WHERE export_compta_id="""+str(obj.id)+"""
#                GROUP BY to_char(date_facture,'YYYY-MM')
#                ORDER BY to_char(date_facture,'YYYY-MM')
#            """
#            cr.execute(sql)
#            for row in cr.fetchall():
#                mois=row[0]
#                name='export-compta-'+mois+'.txt'
#                model='is.export.compta'
#                attachments = self.env['ir.attachment'].search([('res_model','=',model),('res_id','=',obj.id),('name','=',name)])
#                attachments.unlink()
#                dest     = '/tmp/'+name
#                f = codecs.open(dest,'wb',encoding='utf-8')
#                f.write('##Transfert\r\n')
#                f.write('##Section\tDos\r\n')
#                f.write('EUR\r\n')
#                f.write('##Section\tMvt\r\n')
#                for row in obj.ligne_ids:
#                    if row.date_facture[0:7]==mois:
#                        compte=str(row.account_id.code or '')
#                        debit=row.debit
#                        credit=row.debit
#                        if row.credit>0.0:
#                            montant=row.credit  
#                            sens='C'
#                        else:
#                            montant=row.debit  
#                            sens='D'
#                        montant='%0.2f' % montant
#                        date=row.date_facture
#                        date=datetime.datetime.strptime(date, '%Y-%m-%d')
#                        date=date.strftime('%d/%m/%Y')
#                        f.write('"'+obj.name+'"\t')
#                        f.write('"'+obj.journal+'"\t')
#                        f.write('"'+date+'"\t')
#                        f.write('"'+compte+'"\t')
#                        f.write('"'+row.libelle[0:34]+'"\t')
#                        f.write('"'+montant+'"\t')
#                        f.write(sens+'\t')
#                        f.write('B\t')
#                        f.write('"'+(row.libelle_piece[0:34] or '')+'"\t')
#                        f.write('"'+(row.piece or '')+'"\t')
#                        f.write('\r\n')
#                f.write('##Section\tJnl\r\n')
#                f.write('"CAI"\t"Caisse"\t"T"\r\n')
#                f.close()
#                r = open(dest,'rb').read().encode('base64')
#                vals = {
#                    'name':        name,
#                    'datas_fname': name,
#                    'type':        'binary',
#                    'res_model':   model,
#                    'res_id':      obj.id,
#                    'datas':       r,
#                }
#                id = self.env['ir.attachment'].create(vals)




