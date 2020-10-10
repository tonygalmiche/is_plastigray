# -*- coding: utf-8 -*-
import datetime
from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning


class is_bon_transfert(models.Model):
    _name = "is.bon.transfert"
    _description = "Bon de transfert"
    _order='name desc'

    name            = fields.Char('N° de bon de transfert', readonly=True)
    location_id     = fields.Many2one('stock.location', 'Emplacement (Navette)', required=True)
    date_creation   = fields.Date('Date de création', readonly=True)
    date_fin        = fields.Date('Date de dernière entrée')
    partner_id      = fields.Many2one('res.partner', 'Client')
    transporteur_id = fields.Many2one('res.partner', 'Transporteur')
    commentaire     = fields.Text('Commentaire')
    qt_total        = fields.Float('Quantité totale', compute='_compute', readonly=True, store=True, digits=(14,0))
    total_uc        = fields.Float('Total UC'       , compute='_compute', readonly=True, store=True, digits=(14,1))
    total_um        = fields.Float('Total UM'       , compute='_compute', readonly=True, store=True, digits=(14,1))
    line_ids        = fields.One2many('is.bon.transfert.line'  , 'bon_transfert_id', u"Lignes")
    galia_um_ids    = fields.One2many('is.galia.base.um', 'bon_transfert_id', u"UMs scannées", readonly=True)

    #def _date():
    #    return datetime.date.today().strftime('%Y-%m-%d')

    _defaults = {
        #'date_creation':  _date(),
        'date_creation':  lambda *a: fields.datetime.now(),
    }


    @api.depends('line_ids')
    def _compute(self):
        cr = self._cr
        for obj in self:
            qt_total=total_uc=total_um=0
            for line in obj.line_ids:
                qt_total=qt_total+line.quantite
                total_uc=total_uc+line.nb_uc
                total_um=total_um+line.nb_um
            obj.qt_total=qt_total
            obj.total_uc=total_uc
            obj.total_um=total_um


    @api.model
    def create(self, vals):
        data_obj = self.env['ir.model.data']
        sequence_ids = data_obj.search([('name','=','is_bon_transfert_seq')])
        if sequence_ids:
            sequence_id = data_obj.browse(sequence_ids[0].id).res_id
            vals['name'] = self.env['ir.sequence'].get_id(sequence_id, 'id')
        res = super(is_bon_transfert, self).create(vals)
        return res


    @api.multi
    def on_change(self, location_id, date_fin):
        cr = self._cr
        value = {}
        lines = []
        if location_id and date_fin==False:
            SQL="""
                select sq.product_id, sum(sq.qty)
                from stock_quant sq
                where sq.location_id="""+str(location_id)+"""
                group by sq.product_id
                order by sq.product_id
                limit 200
            """
            cr.execute(SQL)
            result = cr.fetchall()
            for row in result:
                vals = {
                    'product_id': row[0],
                    'quantite'  : row[1],
                }
                lines.append(vals)
        if location_id and date_fin:
            SQL="""
                select sm.product_id, sum(sm.product_uom_qty)
                from stock_move sm
                where sm.location_dest_id="""+str(location_id)+"""
                      and date>='"""+str(date_fin)+""" 00:00:00'
                      and date<='"""+str(date_fin)+""" 23:59:59'
                group by sm.product_id
                order by sm.product_id
                limit 200
            """
            cr.execute(SQL)
            result = cr.fetchall()
            for row in result:
                vals = {
                    'product_id': row[0],
                    'quantite'  : row[1],
                }
                lines.append(vals)
        value.update({'line_ids': lines})
        return {'value': value}


