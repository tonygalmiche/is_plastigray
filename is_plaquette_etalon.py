# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning
from datetime import datetime
from dateutil.relativedelta import relativedelta


class is_plaquette_etalon(models.Model):
    _name='is.plaquette.etalon'
    _order='code_pg'
    _rec_name='code_pg'
    _sql_constraints = [('code_pg_uniq','UNIQUE(code_pg)', u'Ce code existe déjà')]

    code_pg = fields.Char("Code PG", required=True)
    designation = fields.Char("Désignation", required=True)
    fabriquant     = fields.Char("Fabricant")
    date_reception = fields.Date("Date de réception")
    site_id = fields.Many2one("is.database", "Site")
    lieu_stockage = fields.Char("Lieu de stockage")
    
    periodicite = fields.Integer("Périodicité (en mois)")
    type_controle = fields.Selection([('colorimetre','colorimètre'),('visuel','visuel')],string="Type de contrôle")
    date_prochain_controle= fields.Date("Date prochain contrôle", compute='_compute_date_prochain_controle', readonly=True, store=True)    
    controle_ids = fields.One2many('is.historique.controle', 'plaquette_id', string='Historique des contrôles')


    @api.multi
    @api.depends('controle_ids','periodicite')
    def _compute_date_prochain_controle(self):
        for rec in self:
            if rec.controle_ids:
                for row in rec.controle_ids:
                    if row.operation_controle_id.code!='arret':
                        date_controle=row.date_controle
                        if date_controle:
                            date_controle = datetime.strptime(date_controle, "%Y-%m-%d")
                            if rec.periodicite:
                                periodicite = int(rec.periodicite)
                            else:periodicite = 0
                            date_prochain_controle = date_controle + relativedelta(months=periodicite)
                            rec.date_prochain_controle = date_prochain_controle.strftime('%Y-%m-%d')
                    else:
                        rec.date_prochain_controle = False
                    break







