# -*- coding: utf-8 -*-

from openerp.osv import osv, fields
import datetime
import time


#TODO : 
# - Creer la table 'is_liste_servir_client
# - Créer une requete pour lister les clients ayant des commandes à livrer sur la periode indiquée
# - Remplir la table avec les données de la requetes
# - Depuis chaque ligne de la table, un bouton permettra de générer la liste à servir ou d'afficher la liste existante
# - Si une liste existe déja, il ne sera pas possible d'en créer une nouvelle
# - Mettre un verrou égalment dans la création des listes pour ne pas avoir 2 liste en même temps sur la même période



class is_liste_servir_wizard(osv.osv_memory):
    _name = "is.liste.servir.wizard"
    _description = "Listes a servir des clients"  
    
    _columns = {
        'date_debut': fields.date(u"Date de début d'expédition", required=False),
        'date_fin':   fields.date(u"Date de fin d'expédition", required=True),
        'livrable':   fields.boolean("Livrable (avec stock)"),
    }


    def _date_fin():
        now = datetime.date.today()                 # Date du jour
        date_fin = now + datetime.timedelta(days=1) # J+1
        return date_fin.strftime('%Y-%m-%d')        # Formatage


    _defaults={
        'livrable': False,
        'date_fin': _date_fin(),
    }



    def generer_liste_servir_client(self, cr, uid, ids, context=None):
        data = self.read(cr, uid, ids)[0]
        if data:
            SQL="delete from is_liste_servir_client"
            cr.execute(SQL)
#            SQL="""
#                select so.partner_id, rp.zip, rp.city, rp.is_delai_transport, sum(sol.product_uom_qty)
#                from sale_order so inner join sale_order_line sol on so.id=sol.order_id
#                                   inner join res_partner rp on so.partner_id=rp.id
#                where sol.is_date_expedition<='"""+str(data['date_fin'])+"""' 
#                      and so.state='draft' """
#            if data['date_debut']:
#                SQL=SQL+" and sol.is_date_expedition>='"+str(data['date_debut'])+"' "
#            SQL=SQL+"group by so.partner_id, rp.zip, rp.city, rp.is_delai_transport"


            SQL="""
                select  so.partner_id, 
                        rp.zip, 
                        rp.city, 
                        rp.is_delai_transport, 
                        sum(sol.product_uom_qty)
                from sale_order so inner join sale_order_line   sol on so.id=sol.order_id
                                   inner join res_partner       rp  on so.partner_id=rp.id
                                   inner join product_product   pp  on sol.product_id=pp.id
                                   inner join  product_template pt  on pp.product_tmpl_id=pt.id
                where sol.is_date_expedition<='"""+str(data['date_fin'])+"""' 
                      and so.state='draft' 
                      and sol.is_type_commande='ferme' 
                      and so.is_type_commande!='ls'
            """
            if data['livrable']:
                SQL=SQL+"""
                      and (
                        select sum(sq.qty) 
                        from stock_quant sq inner join stock_location sl on sq.location_id=sl.id
                        where sq.product_id=pp.id and sl.usage='internal' and sl.active='t'
                      )>=sol.product_uom_qty
                """
            if data['date_debut']:
                SQL=SQL+" and sol.is_date_expedition>='"+str(data['date_debut'])+"' "
            SQL=SQL+"group by so.partner_id, rp.zip, rp.city, rp.is_delai_transport"
            cr.execute(SQL)
            result = cr.fetchall()
            for row in result:
                SQL="""
                    select id 
                    from is_liste_servir 
                    where state!='traite' and partner_id="""+str(row[0])+" limit 1"
                cr.execute(SQL)
                result2 = cr.fetchall()
                liste_servir_id=False
                for row2 in result2:
                    liste_servir_id=row2[0]



                vals={
                    'name'            : row[0],
                    'liste_servir_id' : liste_servir_id,
                    'zip'             : row[1],
                    'city'            : row[2],
                    'delai_transport' : row[3],
                    'date_debut'      : data['date_debut'],
                    'date_fin'        : data['date_fin'],
                    'livrable'        : data['livrable'],
                }
                new_id=self.pool.get('is.liste.servir.client').create(cr, uid, vals, context=context)
            return {
                'name': "Clients à livrer",
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree',
                'res_model': 'is.liste.servir.client',
                'target': 'current',
            }




        dummy, view_id = self.env['ir.model.data'].get_object_reference('is_pg_product', 'is_product_template_only_form_view')
        for obj in self:
            return {
                'name': "Article",
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'product.template',
                'type': 'ir.actions.act_window',
                'res_id': obj.product_id.product_tmpl_id.id,
                'domain': '[]',
            }







