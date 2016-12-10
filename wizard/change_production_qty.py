# -*- coding: utf-8 -*-

from openerp.exceptions import except_orm
from openerp import models, fields, api, _



class change_production_qty(models.TransientModel):
    _inherit = "change.production.qty"

    @api.one
    def change_prod_qty(self):
        print "### TEST ###"
        for obj in self:
            print obj, obj.product_qty
            #obj.product_qty=88


        prod_obj = self.env['mrp.production']
        prod = prod_obj.browse(self._context.get('active_id'))
        print prod


        res = super(change_production_qty, self).change_prod_qty()


        return res

