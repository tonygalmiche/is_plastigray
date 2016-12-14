# -*- coding: utf-8 -*-

from openerp import tools
from openerp.osv import fields,osv
from openerp.addons.decimal_precision import decimal_precision as dp

class report_stock_lot_change_location(osv.osv):
    _name = "report.stock.lot.change.location"
    _description = "stock des produits par lot"
    _order = "product_id,location_id,lot_id"
    _auto = False
    _columns = {
        'product_id' : fields.many2one('product.product', 'Article'    , readonly=True),
        'mold'       : fields.char('Moule'                             , readonly=True),
        'location_id': fields.many2one('stock.location', 'Emplacement' , readonly=True),
        'qty'        : fields.float(u'Quantité'                        , readonly=True),
        'qty_par_uc' : fields.integer(u'UC'                            , readonly=True),
        'qty_uc'     : fields.float(u'Nb UC'                           , readonly=True),
        'lot_id'     : fields.many2one('stock.production.lot', 'Lot'   , readonly=True),
        'in_date'    : fields.datetime('Incoming Date'                 , readonly=True),
        'operation'  : fields.selection([
                                ('bloque', u'Bloqué'),
                                ('debloque', u'Débloqué'),
                                ('change_location', 'Changement emplacement'),
                                ('rebut', 'Mise au rebut')], 'Operation', readonly=True),     
    }
    
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_stock_lot_change_location')
        cr.execute("""
                CREATE OR REPLACE view report_stock_lot_change_location AS (
                SELECT
                        min(quant.id) as id,
                        sum(quant.qty) as qty,
                        is_qt_par_uc2(pp.product_tmpl_id) as qty_par_uc,
                        (sum(quant.qty) / is_qt_par_uc2(pp.product_tmpl_id))  as qty_uc,
                        quant.lot_id as lot_id,
                        quant.product_id as product_id,
                        im.name            as mold,
                        quant.location_id as location_id,
                        'change_location' as operation,
                        max(quant.in_date) as in_date
                FROM
                        stock_quant quant INNER JOIN stock_location location ON (quant.location_id = location.id)
                                          INNER JOIN product_product pp      ON quant.product_id  = pp.id
                                          INNER JOIN product_template pt     ON pp.product_tmpl_id = pt.id
                                          LEFT OUTER JOIN is_mold im         ON pt.is_mold_id=im.id 
                WHERE   quant.lot_id is not Null
                AND     location.usage = 'internal'
                GROUP BY quant.lot_id, quant.product_id, pp.product_tmpl_id, im.name, quant.location_id
                HAVING     sum(quant.qty) > 0
                ORDER BY quant.product_id
               )
        """)
    
report_stock_lot_change_location()
