# -*- coding: utf-8 -*-

# Doc : https://doc.openerp.com/trunk/server/03_module_dev_01/
#       https://doc.openerp.com/trunk/server/03_module_dev_01/#manifest-file-openerp-py

{
  "name" : "InfoSaône - Module Odoo d'installation des dépendances pour Plastigray",
  "version" : "0.1",
  "author" : "InfoSaône",
  "category" : "InfoSaône\Plastigray",


  'description': """
InfoSaône - Module Odoo d'installation des dépendances pour Plastigray 
===================================================

Ce module sert uniquement à installer les dépendances du projet Plastigray

""",

  'maintainer': 'InfoSaône',
  'website': 'http://www.infosaone.com',

  "depends" : [
    "base",
    "mail",
    "crm",                    # CRM
    "account_voucher",        # eFacturation & Règlements
    "account_accountant",     # Comptabilité et finance
    "sale",                   # Gestion des ventes
    "stock",                  # Stock
    "mrp",                    # MRP
    "mrp_operations",         # Gammes
    "purchase",               # Gestion des achats
    "is_routing",             # Modifications des gammes
    "is_bom",                 # Modifications des nomenclatures
    "is_pricelist",           # Modifications Liste de prix
    "is_inventory",           # Modifications Inventaires
    "is_automobile_contract", # Gestion des commandes ouvertes pour l'automobile
    "is_contract_edi",        # Importation des commandes ouvertes
    "is_mrp",                 # Calcul des besoins
    "is_mold",                # Moules et Projets pour l'injection plastique
    "is_pg_product",          # Fiche article
  ], # Liste des dépendances (autres modules nececessaire au fonctionnement de celui-ci)
     # -> Il peut être interessant de créer un module dont la seule fonction est d'installer une liste d'autres modules
     # Remarque : La desinstallation du module n'entrainera pas la desinstallation de ses dépendances (ex : mail)

  "init_xml" : [],             # Liste des fichiers XML à installer uniquement lors de l'installation du module
  "demo_xml" : [],             # Liste des fichiers XML à installer pour charger les données de démonstration
  "data" : [
    "res_partner_view.xml",  # Vue partenaire modifiée
    "menu.xml",              # Reorganisation des menus
    "assets.xml",            # Permet d'ajouter des css et des js
    'is_config_view.xml',    # Configuration par défaut
  ], # Liste des fichiers XML à installer lors d'une mise à jour du module (ou lord de l'installation)
  "installable": True,         # Si False, ce module sera visible mais non installable (intéret ?)
  "active": False              # Si True, ce module sera installé automatiquement dés la création de la base de données d'OpenERP
}




