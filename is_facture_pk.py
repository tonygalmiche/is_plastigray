# -*- coding: utf-8 -*-
from openerp import models,fields,api
import time
from datetime import datetime

class is_facture_pk(models.Model):
    _name='is.facture.pk'
    _rec_name = 'num_facture'
    
    @api.depends('date_facture')
    def _compute_annee_facture(self):
        for obj in self:
            date_year = ''
            if obj.date_facture:
                date_year = datetime.strptime(str(obj.date_facture), '%Y-%m-%d')
                date_year = date_year.strftime('%Y')
            obj.annee_facture = date_year

    num_facture = fields.Char('N° de Facture')
    date_facture = fields.Date('Date de facture')
    annee_facture = fields.Char('Année de la facture', compute='_compute_annee_facture', store=True)
    num_bl = fields.Many2one('stock.picking', string='N° de BL')
    line_ids = fields.One2many('is.facture.pk.line', 'is_facture_id', string='Lignes de la facture')
    
    _defaults = {
        'date_facture': time.strftime('%Y-%m-%d'),
    }
    
    @api.multi
    def write(self,vals):
        stock_picking_obj = self.env['stock.picking']
        if vals.get('num_bl', False):
            picking = stock_picking_obj.search([('id', '=', vals['num_bl'])])
            line_ids = []
            for move in picking.move_lines:
                val = {
                    'ref_pk': move.product_id and move.product_id.is_code or False,
                    'designation': move.product_id and move.product_id.name or '',
                    'poids': move.product_id and move.product_id.weight or 0,
                    'qt': move.product_uom_qty,
                    'pump': move.is_sale_line_id.price_unit,
                }
                line_ids.append((0, 0, val))
            self.line_ids.unlink()
            vals.update({'line_ids': line_ids})
        res=super(is_facture_pk, self).write(vals)
        return res
    
    @api.model
    def create(self, vals):
        data_obj = self.env['ir.model.data']
        stock_picking_obj = self.env['stock.picking']
        sequence_ids = data_obj.search([('name','=','seq_is_facture_pk')])
        if len(sequence_ids)>0:
            sequence_id = sequence_ids[0].res_id
            vals['num_facture'] = self.env['ir.sequence'].get_id(sequence_id, 'id')
        if vals.get('num_bl', False):
            picking = stock_picking_obj.search([('id', '=', vals['num_bl'])])
            line_ids = []
            for move in picking.move_lines:
                val = {
                    'ref_pk': move.product_id and move.product_id.is_code or False,
                    'designation': move.product_id and move.product_id.name or '',
                    'poids': move.product_id and move.product_id.weight or 0,
                    'qt': move.product_uom_qty,
                    'pump': move.is_sale_line_id.price_unit,
                }
                line_ids.append((0, 0, val))
            vals.update({'line_ids': line_ids})
        res = super(is_facture_pk, self).create(vals)
        return res


class is_facture_pk_line(models.Model):
    _name='is.facture.pk.line'
    
    @api.depends('qt','pump')
    def _compute_total_pf(self):
        for obj in self:
            obj.total_pf = obj.qt * obj.pump
    
    is_facture_id = fields.Many2one('is.facture.pk', string='Lignes')
    commande = fields.Char('Commande')
    ref_pk = fields.Char('Réf PK')
    designation = fields.Char('Désignation')
    poids = fields.Float('Poids')
    qt = fields.Float('Quantité')
    pump = fields.Float('P.U.M.P')
    ptmp = fields.Float('P.T.M.P')
    pupf = fields.Float('P.U.P.F')
    total_pf = fields.Float('P.Total P.F.', compute='_compute_total_pf', store=True)

