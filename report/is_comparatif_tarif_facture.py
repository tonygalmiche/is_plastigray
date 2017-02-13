# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models,fields,api
from openerp.tools.translate import _


class is_comparatif_tarif_facture(models.Model):
    _name='is.comparatif.tarif.facture'
    _order='invoice_id,product_id'
    _auto = False

    invoice_id         = fields.Many2one('account.invoice', 'Facture')
    invoice_date       = fields.Date('Date Facture')
    order_id           = fields.Many2one('sale.order', 'Commande')
    partner_id         = fields.Many2one('res.partner', 'Client')
    pricelist_id       = fields.Many2one('product.pricelist', 'Liste de prix')
    product_id         = fields.Many2one('product.template', 'Article')
    quantity           = fields.Float('Quantité')
    uos_id             = fields.Many2one('product.uom', 'Unité')
    invoice_price      = fields.Float('Prix facture')
    pricelist_price    = fields.Float('Prix liste de prix')
    price_delta        = fields.Float('Ecart de prix')
    lot_livraison      = fields.Float('Lot de livraison')
    prix_lot_livraison = fields.Float('Prix au lot de livraison')

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'is_comparatif_tarif_facture')
        cr.execute("""
CREATE OR REPLACE FUNCTION is_prix_vente(pricelistid integer, productid integer, qt float, date date) RETURNS float AS $$
BEGIN
    RETURN (
        select price_surcharge 
        from product_pricelist ppl inner join product_pricelist_version ppv on ppv.pricelist_id=ppl.id 
                                   inner join product_pricelist_item    ppi on ppi.price_version_id=ppv.id
        where ppi.product_id=productid
            and ppl.id=pricelistid
            and min_quantity<=qt
            and ppl.type='sale' and ppl.active='t'
            and (ppv.date_end   is null or ppv.date_end   >= date) 
            and (ppv.date_start is null or ppv.date_start <= date) 

            and (ppi.date_end   is null or ppi.date_end   >= date) 
            and (ppi.date_start is null or ppi.date_start <= date) 
        order by ppi.sequence limit 1
    );
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION get_lot_livraison(product_tmpl_id integer, partner_id integer) RETURNS float AS $$
BEGIN
    RETURN (
            coalesce((
                select lot_livraison 
                from is_product_client ipc 
                where ipc.client_id=partner_id and ipc.product_id=product_tmpl_id limit 1
                ),0
            )
    );
END;
$$ LANGUAGE plpgsql;



CREATE OR REPLACE view is_comparatif_tarif_facture AS (
    select 
        ail.id            id,
        ai.id             invoice_id,
        ai.date_invoice   invoice_date,
        so.id             order_id,
        so.partner_id     partner_id,
        so.pricelist_id   pricelist_id,
        pt.id             product_id,
        ail.quantity      quantity,
        ail.uos_id        uos_id,
        ail.price_unit    invoice_price, 
        coalesce(
            is_prix_vente(
                so.pricelist_id,
                ail.product_id,
                ail.quantity,
                ai.date_invoice
            ),
            0
        ) as pricelist_price,
        coalesce(
            is_prix_vente(
                so.pricelist_id,
                ail.product_id,
                ail.quantity,
                ai.date_invoice
            ),
            0
        )-ail.price_unit as price_delta,
        get_lot_livraison(pt.id, so.partner_id) lot_livraison,
        coalesce(
            is_prix_vente(
                so.pricelist_id,
                ail.product_id,
                get_lot_livraison(pt.id, so.partner_id),
                ai.date_invoice
            ),
            0
        ) as prix_lot_livraison
    from account_invoice_line ail inner join account_invoice  ai on ail.invoice_id=ai.id
                                  inner join stock_move       sm on ail.is_move_id=sm.id
                                  inner join sale_order_line sol on sm.is_sale_line_id=sol.id
                                  inner join sale_order       so on sol.order_id=so.id
                                  inner join product_product  pp on ail.product_id=pp.id
                                  inner join product_template pt on pp.product_tmpl_id=pt.id
    where ai.state='draft' and ai.type in ('out_invoice', 'out_refund')
)
        """)


