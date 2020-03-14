# -*- coding: utf-8 -*-

from openerp import models,fields,api
import datetime
import time


class assistent_report1(models.TransientModel):
    _name = "assistent.report1"


    def date_debut_mois():
        now = datetime.date.today()                               # Date du jour
        date_debut_mois = datetime.datetime( now.year, now.month, 1 )   # Premier jour du mois
        return date_debut_mois.strftime('%Y-%m-%d')                     # Formatage


    site= fields.Selection([
            ("1", "Gray"), 
            ("4", "ST-Brice"), 
        ], "Site", required=True)
    version = fields.Selection([
            ("1", "1"),
            ("2", "2"),
            ("3", "3"),
        ], "Version du rapport", required=True, default="2")
    type_rapport= fields.Selection([
            ("rapport_mois", "Liste mensuelle"), 
            ("rapport_date_a_date", "Liste de date à date"),  
            ("rapport_a_date", "Liste à date")             
        ], "Modèle de rapport", required=True)
    date_jour   = fields.Date("Date", required=False)
    date_mois   = fields.Date("Date dans le mois", required=False)
    date_debut  = fields.Date("Date de début", required=False)
    date_fin    = fields.Date("Date de fin", required=False)
    employee    = fields.Many2one('hr.employee', 'Employé', required=False, ondelete='set null', help="Sélectionnez un employé")
    interimaire = fields.Boolean('Intérimaire',  help="Cocher pour sélectionner uniquement les intérimaires")
    saut_page   = fields.Boolean('Saut de page',  help="Cocher pour avoir un saut de page pour chaque employé")
    detail      = fields.Boolean("Vue détaillée")


    _defaults = {
        'date_jour':  time.strftime('%Y-%m-%d'),
        'date_mois':  date_debut_mois(),
        'date_debut': date_debut_mois(),
        'date_fin':   time.strftime('%Y-%m-%d'),
        'type_rapport': 'rapport_mois',
    }


    def assistent_report1(self, cr, uid, ids, context=None):
        report_data = self.browse(cr, uid, ids[0])
        report_link = "http://odoo/odoo-rh/rapport"+ str(report_data.version)+".php"
        url = str(report_link) + '?'+ '&type_rapport=' + str(report_data.type_rapport)+'&site=' + str(report_data.site)+ '&date_jour=' + str(report_data.date_jour)+ '&date_mois=' + str(report_data.date_mois)+'&detail='+str(report_data.detail)+'&employee='+str(report_data.employee.id)+'&interimaire='+str(report_data.interimaire)+'&saut_page='+str(report_data.saut_page)+ '&date_debut=' + str(report_data.date_debut)+ '&date_fin=' + str(report_data.date_fin)
        return {
            'name'     : 'Go to website',
            'res_model': 'ir.actions.act_url',
            'type'     : 'ir.actions.act_url',
            'target'   : 'current',
            'url'      : url
        }


