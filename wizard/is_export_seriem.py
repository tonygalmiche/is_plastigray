# -*- coding: utf-8 -*-
import datetime
#from datetime import date, datetime
import time
from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning
from ftplib import FTP
import os


class is_export_seriem(models.TransientModel):
    _name = "is.export.seriem"
    _description = "Exportation vers Serie-M"

    date_debut   = fields.Date('Date de début', required=True)
    date_fin     = fields.Date('Date de fin'  , required=True)

    def _date():
        now  = datetime.date.today()               # Date du jour
        date = now + datetime.timedelta(days=-1)   # Date -1
        return date.strftime('%Y-%m-%d')           # Formatage

    _defaults = {
        'date_debut':  _date(),
        'date_fin'  :  _date(),
    }


    @api.multi
    def export_seriem(self):
        cr=self._cr
        for obj in self:
            invoices = self.env['account.invoice'].search([
                ('state'       , '=' , 'open'),
                ('date_invoice', '>=', obj.date_debut),
                ('date_invoice', '<=', obj.date_fin),
                ('is_folio_id', '=' , False),
            ])
            if len(invoices)==0:
                raise Warning('Aucune facture à traiter')

            #** Création du Folio **********************************************
            folio=self.env['is.account.folio'].create({})
            #*******************************************************************

            res=[]
            Soc             = u'PLI'
            Folio           = folio.name
            CodeDevice      = u''
            DateJour        = time.strftime('%y%m%d') 
            CompteCollectif = u'"411000"'
            res.append("FPGVMFCO")
            res.append(u"E"+Soc+u'VE'+CodeDevice+(u"0000"+Folio)[-4:]+DateJour+u" 211")


            for invoice in invoices:
                #** Mettre le numéro de Folio sur la facture *******************
                invoice.is_folio_id=folio.id
                #***************************************************************

                id=invoice.id
                TotalTTC  = 0  # Total TTC du compte 411000
                TotalTTC2 = 0  # Montant de la somme des autres lignes (l'écart sera ajouté sur la dernière ligne)

                sql="""
                    SELECT  ai.number, 
                            ai.date_invoice, 
                            rp.is_code, 
                            rp.name, 
                            aa.code, 
                            isa.name, 
                            aa.type, 
                            ai.date_due,
                            aj.code,
                            sum(aml.debit), 
                            sum(aml.credit)
                    FROM account_move_line aml inner join account_invoice ai             on aml.move_id=ai.move_id
                                               inner join account_account aa             on aml.account_id=aa.id
                                               inner join res_partner rp                 on ai.partner_id=rp.id
                                               left outer join account_invoice_line ail  on aml.is_account_invoice_line_id=ail.id
                                               left outer join is_section_analytique isa on ail.is_section_analytique_id=isa.id
                                               left outer join account_journal aj        on rp.is_type_reglement=aj.id
                    WHERE ai.id="""+str(id)+"""
                    GROUP BY ai.number, ai.date_invoice, rp.is_code, rp.name, aa.code, isa.name, aa.type, ai.date_due, aj.code
                    ORDER BY ai.number, ai.date_invoice, rp.is_code, rp.name, aa.code, isa.name, aa.type, ai.date_due, aj.code
                """

                cr.execute(sql)
                for row in cr.fetchall():
                    NumCompte = row[4]
                    Debit     = row[9]
                    Credit    = row[10]
                    Montant   = Credit - Debit
                    Sens=u"D"
                    if Montant>0:
                        Sens    = u"C"
                    else:
                        Sens    = u"D"
                    CodeAuxiliaire=row[2]
                    if NumCompte=="411000" or NumCompte=="401000":
                        CompteCollectif = NumCompte
                        CodeFournisseur = CodeAuxiliaire
                        TotalTTC=Montant
                    else:
                        CodeFournisseur = "      "
                        TotalTTC2 = TotalTTC2 + Montant

                    Montant=abs(int(round(100*Montant)))
                    Montant=(u"00000000000"+str(Montant))[-11:]

                    TypeFacture=row[6]
                    if TypeFacture=='out_refund':
                        TypeFacture=u'A'  # Avoir
                    else:
                        TypeFacture=u'F'  # Facture

                    Client=(row[3]+u"                                ")[:26]

                    NumFacture=(u"000000"+str(row[0]))[-6:]
                    DateEcheance=row[7]
                    DateEcheance=datetime.datetime.strptime(DateEcheance, '%Y-%m-%d')
                    DateEcheance=DateEcheance.strftime('%y%m%d')
                    TypeReglement=(row[8]+"  ")[:2]
                    SectionAnalytique=str(row[5] or u'    ')
                    DateFacture=str(row[1])
                    JourFacture=(u"00"+DateFacture)[-2:]
                    Ligne=u"L"+NumCompte+CodeFournisseur+Montant+Sens+TypeFacture+Client+NumFacture+SectionAnalytique+JourFacture+u"   00000000000   00000000000"
                    res.append(Ligne)

                # ** Ligne de fin type H *******************************************
                TotalTTC=int(round(100*TotalTTC))
                TotalTTC=(u"000000000"+str(TotalTTC))[-9:]
                Ligne=u'H'+Soc+CompteCollectif+CodeAuxiliaire+NumFacture+u'01'+TotalTTC+u' '+DateEcheance+TypeReglement+'  0000000 1'
                res.append(Ligne)
                #*******************************************************************

            # Enregistrement du fichier ****************************************
            os.chdir('/tmp')
            name = 'PGVMFCO'
            err=""
            try:
                fichier = open(name, "w")
            except IOError, e:
                err="Problème d'accès au fichier '"+name+"' => "+ str(e)
            if err=="":
                for row in res:
                    fichier.write(row+u'\n')
                fichier.close()
            else:
                raise Warning(err)

            # ******************************************************************

            # Envoi du fichier dans l'AS400 ************************************
            if err=="":
                uid=self._uid
                user=self.env['res.users'].browse(uid)
                pwd=user.company_id.is_cpta_pwd
                try:
                    ftp = FTP('192.0.0.99', 'qsecofr', pwd)  
                except Exception, e:
                    err=u"Problème d'accès à l'AS400 CPTA => "+ str(e)
                if err=="":
                    f = open(name, 'rb')
                    ftp.sendcmd('CWD FMPRO')
                    ftp.storlines('STOR ' + name, f)
                    f.close() 
                    ftp.quit() 
                else:
                    raise Warning(err)
            # ******************************************************************



            res= {
                'name': 'Folio',
                'view_mode': 'form, tree',
                'view_type': 'form',
                'res_model': 'is.account.folio',
                'type': 'ir.actions.act_window',
                'res_id': folio.id,
            }
            return res






