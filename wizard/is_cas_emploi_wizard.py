from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import Warning


class  is_cas_emploi_wizard(models.TransientModel):
    _name = 'is.cas.emploi.wizard'
    
    
    product_id = fields.Many2one('product.product','Article')
    
    @api.multi
    def do_search_component(self):
        bom_ln_obj = self.env['mrp.bom.line']
        bom_obj = self.env['mrp.bom']
        parent_bom_lst = []
        for rec in self:
            bom_l_ids = bom_ln_obj.search([('product_id','=',rec.product_id.id)])
            bom_ids = bom_l_ids.mapped('bom_id')
            parent_bom_lst.extend(bom_l_ids.mapped('bom_id.id'))
            while(bom_ids):
                a_bom_list = []
                for bom in bom_ids:
                    a_bom_line_ids = bom_ln_obj.search([('product_id.product_tmpl_id','=',bom.product_tmpl_id.id)])
                    a_bom_list.extend(a_bom_line_ids.mapped('bom_id'))
                    parent_bom_lst.extend(a_bom_line_ids.mapped('bom_id.id'))
                bom_ids  = list(set(a_bom_list))
                
        return {
                'name': "Nomenclature",
                'view_mode': 'tree,form',
                'view_type': 'form',
                'res_model': 'mrp.bom',
                'type': 'ir.actions.act_window',
                'domain': [('id','in',list(set(parent_bom_lst)))],
            }
