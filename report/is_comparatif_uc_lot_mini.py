# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_comparatif_uc_lot_mini(models.Model):
    _name='is.comparatif.uc.lot.mini'
    _order='product_id'
    _auto = False

    product_id         = fields.Many2one('product.template', 'Article')
    is_category_id     = fields.Many2one('is.category', 'Catégorie')
    uc                 = fields.Float('Conditionnement')
    lot_mini           = fields.Float("Lot d'appro")
    multiple           = fields.Float("Multiple")
    test_lot_mini      = fields.Float("Test Lot d'appro")
    test_multiple      = fields.Float("Test Multiple")


    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_comparatif_uc_lot_mini')
        cr.execute("""

CREATE OR REPLACE FUNCTION is_qt_par_uc(product_template_id integer) RETURNS float AS $$
BEGIN
    RETURN (select qty from product_packaging where product_tmpl_id=product_template_id order by id limit 1);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE view is_comparatif_uc_lot_mini AS (
    select 
        pt.id                   as id,
        pt.id                   as product_id, 
        pt.is_category_id       as is_category_id, 
        is_qt_par_uc(pt.id)     as uc,
        pt.lot_mini             as lot_mini,
        pt.multiple             as multiple,
        round(cast(pt.lot_mini      / is_qt_par_uc(pt.id) as numeric),4) as test_lot_mini,
        round(cast(pt.multiple      / is_qt_par_uc(pt.id) as numeric),4) as test_multiple
    from product_template pt 
    where 
        pt.id>0
        and is_qt_par_uc(pt.id)!=0
        and (
            round(cast(pt.lot_mini/is_qt_par_uc(pt.id) as numeric),0) != round(cast(pt.lot_mini/is_qt_par_uc(pt.id) as numeric),4) 
            or
            (round(cast(pt.multiple/is_qt_par_uc(pt.id) as numeric),0) != round(cast(pt.multiple/is_qt_par_uc(pt.id) as numeric),4) and multiple>1)
        )
)

        """)



