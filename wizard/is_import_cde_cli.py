# -*- coding: utf-8 -*-

import csv
import numpy as np
import xlrd

from openerp.tools.translate import _
from openerp import netsvc
from openerp.osv import osv, fields
from lxml import etree
from tempfile import TemporaryFile
import base64
import os
import time
from datetime import date, datetime



class is_import_cde_cli_line(osv.osv_memory):
    _name = "is.import.cde.cli.line"
    _columns = {
        'client_order_ref': fields.char('Reference commande client', size=64),
        'is_ref_client'   : fields.char('Reference article client', size=64),
        'import_id'       : fields.many2one('is.import.cde.cli', 'Import'),
    }
is_import_cde_cli_line()


class is_import_cde_cli(osv.osv_memory):
    _name = "is.import.cde.cli"
    _description = "Importer les commandes ouvertes"  
    
    _columns = {
        'partner_id': fields.many2one('res.partner', 'Client', required=False),
        'import_function': fields.char("Fonction d'importation EDI", size=32, readonly=True),
        'name': fields.char('Nom de fichier', size=128),
        'file': fields.binary('Fichier', required=True),
        'create_uid': fields.many2one('res.users', 'Importe par', readonly=True),
        'create_date': fields.datetime("Date d'importation"),
        'line_ids': fields.one2many('is.import.cde.cli.line', 'import_id', "Commandes ouvertes non trouvées dans le fichier d'import"),
    }
    
    
    # Remplir le champ import_function à partir de champ partner_id
    def onchange_partner_id(self, cr, uid, ids, part, context=None):
        if not part:
            return {}
        part = self.pool.get('res.partner').browse(cr, uid, part, context=context)
        val = {
            'import_function': part.is_import_function,
        }
        return {'value': val}
    


#    def _get_contract_ids(self, cr, uid, context=None):
#        if context is None:
#            context = {}
#        return context.get('contract_ids', [])
#    
#    _defaults = {
#        'contract_ids': _get_contract_ids,
#    }


    # Retourner les contrats de la liste des informations extrait de fichier d'importation
    def get_contracts(self, cr, uid, data, context=None):
        res = []        
        if data:
            for item in data:
                res.append((item['ref_product'], item['ref_partner']))
        return res
                  
    # Retourner la liste des contrats (couple(refcommandeclient, refproduitclient)) lié au client choisi
    def get_contracts_partner(self, cr, uid, partner_id, context=None):
        res = []
        sale_order_obj = self.pool.get('sale.order')
        
        sale_order_ids = sale_order_obj.search(cr, uid, [('partner_id', '=', partner_id)], context=context)
        if sale_order_ids:
            for row in sale_order_obj.read(cr, uid, sale_order_ids, ['is_ref_client','client_order_ref']):
                res.append((row['is_ref_client'], row['client_order_ref']))

        print "##TEST 1", res
        ##TEST 1 [(u'107', u'test'), (False, u'test'), (False, u'toto'), (u'107', u'Ref1'), (u'107', False), (False, False)]


        return res
    
#                                <field name="is_ref_client" />
#                                <field name="client_order_ref" />





    # Comparer la liste des contrats de fichier d'importaion avec celle associée au client
    # Retourner les contrats non trouvés
    def compare_lst_contracts(self, cr, uid, lst_contracts_partner, lst_contracts, context=None):
        res = []
        for contract in lst_contracts:
            if not contract in lst_contracts_partner:
                #res.append(contract)
                x="Commande / Article : "+contract[1]+" / "+contract[0]
                res.append(x)
            else:
                continue
        return chr(10).join(res)
    
#    # Faire Afficher la liste des contrats non existants
#    def contracts_notfound(self, cr, uid, id, lst_contracts_notfound, context=None):
#        res = []
#        for contract in lst_contracts_notfound:
#            vals = {
#                'client_order_ref': contract[1],
#                'is_ref_client': contract[0],
#                'import_id': id,
#                  
#            }
#            #vals="Article / Commande : "+contract[0]+" / "+contract[1]
#            #print "contracts_notfound", vals
#            res.append(vals)
#        return res 
    

