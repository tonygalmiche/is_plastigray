# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import Warning


#TODO : 
# - Ajouter les filtres dans la zone de recherche sur toutes les colonnes $
# - Revoir le niveau en champ de type texte avec des tirets devant
# - Ajouter le segment


class  is_cas_emploi_wizard_new(models.TransientModel):
    _name = 'is.cas.emploi.wizard.new'
    
    
    product_id = fields.Many2one('product.product','Article', required=True)
    


    @api.multi
    def cas_emploi(self, wizard_id, composant_id, niveau):
        cr=self._cr
        sql="""
            select 
                mbl.sequence,
                mbl.product_id,
                mbl.product_qty,
                mb.product_tmpl_id,
                mb.id mb_id,
                (select id from product_product where product_tmpl_id=mb.product_tmpl_id limit 1) compose_id,
                mb.is_sous_traitance,
                mb.is_negoce,
                mb.is_inactive
            from mrp_bom_line mbl inner join mrp_bom mb on mbl.bom_id=mb.id
            where mbl.product_id="""+str(composant_id)+"""
        """
        cr.execute(sql)
        result=cr.fetchall()
        for row in result:
            compose_id=row[5]
            compose=self.env['product.product'].browse(compose_id)

            niveau_txt=''
            for i in range(1, niveau):
                niveau_txt=niveau_txt+u'-'
            niveau_txt=niveau_txt+str(niveau)

            vals={
                'wizard_id'         : wizard_id,
                'niveau'            : niveau_txt,
                'composant_id'      : composant_id,
                'ligne'             : row[0],
                'quantite'          : row[2],
                'mrp_bom_id'        : row[4],
                'segment_id'        : compose.segment_id.id,
                'is_categery_id'    : compose.is_category_id.id,
                'is_gestionnaire_id': compose.is_gestionnaire_id.id,
                'is_mold_dossierf'  : compose.is_mold_dossierf,
                'is_ref_client'     : compose.is_ref_client,
                'is_ref_fournisseur': compose.is_ref_fournisseur,
                'is_client_id'      : compose.is_client_id.id,
                'is_fournisseur_id' : compose.is_fournisseur_id.id,
                'is_sous_traitance' : row[6],
                'is_negoce'         : row[7],
                'is_inactive'       : row[8],
            }
            res=self.env['is.cas.emploi.line'].create(vals)
            self.cas_emploi(wizard_id, compose_id,niveau+1)



    @api.multi
    def do_search_component(self):
        for obj in self:
            print obj, obj.product_id
            if obj.product_id:
                self.cas_emploi(obj.id, obj.product_id.id,1)
        return {
            'name': u"Cas d'emploi "+str(obj.product_id.is_code),
            'view_mode': 'tree,form',
            'view_type': 'form',
            'res_model': 'is.cas.emploi.line',
            'type': 'ir.actions.act_window',
            'domain': [('wizard_id','=',obj.id)],
        }


class is_cas_emploi_line(models.TransientModel):
    _name = 'is.cas.emploi.line'
    
    wizard_id          = fields.Many2one('is.cas.emploi.wizard.new','Wizard')
    niveau             = fields.Char('Niveau')
    composant_id       = fields.Many2one('product.product','Composant')
    ligne              = fields.Integer('Ligne')
    quantite           = fields.Float('Quantité', digits=(14,6))
    mrp_bom_id         = fields.Many2one('mrp.bom','Composé')
    segment_id         = fields.Many2one('is.product.segment','Segment')
    is_categery_id     = fields.Many2one('is.category','Catégorie')
    is_gestionnaire_id = fields.Many2one('is.gestionnaire','Gestionnaire')
    is_mold_dossierf   = fields.Char('Moule ou Dossier F')
    is_ref_client      = fields.Char('Référence client')
    is_ref_fournisseur = fields.Char('Référence fournisseur')
    is_client_id       = fields.Many2one('res.partner', 'Client par défaut')
    is_fournisseur_id  = fields.Many2one('res.partner', 'Fournisseur par défaut')
    is_sous_traitance  = fields.Boolean('Nomenclature de sous-traitance')
    is_negoce          = fields.Boolean('Nomenclature de négoce')
    is_inactive        = fields.Boolean('Nomenclature inactive')


