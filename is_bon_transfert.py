# -*- coding: utf-8 -*-
import datetime
from openerp import models,fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning
import os
import logging
_logger = logging.getLogger(__name__)


class is_bon_transfert(models.Model):
    _name = "is.bon.transfert"
    _inherit=['mail.thread']
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
    traitement_edi      = fields.Selection(related='partner_id.is_traitement_edi', string='Traitement EDI', readonly=True)
    date_traitement_edi = fields.Datetime("Date traitement EDI")


    _defaults = {
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


    @api.multi
    def get_is_code_rowspan(self,product_id):
        cr = self._cr
        for obj in self:
            SQL="""
                select count(*)
                from is_galia_base_uc uc inner join is_galia_base_um um on uc.um_id=um.id
                                         inner join is_bon_transfert bon on um.bon_transfert_id=bon.id
                                         inner join product_product pp on uc.product_id=pp.id 
                where 
                    bon.id="""+str(obj.id)+""" and 
                    uc.product_id="""+str(product_id)+""" 
            """
            cr.execute(SQL)
            result = cr.fetchall()
            nb=0
            for row in result:
                nb=row[0]
            return nb


    @api.multi
    def get_um_rowspan(self,product_id,um_id):
        cr = self._cr
        for obj in self:
            SQL="""
                select count(*)
                from is_galia_base_uc uc inner join is_galia_base_um um on uc.um_id=um.id
                                         inner join is_bon_transfert bon on um.bon_transfert_id=bon.id
                                         inner join product_product pp on uc.product_id=pp.id 
                where 
                    bon.id="""+str(obj.id)+""" and 
                    uc.product_id="""+str(product_id)+""" and
                    um.id="""+str(um_id)+""" 
            """
            cr.execute(SQL)
            result = cr.fetchall()
            nb=0
            for row in result:
                nb=row[0]
            return nb


    @api.multi
    def get_etiquettes(self):
        cr = self._cr
        res=[]
        for obj in self:
            SQL="""
                select 

                    pt.is_code,
                    um.name,
                    uc.num_eti,
                    uc.qt_pieces,
                    pp.id,
                    um.id
                from is_galia_base_uc uc inner join is_galia_base_um um on uc.um_id=um.id
                                         inner join is_bon_transfert bon on um.bon_transfert_id=bon.id
                                         inner join product_product pp on uc.product_id=pp.id 
                                         inner join product_template pt on pp.product_tmpl_id=pt.id
                where bon.id="""+str(obj.id)+"""
                order by pt.is_code, um.name, uc.num_eti
            """
            cr.execute(SQL)
            result = cr.fetchall()
            ct_code = 0
            ct_um   = 0
            is_code_rowspan = 0
            um_rowspan = 0
            mem_code = ''
            mem_um   = ''
            for row in result:
                is_code_rowspan=0
                um_rowspan=0
                if row[0]!=mem_code:
                    mem_code=row[0]
                    is_code_rowspan=self.get_is_code_rowspan(row[4])
                    ct_code=0

                is_code_um = (row[0]+row[1])
                if is_code_um!=mem_um:
                    mem_um=is_code_um
                    um_rowspan=self.get_um_rowspan(row[4],row[5])
                    ct_um=0

                ct_code+=1
                ct_um+=1

                vals={
                    'is_code'  : row[0],
                    'um'       : row[1],
                    'uc'       : row[2],
                    'qt_pieces': row[3],
                    'is_code_rowspan': is_code_rowspan,
                    'um_rowspan': um_rowspan,
                }
                res.append(vals)
        return res


    @api.multi
    def desadv_action(self):
        for obj in self : 
            cdes = self.env['is.commande.externe'].search([('name','=',"edi-tenor-desadv")])
            for cde in cdes:
                model=self._name
                uid=self._uid
                user=self.env['res.users'].browse(uid)
                soc=user.company_id.partner_id.is_code
                x = cde.commande
                x = x.replace("#soc"   , soc)
                x = x.replace("#model" , model)
                x = x.replace("#res_id", str(obj.id))
                x = x.replace("#uid"   , str(uid))
                lines=os.popen(x).readlines()
                for line in lines:
                    _logger.info(line.strip())
                now = datetime.datetime.now()
                obj.date_traitement_edi = now
                body = u"<b>DESADV envoyé</b><br>"+"<br>".join(lines)
                vals={
                    'author_id': user.partner_id.id,
                    'type'     : "notification",
                    'body'     : body,
                    'model'    : model,
                    'res_id'   : obj.id
                }
                res=self.env['mail.message'].create(vals)


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

    @api.depends('product_id','quantite')
    def _compute_point_dechargement(self):
        for obj in self:
            x = False
            if obj.bon_transfert_id.partner_id.is_traitement_edi:
                orders = self.env['sale.order'].search([
                    ('partner_id.is_code', '=', obj.bon_transfert_id.partner_id.is_code),
                    ('is_ref_client'     , '=', obj.product_id.is_ref_client),
                    ('is_type_commande'  , '=', 'ouverte'),
                ])
                for order in orders:
                    x = order.is_point_dechargement
            obj.point_dechargement = x


    bon_transfert_id   = fields.Many2one('is.bon.transfert', 'Bon de transfert', required=True, ondelete='cascade', readonly=True)
    product_id         = fields.Many2one('product.product', 'Article', required=True)
    mold_id            = fields.Many2one('is.mold', 'Moule'      , compute='_compute', readonly=True, store=True)
    ref_client         = fields.Char('Référence client'          , compute='_compute', readonly=True, store=True)
    quantite           = fields.Float('Quantité', digits=(14,0))
    uom_id             = fields.Many2one('product.uom', 'Unité'  , compute='_compute', readonly=True, store=True)
    uc_id              = fields.Many2one('product.ul', 'UC'      , compute='_compute', readonly=True, store=True)
    nb_uc              = fields.Float('Nb UC'                    , compute='_compute', readonly=True, store=True, digits=(14,1))
    um_id              = fields.Many2one('product.ul', 'UM'      , compute='_compute', readonly=True, store=True)
    nb_um              = fields.Float('Nb UM'                    , compute='_compute', readonly=True, store=True, digits=(14,1))
    point_dechargement = fields.Char(u'Point de déchargement', compute='_compute_point_dechargement', readonly=True, store=False)