#        'client_order_ref': fields.char('Reference commande client', size=64),
#        'is_ref_client'   : fields.char('Reference article client', size=64),




    # Retourner l'id de contrat associé au couple (refcommandeclient, refproduitclient)
    def get_order_id(self, cr, uid, ref_partner, ref_product, context=None):
        obj = self.pool.get('sale.order')
        id = obj.search(cr, uid, [('client_order_ref','=',ref_partner),('is_ref_client','=',ref_product)], context=context)[0]
        print "get_order_id=",id
        return id
    
    # Supprimer les devis associé au contrat courant et ayant une date supérieure à la date de jour
    def delete_quotations(self, cr, uid, order_id, context=None):
        order_obj = self.pool.get('sale.order.line')
        #today = time.strftime('%Y-%m-%d')
        today = time.strftime('%d/%m/%Y')
        order_ids = order_obj.search(cr, uid, [
            ('order_id','=',order_id),
            ('state','=','draft')
        ], context=context)

        print "delete_quotations : order_ids=",order_ids, order_id, today

        res = order_obj.unlink(cr, uid, order_ids, context=context)
        return res
    
    # interpreter la date de livraison de fichier d'importation
    def convert_date(self, cr, uid, import_function, date_livraison, context=None):
        if import_function == 'xml1':
            date = time.strptime(date_livraison, '%Y%m%d%H%M%S')
            return time.strftime('%Y-%m-%d', date)
        elif import_function == 'csv1':
            date = time.strptime(date_livraison, '%d.%m.%Y')
            return time.strftime('%Y-%m-%d', date)
        
    # interpreter le type de contrat de fichier d'importation
    def convert_contract_type(self, cr, uid, import_function, contract_type, context=None):
        if import_function == 'xml1':
            if contract_type == '1':
                return 'ferme'
            elif contract_type == '4':
                return 'previsionnel'
            else:
                return ''
        if import_function == 'csv1':
            if contract_type == 'F':
                return 'ferme'
            elif contract_type == 'P':
                return 'previsionnel'
            else:
                return ''       
    
    # Creation de devis
    def create_quotation(self, cr, uid, ids, import_function, order_id, partner_id, detail, context=None):
        order_obj = self.pool.get('sale.order')
        order_line_obj = self.pool.get('sale.order.line')
        order = order_obj.browse(cr, uid, order_id, context=context)
        date_livraison = self.convert_date(cr, uid, import_function, detail['date_livraison'], context=context)
        date_expedition = order_line_obj.onchange_date_livraison(cr, uid, ids, date_livraison, order.partner_id, 1, order.id, context=context)['value']['is_date_expedition']
        type_commande = self.convert_contract_type(cr, uid, import_function, detail['type_contract'], context=context)
        order_line = order_line_obj.product_id_change(cr, uid, ids, 1, order.is_article_commande_id.id, 0, False, 0, False, '', order.partner_id.id, False, True, False, False, False, False, context=context)['value']
        order_line.update({
            'order_id':order.id, 
            'is_date_livraison':date_livraison, 
            'is_type_commande':type_commande, 
            'is_date_expedition':date_expedition, 
            'product_id':order.is_article_commande_id.id, 
            'product_uom_qty': detail['qty_product']
        })
        newid = order_line_obj.create(cr, uid, order_line, context=context)
        return newid

        
    def import_contract_orders(self, cr, uid, ids, context=None):                 
        if context is None:
            context = {}
        
        xml1_obj = self.pool.get('is_import_xml1')
        csv1_obj = self.pool.get('is_import_csv1')
        obj_model = self.pool.get('ir.model.data')

        result = []
        
        data = self.read(cr, uid, ids)[0]       
        if data:
            partner = self.pool.get('res.partner').browse(cr, uid, data['partner_id'][0], context=context)
            # Extraire les informations du fichier d'importation à utiliser dans la création des commandes ouvertes      
            if partner.is_import_function == 'xml1':
                res = xml1_obj.get_data_xml(cr, uid, data, context=context)
            elif partner.is_import_function == 'csv1':
                res = csv1_obj.get_data_csv(cr, uid, data, context=context)
            else:
                res = []
                
            lst_contracts = self.get_contracts(cr, uid, res, context=context)
            lst_contracts_partner = self.get_contracts_partner(cr, uid, data['partner_id'][0], context=context)
            lst_contracts_notfound = self.compare_lst_contracts(cr, uid, lst_contracts_partner, lst_contracts, context=context)

            print "lst_contracts=",lst_contracts


            if lst_contracts_notfound:
                raise osv.except_osv('Contrat non trouvés !',str(lst_contracts_notfound))

                #line_ids = self.contracts_notfound(cr, uid, ids[0], lst_contracts_notfound, context=context)
                #context = {}
                #context.update({'line_ids': line_ids})


                #print "## TEST3", line_ids
                ## TEST3 [{'import_id': 6, 'ref_partner': '0424027', 'ref_product': 'SJ3004ZD'}, {'import_id': 6, 'ref_partner': '0424028', 'ref_product': 'SJ3003ZD'}]
                #print "## TEST4", context

                #model_data_ids = obj_model.search(cr,uid,[('model','=','ir.ui.view'),('name','=','is_import_cde_cli_notfound_view')])
                #resource_id = obj_model.read(cr, uid, model_data_ids, fields=['res_id'])[0]['res_id']

                #context = {}
                #context.update({'partner_id': 7})




#                return {
#                        'view_type': 'form',
#                        'view_mode': 'form',
#                        'res_model': 'is.import.cde.cli',
#                        'views': [(resource_id,'form')],
#                        'type': 'ir.actions.act_window',
#                        'target': 'new',
#                        'context': context,
#                }               
            else:
                for item in res:

                    print "item=",item
                    #item= {'ref_partner': '0424027', 'ref_product': 'SJ3004ZD', 'details': [{'date_livraison': '20140702000000', 'qty_product': '1000', 'type_contract': '4'}]}


                    # déterminer l'id de contrat associé au couple (refcommandeclient, refproduitclient)
                    order_id = self.get_order_id(cr, uid, item['ref_partner'], item['ref_product'], context=context)
                    # Suppression des devis ayant une date de livraison supérieure à la date de jour
                    self.delete_quotations(cr, uid, order_id, context=context)
                    for detail in item['details']:
                        newid = self.create_quotation(cr, uid, ids, partner.is_import_function, order_id, data['partner_id'][0], detail, context=context)
                        result.append(newid)
        
        result.sort()                
        action_model = False
        data_pool = self.pool.get('ir.model.data')
        action = {}
        action_model,action_id = data_pool.get_object_reference(cr, uid, 'sale', "action_quotations")
        
        if action_model:
            action_pool = self.pool.get(action_model)
            action = action_pool.read(cr, uid, action_id, context=context)
            action['domain'] = "[('id','in', ["+','.join(map(str,result))+"])]"
        return action
    
is_import_cde_cli()

