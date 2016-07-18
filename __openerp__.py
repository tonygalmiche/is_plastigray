# -*- coding: utf-8 -*-
{
    "name" : "InfoSaône - Module Odoo pour Plastigray",
    "version" : "0.2",
    "author" : "InfoSaône",
    "category" : "InfoSaône\Plastigray",
    'description': """
    InfoSaône - Module Odoo pour Plastigray 
    ===================================================
    Ce module sert uniquement à installer les dépendances du projet Plastigray et à configurer les menus
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
        "is_pricelist",           # Modifications Liste de prix
        "is_inventory",           # Modifications Inventaires
        "is_mrp",                 # Calcul des besoins
        "is_mold",                # Moules et Projets pour l'injection plastique
        "is_pg_product",          # Fiche article
        "is_gestion_lot",         # Gestion des lots pour le contrôle qualité
    ], 
    "data" : [
        "res_partner_view.xml",  # Vue partenaire modifiée
        "assets.xml",            # Permet d'ajouter des css et des js
        "sale_view.xml",
        "mrp_view.xml",
        "stock_view.xml",
        "product_view.xml",
        "is_pdc_view.xml",
        "is_liste_servir_sequence.xml",
        "is_liste_servir_view.xml",
        "is_plastigray_report.xml",
        "is_edi_cde_cli_view.xml",
        "wizard/is_liste_servir_wizard_view.xml",
        "views/layouts.xml",
        "views/report_mrpbomstructure.xml",
        "views/webclient_templates.xml",
        "views/report_liste_servir.xml",
        "report/is_pic_3mois.xml",
        "menu.xml",              # Reorganisation des menus
        "security/ir.model.access.csv",
    ], 
    "installable": True,
    "active": False
}




