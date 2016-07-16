# -*- coding: utf-8 -*-

import csv
import StringIO

from openerp.tools.translate import _
from openerp import netsvc
from openerp.osv import osv, fields
from lxml import etree
from tempfile import TemporaryFile
import base64
import os
import time
from datetime import date, datetime

    
class is_import_csv1(osv.osv):
    _name = "is_import_csv1"
    _description = "Importation des fichiers de la fonction d'import csv1"
    _columns = {
    } 
    
    # Retourner True si ref_product existe déjà dans result
    def exist_ref_product(self, cr, uid, ref_product, result, context=None):
        if result:
            for item in result:
                if item['ref_product'] == ref_product:
                    return True
                else:
                    continue
        return False
    
    
    # Ajouter les details des commandes client dans la liste des contrats
    def add_details_contract(self, cr, uid, ref_product, res, result, context=None):
        if result:
            for item in result:
                if item['ref_product'] == ref_product:
                    item['details'].append(res)
                else:
                    continue
        return True
    
    def get_quantity(self, cr, uid, str_qty, context=None):
        if str_qty:
            str_qty = str_qty.replace(' ','')
            if len(str_qty.split(',')) == 2:
                return float(str_qty.replace(',','.'))
            else:
                return float(str_qty)
        else:
            return 0.0
    
    # Lire le fichier csv et remplir une liste par les informations adéquates
    def get_data_csv(self, cr, uid, data, context=None):
        quotechar='"'
        delimiter=','
            
        name = str(datetime.now()).replace(':', '').replace('.', '').replace(' ', '')
        filename = '/tmp/%s.xls' % name
        temp = open(filename, 'w+b')
        temp.write((base64.decodestring(data['file']))) 
        temp.close()
                      
        myTabfile = open(filename,'rU').read().replace("\00"," ")
        file = StringIO.StringIO(myTabfile)
        reader = csv.reader (file, dialect=csv.excel_tab)
                  
        result = []
        numrow = 0
        for row in reader:
            print 'row', row
            if numrow == 0:
                numrow += 1
                continue
            else:
                # 0: article, 1: type_contrat, 2: date_livraison, 3: quantity
                if not self.exist_ref_product(cr, uid, row[5], result, context=context):
                    contract = {
                        'ref_product': row[5],
                        'ref_partner': False,
                        'details': [{
                            'type_contract': row[7],
                            'date_livraison': row[9],
                            'qty_product': self.get_quantity(cr, uid, row[12], context=context),
                        }]
                    }
                    print "contract ******", contract
                    result.append(contract)
                else:
                    res = {
                        'type_contract': row[7],
                        'date_livraison': row[9],
                        'qty_product': self.get_quantity(cr, uid, row[12], context=context),
                    }
                    self.add_details_contract(cr, uid, row[5], res, result, context=context)
                numrow += 1
        print "result *******", result                
        return result
                
    
is_import_csv1()
