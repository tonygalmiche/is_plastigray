# -*- coding: utf-8 -*-

import csv
import numpy as np
import xlrd

from openerp.tools.translate import _
from openerp import netsvc
from openerp import models,fields,api
from lxml import etree
from tempfile import TemporaryFile
import base64
import os
import time
from datetime import date, datetime


#TODO : 
#- Rechercher la commande Odoo dans la fonction d'import eCar et non pas en général
#- Créer une nouvelle fonction d'import eCar en plus de xml1 et cvs1
#- Importer les commandes dans Odoo
#- Tenir compte du type d'import du client
#- Faire fonctionner l'import CSV


class is_edi_cde_cli_line(models.Model):
    _name = "is.edi.cde.cli.line"
    _order = "edi_cde_cli_id,ref_article_client,date_livraison"

    edi_cde_cli_id      = fields.Many2one('is.edi.cde.cli', 'EDI Commandes Clients', required=True, ondelete='cascade')
    num_commande_client = fields.Char('N° Cde Client')
    ref_article_client  = fields.Char('Ref Article Client')
    quantite            = fields.Integer('Quantité')
    date_livraison      = fields.Date('Date liv')
    type_commande       = fields.Selection([('ferme', 'Ferme'),('previsionnel', 'Prév.')], "Type")
    order_id            = fields.Many2one('sale.order', 'Cde Odoo')
    anomalie            = fields.Char('Anomalie')


    @api.multi
    def action_acceder_commande(self):
        dummy, view_id = self.env['ir.model.data'].get_object_reference('sale', 'view_order_form')
        for obj in self:
            return {
                'name': "Commande",
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'sale.order',
                'type': 'ir.actions.act_window',
                'res_id': obj.order_id.id,
                'domain': '[]',
            }




