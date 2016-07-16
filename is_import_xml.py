# -*- coding: utf-8 -*-

from openerp.tools.translate import _
from openerp import netsvc
from openerp.osv import osv, fields
from lxml import etree
from tempfile import TemporaryFile
import base64
import os
import time
from datetime import date, datetime

class is_import_xml1(osv.osv):
    _name = "is_import_xml1"
    _description = "Importation des fichiers de la fonction d'import xml1"
    _columns = {
    }  
    
    # Extraire les informations necessaires de fichier xml et retourne une liste des dictionaires    
    def get_data_xml(self, cr, uid, data, context=None):
        name = str(datetime.now()).replace(':', '').replace('.', '').replace(' ', '')
        filename = '/tmp/%s.xml' % name
        temp = open(filename, 'w+b')
        temp.write((base64.decodestring(data['file']))) 
        temp.close()
        tree = etree.parse(filename)      
        
        res = []
        for partie_citee in tree.xpath("/DELINS/PARTIE_CITEE"):
            if  partie_citee.xpath("ARTICLE_PROGRAMME"):
                contract = {
                    'ref_product': partie_citee.xpath("ARTICLE_PROGRAMME/NumeroArticleClient")[0].text,
                    'ref_partner': partie_citee.xpath("ARTICLE_PROGRAMME/NumeroCommande")[0].text,
                    'details': []
                }
                res1 = []
                for detail_programme in partie_citee.xpath("ARTICLE_PROGRAMME/DETAIL_PROGRAMME"):
                    detail = {
                        'qty_product': detail_programme.xpath("QuantiteALivrer")[0].text,
                        'type_contract': detail_programme.xpath("CodeStatutProgramme")[0].text,
                        'date_livraison': detail_programme.xpath("DateHeureLivraisonAuPlusTot")[0].text,
                    }
                    res1.append(detail)
                
                contract.update({'details':res1})
                res.append(contract)
            else:
                continue


        for partie_citee in tree.xpath("/CALDEL/SEQUENCE_PRODUCTION"):
            if  partie_citee.xpath("ARTICLE_PROGRAMME"):
                contract = {
                    'ref_product': partie_citee.xpath("ARTICLE_PROGRAMME/NumeroArticleClient")[0].text,
                    'ref_partner': partie_citee.xpath("ARTICLE_PROGRAMME/NumeroCommande")[0].text,
                    'details': []
                }
                res1 = []
                for detail_programme in partie_citee.xpath("ARTICLE_PROGRAMME/DETAIL_PROGRAMME"):
                    detail = {
                        'qty_product': detail_programme.xpath("QuantiteALivrer")[0].text,
                        'type_contract': detail_programme.xpath("CodeStatutProgramme")[0].text,
                        'date_livraison': detail_programme.xpath("DateHeureLivraisonAuPlusTot")[0].text,
                    }
                    res1.append(detail)
                
                contract.update({'details':res1})
                res.append(contract)
            else:
                continue



        return res
    
is_import_xml1()
