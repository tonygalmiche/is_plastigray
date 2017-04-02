# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_product_packaging(models.Model):
    _name='is.product.packaging'
    _order='product_tmpl_id,sequence,id'
    _auto = False

    product_tmpl_id    = fields.Many2one('product.template', 'Article')
    segment_id         = fields.Many2one('is.product.segment', 'Segment')
    is_category_id     = fields.Many2one('is.category', 'Catégorie')
    is_gestionnaire_id = fields.Many2one('is.gestionnaire', 'Gestionnaire')
    is_mold_dossierf   = fields.Char('Moule ou Dossier F')
    weight_net         = fields.Float('Poids net',  digits=(14, 4))
    weight             = fields.Float('Poids brut', digits=(14, 4))
    sequence           = fields.Integer('Séquence')
    qty                = fields.Integer('Quantité par colis')
    ul                 = fields.Many2one('product.ul', 'Unité logistique colis')
    ul_qty             = fields.Integer('Colis par couche')
    rows               = fields.Integer('Nombre de couches')
    ul_container       = fields.Many2one('product.ul', 'Unité logistique palette')

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_product_packaging')
        cr.execute("""
            CREATE OR REPLACE view is_product_packaging AS (
                select 
                    pack.id,
                    pack.product_tmpl_id,
                    pt.segment_id,
                    pt.is_category_id,
                    pt.is_gestionnaire_id,
                    pt.is_mold_dossierf,
                    pt.weight_net,
                    pt.weight,
                    pack.sequence, 
                    pack.qty, 
                    pack.ul,
                    pack.ul_qty, 
                    pack.rows,
                    pack.ul_container
                from product_template pt inner join product_packaging pack on pt.id=pack.product_tmpl_id
            );
        """)



