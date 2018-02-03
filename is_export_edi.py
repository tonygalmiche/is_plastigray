# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning
import os

# TODO : 
# - Créer l'import EDI pour ce fichier (type edi = odoo)


class is_export_edi(models.Model):
    _name='is.export.edi'
    _order='name desc'

    @api.depends('code')
    def _compute(self):
        for obj in self:
            partner_id=False
            if obj.code:
                partners = self.env['res.partner'].search([('is_code','=',obj.code),('is_adr_code','=','0')])
                for partner in partners:
                    partner_id=partner.id
            obj.partner_id=partner_id

    name            = fields.Char("N° export", readonly=True)
    code            = fields.Char("Code fournisseur",required=True)
    code_adr        = fields.Char("Code adresse fournisseur")
    partner_id      = fields.Many2one('res.partner', 'Fournisseur', compute='_compute', readonly=True, store=True)
    contact_id      = fields.Many2one('res.partner', 'Contact Logistique')
    date_fin        = fields.Date("Date de fin", required=True)
    historique_ids  = fields.One2many('is.export.edi.histo'  , 'edi_id', u"Historique")


    @api.multi
    def code_on_change(self,code):
        cr , uid, context = self.env.args
        res={}
        res['value']={}
        contact_id=False
        if code:
            partners = self.env['res.partner'].search([('is_code','=',code),('is_adr_code','=','0')])
            for partner in partners:
                partner_id=partner.id
                #** Recherche du contact logistique ****************************
                SQL="""
                    select rp.id, rp.is_type_contact, itc.name
                    from res_partner rp inner join is_type_contact itc on rp.is_type_contact=itc.id
                    where rp.parent_id="""+str(partner_id)+""" and itc.name ilike '%logistique%' and active='t' limit 1
                """
                cr.execute(SQL)
                result = cr.fetchall()
                for row in result:
                    contact_id=row[0]
                #***************************************************************
        res['value']['contact_id']=contact_id
        return res



    @api.model
    def create(self, vals):
        data_obj = self.env['ir.model.data']
        sequence_ids = data_obj.search([('name','=','is_export_edi_seq')])
        if sequence_ids:
            sequence_id = data_obj.browse(sequence_ids[0].id).res_id
            vals['name'] = self.env['ir.sequence'].get_id(sequence_id, 'id')
        obj = super(is_export_edi, self).create(vals)
        return obj


    @api.multi
    def creer_fichier_edi_action(self):
        cr , uid, context = self.env.args
        for obj in self:
            SQL="""
                select 
                    rp.is_code,
                    rp.is_adr_code,
                    f.name,
                    pt.is_code,
                    l.date,
                    l.type_cde,
                    (l.quantite-coalesce(l.quantite_rcp,0))*is_unit_coef(pt.uom_id, l.uom_id)
                from is_cde_ouverte_fournisseur_line l inner join is_cde_ouverte_fournisseur_product p on l.product_id=p.id
                                                       inner join product_product  pp on p.product_id=pp.id
                                                       inner join product_template pt on pp.product_tmpl_id=pt.id
                                                       inner join is_cde_ouverte_fournisseur f on p.order_id=f.id
                                                       inner join res_partner rp on f.partner_id=rp.id
                where rp.is_code='"""+obj.code+"""' and l.date<='"""+obj.date_fin+"""' 

            """
            if obj.code_adr:
                SQL=SQL+" and rp.is_adr_code='"+obj.code_adr+"' "
            SQL=SQL+"order by rp.is_code, rp.is_adr_code, pt.is_code, l.date "
            cr.execute(SQL)
            result = cr.fetchall()
            datas="";
            for row in result:
                lig=row[0]+'\t'+row[1]+'\t'+row[2]+'\t'+row[3]+'\t'+str(row[4])+'\t'+row[5]+'\t'+str(row[6])+'\n'
                datas=datas+lig

            #** Ajout en pièce jointe ******************************************
            name='export-edi-'+obj.name+'.csv'
            attachment_obj = self.env['ir.attachment']
            model=self._name
            attachments = attachment_obj.search([('res_model','=',model),('res_id','=',obj.id),('name','=',name)]).unlink()
            vals = {
                'name':        name,
                'datas_fname': name,
                'type':        'binary',
                'file_type':   'text/csv',
                'res_model':   model,
                'res_id':      obj.id,
                'datas':       datas.encode('base64'),
            }
            attachment_obj.create(vals)
            self.set_histo(obj.id, 'Création fichier EDI')
            #*******************************************************************


    @api.multi
    def envoyer_par_mail_action(self):
        for obj in self:
            self.envoi_mail()
            self.set_histo(obj.id, u"Envoie par mail du fichier d'EDI à "+obj.contact_id.email)



    @api.multi
    def set_histo(self, edi_id, description):
        vals={
            'edi_id'     : edi_id,
            'description': description,
        }
        histo=self.env['is.export.edi.histo'].create(vals)



    @api.multi
    def envoi_mail(self):
        for obj in self:
            email_to=obj.contact_id.email
            if email_to==False:
                raise Warning(u"Mail non renseigné pour ce contact !")
            user  = self.env['res.users'].browse(self._uid)
            email = user.email
            nom   = user.name
            if email==False:
                raise Warning(u"Votre mail n'est pas renseigné !")
            if email:
                attachment_id = self.env['ir.attachment'].search([
                    ('res_model','=','is.export.edi'),
                    ('res_id'   ,'=',obj.id),
                ])
                body_html=u"""
                    <html>
                        <head>
                            <meta content="text/html; charset=UTF-8" http-equiv="Content-Type">
                        </head>
                        <body>
                            <p>Bonjour, </p>
                            <p>Ci-joint le fichier d'EDI à traiter</p>
                        </body>
                    </html>
                """
                email_vals={
                    'subject'       : "[EDI] "+obj.name,
                    'email_to'      : email_to, 
                    'email_cc'      : email,
                    'email_from'    : email, 
                    'body_html'     : body_html.encode('utf-8'), 
                    'attachment_ids': [(6, 0, [attachment_id.id])] 
                }
                email_id=self.env['mail.mail'].create(email_vals)
                self.env['mail.mail'].send(email_id)


class is_export_edi_histo(models.Model):
    _name='is.export.edi.histo'
    _order='name desc'

    edi_id      = fields.Many2one('is.export.edi', 'Export EDI', required=True, ondelete='cascade', readonly=True)
    name        = fields.Datetime("Date")
    user_id     = fields.Many2one('res.users', 'Utilisateur')
    description = fields.Char("Opération éffectuée")

    _defaults = {
        'name'   : lambda *a: fields.datetime.now(),
        'user_id': lambda obj, cr, uid, context: uid,
    }







