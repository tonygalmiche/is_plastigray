# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_comparatif_gamme_standard_generique(models.Model):
    _name='is.comparatif.gamme.standard.generique'
    _order='product_id'
    _auto = False

    product_id                 = fields.Many2one('product.template', 'Article')
    standard_routing_id        = fields.Many2one('mrp.routing', 'Gamme Standard')
    standard_sequence          = fields.Integer('Sequence')
    standard_name              = fields.Char('Nom')
    standard_workcenter_id     = fields.Many2one('mrp.workcenter', 'Poste de charge')
    standard_nb_secondes       = fields.Float('Nb secondes')


    #routing_generique_id       = fields.Many2one('mrp.routing', 'Gamme Générique')

    #workcenter_generique_id    = fields.Many2one('mrp.workcenter', 'Poste de charge générique')

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_comparatif_gamme_standard_generique')

        cr.execute("""
            CREATE OR REPLACE view is_comparatif_gamme_standard_generique AS (
                SELECT 
                    mb.id,
                    mb.product_tmpl_id  as product_id,
                    mr1.id              as standard_routing_id,
                    mrw1.sequence       as standard_sequence,
                    mrw1.name           as standard_name,
                    mrw1.workcenter_id  as standard_workcenter_id,
                    mrw1.is_nb_secondes as standard_nb_secondes
                FROM mrp_bom mb inner join mrp_routing mr1             on mb.routing_id=mr1.id
                                inner join mrp_routing_workcenter mrw1 on mr1.id=mrw1.routing_id


                WHERE mb.id>0
            )
        """)

#routing_id
#sequence name is_nb_secondes
#                                inner join mrp_routing mr2             on mb.is_gamme_generique_id=mr2.id
#                                inner join mrp_routing_workcenter mrw2 on mr2.id=mrw2.routing_id
#                    mr2.id             as routing_generique_id,
#                    mrw2.workcenter_id as workcenter_generique_id