class is_edi_cde_cli(models.Model):
    _name = "is.edi.cde.cli"
    _description = "EDI commandes clients"  

    name            = fields.Date('Date de création', readonly='1')
    partner_id      = fields.Many2one('res.partner', 'Client', required=False)
    import_function = fields.Char("Fonction d'importation", compute='_import_function', readonly=True)
    file_ids        = fields.Many2many('ir.attachment', 'is_doc_attachment_rel', 'doc_id', 'file_id', 'Fichiers')
    create_id       = fields.Many2one('res.users', 'Importe par', readonly=True)
    create_date     = fields.Datetime("Date d'importation")
    state           = fields.Selection([('analyse', u'Analyse'),('traite', u'Traité')], u"État", readonly=True, select=True)
    line_ids        = fields.One2many('is.edi.cde.cli.line', 'edi_cde_cli_id', u"Commandes a importer")

    _defaults = {
        'name' : fields.Datetime.now,
        'state': 'analyse',
    }

    @api.depends('partner_id')
    def _import_function(self):
        for obj in self:
            if obj.partner_id:
                obj.import_function=obj.partner_id.is_import_function


    @api.multi
    def action_analyser_fichiers(self):
        for obj in self:

            for row in obj.line_ids:
                row.unlink()

            line_obj = self.env['is.edi.cde.cli.line']
            for attachment in obj.file_ids:
                datas = self.get_data(obj.import_function, attachment)

                for row in datas:
                    num_commande_client = row["num_commande_client"]
                    ref_article_client  = row["ref_article_client"]
                    order=self.env['sale.order'].search([
                        ('partner_id'      , '=', obj.partner_id.id),
                        ('is_ref_client'   , '=', ref_article_client),
                        ('client_order_ref', '=', num_commande_client)]
                    )
                    order_id=False
                    anomalie="Non trouvée"
                    if len(order):
                        order_id=order[0].id
                        anomalie=""
                    for ligne in row["lignes"]:
                        vals={
                            'edi_cde_cli_id'     : obj.id,
                            'num_commande_client': num_commande_client,
                            'ref_article_client' : ref_article_client,
                            'quantite'           : ligne["quantite"],
                            'date_livraison'     : ligne["date_livraison"],
                            'type_commande'      : ligne["type_commande"],
                            'order_id'           : order_id,
                            'anomalie'           : anomalie,
                        }
                        line_obj.create(vals)


    @api.multi
    def action_importer_commandes(self):
        for obj in self:
            line_obj       = self.env['sale.order.line']
            for line in obj.line_ids:
                if line.order_id:
                    order_line=line_obj.search([
                        ('order_id', '=', line.order_id.id),
                        ('is_date_livraison', '=', line.date_livraison)]
                    )
                    for row in order_line:
                        row.unlink()
                    vals={
                        'order_id':line.order_id.id, 
                        'is_date_livraison':line.date_livraison, 
                        'is_type_commande':line.type_commande, 
                        'product_id':line.order_id.is_article_commande_id.id, 
                        'product_uom_qty':line.quantite, 
                    }
                    line_obj.create(vals)
            obj.state='traite'


    @api.multi
    def get_data(self, import_function, attachment):
        datas={}
        if import_function=="eCar":
            datas=self.get_data_eCar(attachment)
        return datas


    @api.multi
    def get_data_eCar(self, attachment):
        res = []
        for obj in self:
            filename = '/tmp/%s.xml' % attachment.id
            temp = open(filename, 'w+b')
            temp.write((base64.decodestring(attachment.datas))) 
            temp.close()
            tree = etree.parse(filename)

            for partie_citee in tree.xpath("/DELINS/PARTIE_CITEE"):
                if  partie_citee.xpath("ARTICLE_PROGRAMME"):
                    val = {
                        'ref_article_client': partie_citee.xpath("ARTICLE_PROGRAMME/NumeroArticleClient")[0].text,
                        'num_commande_client': partie_citee.xpath("ARTICLE_PROGRAMME/NumeroCommande")[0].text,
                        'lignes': []
                    }
                    res1 = []
                    for detail_programme in partie_citee.xpath("ARTICLE_PROGRAMME/DETAIL_PROGRAMME"):
                        type_commande=detail_programme.xpath("CodeStatutProgramme")[0].text
                        if type_commande=="4":
                            type_commande="previsionnel"
                        else:
                            type_commande="ferme"
                        ligne = {
                            'quantite'      : detail_programme.xpath("QuantiteALivrer")[0].text,
                            'type_commande' : type_commande,
                            'date_livraison': detail_programme.xpath("DateHeureLivraisonAuPlusTot")[0].text[:8],
                        }
                        res1.append(ligne)
                    
                    val.update({'lignes':res1})
                    res.append(val)
                else:
                    continue

            for partie_citee in tree.xpath("/CALDEL/SEQUENCE_PRODUCTION"):
                if  partie_citee.xpath("ARTICLE_PROGRAMME"):
                    ref_article_client=partie_citee.xpath("ARTICLE_PROGRAMME/NumeroArticleClient")[0].text
                    order=self.env['sale.order'].search([
                        ('partner_id'   , '=', obj.partner_id.id),
                        ('is_ref_client', '=', ref_article_client)]
                    )
                    num_commande_client="??"
                    if len(order):
                        num_commande_client=order[0].client_order_ref
                    val = {
                        'ref_article_client': ref_article_client,
                        'num_commande_client': num_commande_client,
                        'lignes': []
                    }
                    res1 = []
                    for detail_programme in partie_citee.xpath("ARTICLE_PROGRAMME/DETAIL_PROGRAMME_ARTICLE"):
                        ligne = {
                            'quantite': detail_programme.xpath("QteALivrer")[0].text,
                            'type_commande': 'ferme',
                            'date_livraison': detail_programme.xpath("DateHeureLivraisonAuPlusTot")[0].text[:8],
                        }
                        res1.append(ligne)
                    val.update({'lignes':res1})
                    res.append(val)
                else:
                    continue

        return res

