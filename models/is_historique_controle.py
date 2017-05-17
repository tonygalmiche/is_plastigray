# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 Mars IT Solution (<http://www.marsits.com/>) 
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning
from datetime import datetime

class is_historique_controle(models.Model):
    _name='is.historique.controle'

    plaquette_id = fields.Many2one('is.plaquette.etalon', string='Plaquette étalon')
    instrument_id = fields.Many2one('is.instrument.mesure', string='Instruments de mesure')
    gabarit_id = fields.Many2one('is.gabarit.controle', string='Gabarit de contrôle')
    date_controle = fields.Date(string='Date du contrôle', default=fields.Date.context_today, copy=False)
    site_id = fields.Many2one('is.emplacement.outillage', string='Site')
    affectation = fields.Char(string='Affectation')
    operation = fields.Selection([('c','Création'),('v','Vérification'),('e','Étalonnage'),('m','Maintenance'),
                                 ('t','Transfert de société'),('a','Arrêt étalonnage'),('f',' Fin de vie')], string='Opération')
    organisme = fields.Char(string='Organisme')
    resultat = fields.Char(string='Résultat')
    commentaire = fields.Char(string='Commentaire')
    classe = fields.Char(string='Classe')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4
