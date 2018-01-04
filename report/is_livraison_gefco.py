# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_livraison_gefco(models.Model):
    _name='is.livraison.gefco'
    _order='is_date_expedition desc, name desc, product_id'
    _auto = False

    is_date_expedition  = fields.Date("Date d'expédition")
    partner_id          = fields.Many2one('res.partner', 'Client')
    name                = fields.Char('BL')
    is_mold_dossierf    = fields.Char('Moule ou Dossier F')
    product_id          = fields.Many2one('product.template', 'Article')

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_livraison_gefco')
        cr.execute("""
            CREATE OR REPLACE view is_livraison_gefco AS (
                select 
                    sm.id,
                    sp.is_date_expedition,
                    sp.partner_id,
                    sp.name,
                    pt.is_mold_dossierf,
                    pt.id product_id
                from stock_picking sp inner join stock_move       sm on sp.id=sm.picking_id
                                      inner join product_product  pp on sm.product_id=pp.id
                                      inner join product_template pt on pp.product_tmpl_id=pt.id
                                      inner join res_partner      rp on sp.partner_id=rp.id
                where 
                    pt.is_livraison_gefbox='t' and
                    sm.state='done' and
                    sp.state='done' and
                    sp.picking_type_id=2 
            )
        """)

