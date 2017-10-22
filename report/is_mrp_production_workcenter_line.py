# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_mrp_production_workcenter_line(models.Model):
    _name='is.mrp.production.workcenter.line'
    _order='workcenter_id,is_ordre'
    _auto = False

    name               = fields.Many2one('mrp.production', 'Ordre de fabrication')
    product_id         = fields.Many2one('product.product', 'Article')
    state              = fields.Char('Etat')
    mpwl_id            = fields.Many2one('mrp.production.workcenter.line', 'Ordre de travail')
    workcenter_id      = fields.Many2one('mrp.workcenter', 'Poste de travail')
    sequence           = fields.Integer('Sequence')
    hour               = fields.Float("Nombre d'Heures")
    cycle              = fields.Float("Nombre de cycles")
    is_ordre           = fields.Integer(' Ordre ')
    is_date_tri        = fields.Datetime('Date tri')
    is_date_planning   = fields.Datetime('Date planning')

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_mrp_production_workcenter_line')
        cr.execute("""
            CREATE OR REPLACE view is_mrp_production_workcenter_line AS (
                select
                    mpwl.id               as id,
                    mp.id                 as name,
                    mp.product_id         as product_id,
                    mp.state              as state,
                    mpwl.id               as mpwl_id,
                    mpwl.workcenter_id    as workcenter_id,
                    mpwl.sequence         as sequence,
                    mpwl.hour             as hour,
                    mpwl.cycle            as cycle,
                    mpwl.is_ordre         as is_ordre,
                    mpwl.is_date_tri      as is_date_tri,
                    mpwl.is_date_planning as is_date_planning
                from mrp_production_workcenter_line mpwl inner join mrp_production mp on mpwl.production_id=mp.id
                where mp.state<>'cancel'
                order by mpwl.workcenter_id, mpwl.is_ordre
            )
        """)