#    @api.multi
#    def get_etiquettes(self):
#        cr = self._cr
#        for obj in self:
#            SQL="""
#                select 
#                    pt.is_code,
#                    uc.num_eti
#                from is_galia_base_uc uc inner join is_galia_base_um um on uc.um_id=um.id
#                                         inner join is_bon_transfert bon on um.bon_transfert_id=bon.id
#                                         inner join product_product pp on uc.product_id=pp.id 
#                                         inner join product_template pt on pp.product_tmpl_id=pt.id
#                where bon.id="""+str(obj.id)+"""
#                order by pt.is_code, uc.num_eti
#            """
#            cr.execute(SQL)
#            result = cr.fetchall()
#            mem_code_pg=''
#            mem_eti=0
#            res={}
#            nb=0
#            for row in result:
#                nb+=1
#                code_pg = row[0]
#                eti     = row[1]
#                if code_pg!=mem_code_pg:
#                    res[code_pg] = {}
#                    mem_code_pg = code_pg
#                if mem_eti!=(eti-nb):
#                    res[code_pg][eti] = []
#                    mem_eti=eti
#                    nb=0
#                res[code_pg][mem_eti].append(eti)
#            res2={}
#            for code_pg in res:
#                res2[code_pg]=[]
#                for eti in res[code_pg]:
#                    nb=len(res[code_pg][eti])
#                    if nb==1:
#                        v=str(res[code_pg][eti][0])
#                    else:
#                        v=str(res[code_pg][eti][0])+'..'+str(res[code_pg][eti][nb-1])[-4:]
#                    res2[code_pg].append(v)
#        return res2






    @api.multi
    def get_etiquettes(self):
        cr = self._cr
        res=[]
        for obj in self:
            SQL="""
                select 

                    pt.is_code,
                    uc.num_eti,
                    uc.qt_pieces,
                    um.name
                from is_galia_base_uc uc inner join is_galia_base_um um on uc.um_id=um.id
                                         inner join is_bon_transfert bon on um.bon_transfert_id=bon.id
                                         inner join product_product pp on uc.product_id=pp.id 
                                         inner join product_template pt on pp.product_tmpl_id=pt.id
                where bon.id="""+str(obj.id)+"""
                order by pt.is_code, uc.num_eti
            """
            cr.execute(SQL)
            result = cr.fetchall()
            for row in result:
                res.append(row)
        print res
        return res

























class is_bon_transfert_line(models.Model):
    _name='is.bon.transfert.line'
    _order='product_id'


    @api.depends('product_id','quantite')
    def _compute(self):
        cr = self._cr
        for obj in self:
            if obj.product_id:
                SQL="""
                    select  pa.ul, 
                            pa.qty, 
                            pa.ul_container, 
                            pa.rows*pa.ul_qty, 
                            pt.is_mold_id, 
                            pt.is_ref_client, 
                            pt.uom_id
                    from product_product pp left outer join product_packaging pa on pp.product_tmpl_id=pa.product_tmpl_id 
                                            inner join product_template       pt on pp.product_tmpl_id=pt.id
                    where pp.id="""+str(obj.product_id.id)+"""
                    limit 1
                """
                cr.execute(SQL)
                result = cr.fetchall()
                for row in result:
                    qt=obj.quantite
                    qt_par_uc=row[1] or 1
                    nb_uc=qt/qt_par_uc
                    qt_par_um=row[3] or 1
                    nb_um=qt/(qt_par_uc*qt_par_um)
                    obj.uc_id      = row[0]
                    obj.nb_uc      = nb_uc
                    obj.um_id      = row[2]
                    obj.nb_um      = nb_um
                    obj.mold_id    = row[4]
                    obj.ref_client = row[5]
                    obj.uom_id     = row[6]


    bon_transfert_id = fields.Many2one('is.bon.transfert', 'Bon de transfert', required=True, ondelete='cascade', readonly=True)
    product_id       = fields.Many2one('product.product', 'Article', required=True)
    mold_id          = fields.Many2one('is.mold', 'Moule'      , compute='_compute', readonly=True, store=True)
    ref_client       = fields.Char('Référence client'          , compute='_compute', readonly=True, store=True)
    quantite         = fields.Float('Quantité', digits=(14,0))
    uom_id           = fields.Many2one('product.uom', 'Unité'  , compute='_compute', readonly=True, store=True)
    uc_id            = fields.Many2one('product.ul', 'UC'      , compute='_compute', readonly=True, store=True)
    nb_uc            = fields.Float('Nb UC'                    , compute='_compute', readonly=True, store=True, digits=(14,1))
    um_id            = fields.Many2one('product.ul', 'UM'      , compute='_compute', readonly=True, store=True)
    nb_um            = fields.Float('Nb UM'                    , compute='_compute', readonly=True, store=True, digits=(14,1))


